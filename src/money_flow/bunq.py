import time
from decimal import Decimal
from os.path import isfile

from bunq.sdk.context.api_context import ApiContext
from bunq.sdk.context.api_environment_type import ApiEnvironmentType
from bunq.sdk.context.bunq_context import BunqContext
from bunq.sdk.http.pagination import Pagination
from bunq.sdk.model.generated.endpoint import (
    MonetaryAccountBankApiObject,
    MonetaryAccountJointApiObject,
    MonetaryAccountSavingsApiObject,
    PaymentApiObject,
)
from bunq.sdk.model.generated.object_ import AmountObject, PointerObject


def fixed_from_json_list(cls, response_raw, wrapper=None):
    from bunq import Pagination
    from bunq.sdk.json import converter

    json = response_raw.body_bytes.decode()
    obj = converter.json_to_class(dict, json)
    array = obj[cls._FIELD_RESPONSE]
    array_deserialized = []
    for item in array:
        item_unwrapped = item if wrapper is None else item.get(wrapper, item)
        try:
            item_deserialized = converter.deserialize(cls, item_unwrapped)
        except TypeError:
            print(
                f"failed to deserialize item of type {cls.__name__}: description {item_unwrapped['description']}, "
                f"IBAN: {item_unwrapped['alias'][0]['value']}, {float(item_unwrapped['balance']['value']):,.2f} EUR"
            )
        else:
            array_deserialized.append(item_deserialized)
    pagination = None
    if cls._FIELD_PAGINATION in obj:
        pagination = converter.deserialize(Pagination, obj[cls._FIELD_PAGINATION])
    from bunq.sdk.http.bunq_response import BunqResponse

    return BunqResponse(array_deserialized, response_raw.headers, pagination)


MonetaryAccountSavingsApiObject._from_json_list = classmethod(fixed_from_json_list)


class BunqLib:
    def __init__(
        self,
        api_key,
        environment_type,
        device_description,
        api_context_file_path,
    ):
        self.api_key = api_key
        self.environment_type = (
            ApiEnvironmentType.PRODUCTION if environment_type == "production" else ApiEnvironmentType.SANDBOX
        )
        self.device_description = device_description
        self.api_context_file_path = api_context_file_path
        self.is_connected = False
        self.accounts = None

    def connect(self):
        if isfile(self.api_context_file_path):
            pass  # Config is already present
        else:
            ApiContext.create(self.environment_type, self.api_key, self.device_description).save(
                self.api_context_file_path
            )

        api_context = ApiContext.restore(self.api_context_file_path)
        api_context.ensure_session_active()
        api_context.save(self.api_context_file_path)

        BunqContext.load_api_context(api_context)
        self.is_connected = True

    @staticmethod
    def make_payment(
        from_account_id: str,
        to_account_alias: str,
        to_account_type: str,
        amount: Decimal,
        description: str,
        to_iban: str,
        simulate: bool = True,
        original_amount_to_sort: Decimal = None,
    ):
        if simulate:
            s = "Simulating transfer of"
        else:
            s = "Transferring"
        perc = f"({amount / original_amount_to_sort * 100:.1f}%) " if original_amount_to_sort else ""
        print(f"{s} {amount:.2f} EUR {perc}to {to_account_alias} " f"({to_account_type} account {to_iban})")
        if not simulate:
            max_retries = 5
            retry_delay = 10  # seconds
            retry_count = 0
            success = False
            while retry_count < max_retries and not success:
                try:
                    # Code that you want to retry until it succeeds without exception
                    # Replace the following line with your actual code
                    PaymentApiObject.create(
                        amount=AmountObject("{:.2f}".format(amount), "EUR"),
                        counterparty_alias=PointerObject("IBAN", to_iban, name=to_account_alias),
                        description=description,
                        monetary_account_id=from_account_id,
                    )
                    # If the code reaches this point without raising an exception, it's considered a success
                    time.sleep(2)
                    success = True
                except Exception as e:
                    print(f"Exception occurred: {e}")
                    retry_count += 1
                    print(f"Retrying... ({retry_count}/{max_retries})")
                    time.sleep(retry_delay)

            if not success:
                print("Exceeded maximum number of retries. Code execution failed.")

    def get_balance_by_id(self, *, id_: int):
        if not self.is_connected:
            raise Exception("Not connected. Please call connect first")

        balance = round(self.accounts[id_]["balance"], 2)
        return Decimal(balance)

    def get_balance_by_iban(self, *, iban: str):
        if not self.is_connected:
            raise Exception("Not connected. Please call connect first")

        if not self.accounts:
            self.get_accounts()

        accounts = self.accounts
        for _, account_info in accounts.items():
            if account_info["iban"] == iban:
                return Decimal(account_info["balance"])

    @staticmethod
    def get_some_accounts(pagination, first_time=False, account_type: str = "bank"):
        if first_time:
            params = pagination.url_params_count_only
        else:
            params = pagination.url_params_previous_page
        if account_type == "savings":
            response = MonetaryAccountSavingsApiObject.list(params=params)
        elif account_type == "joint":
            response = MonetaryAccountJointApiObject.list(params=params)
        else:
            response = MonetaryAccountBankApiObject.list(params=params)
        return response.value, response.pagination

    def add_raw_accounts_of_one_type(self, all_accounts, account_type: str = "bank"):
        pagination = Pagination()
        pagination.count = 200
        accounts, pagination = self.get_some_accounts(pagination, first_time=True, account_type=account_type)
        time.sleep(1.1)
        all_accounts.extend(accounts)
        while pagination.has_previous_page():
            accounts, pagination = self.get_some_accounts(pagination, account_type=account_type)
            time.sleep(1.1)
            all_accounts.extend(accounts)
        return all_accounts

    def get_accounts(self):
        all_accounts = []
        all_accounts = self.add_raw_accounts_of_one_type(all_accounts, account_type="bank")
        all_accounts = self.add_raw_accounts_of_one_type(all_accounts, account_type="joint")
        all_accounts = self.add_raw_accounts_of_one_type(all_accounts, account_type="savings")

        self.accounts = {}
        for account in all_accounts:
            object_type = type(account).__name__
            if account.status == "ACTIVE" and object_type != "_MonetaryAccountExternal":
                self.accounts[account.id_] = {
                    "description": account.description,
                    "balance": float(account.balance.value),
                    "iban": account.alias[0].value,
                    "type": object_type[15:-9].lower(),
                }
