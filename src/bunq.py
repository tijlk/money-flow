from decimal import Decimal
from os.path import isfile
import time

from bunq.sdk.context.api_context import ApiContext
from bunq.sdk.context.api_environment_type import ApiEnvironmentType
from bunq.sdk.context.bunq_context import BunqContext
from bunq.sdk.model.generated.endpoint import MonetaryAccount, Payment
from bunq.sdk.model.generated.object_ import Amount, Pointer


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
            ApiEnvironmentType.PRODUCTION
            if environment_type == "production"
            else ApiEnvironmentType.SANDBOX
        )
        self.device_description = device_description
        self.api_context_file_path = api_context_file_path
        self.is_connected = False
        self.accounts = None

    def connect(self):
        if isfile(self.api_context_file_path):
            pass  # Config is already present
        else:
            ApiContext.create(
                self.environment_type, self.api_key, self.device_description
            ).save(self.api_context_file_path)

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
        original_amount_to_sort: Decimal = None
    ):
        if simulate:
            s = "Simulating transfer of"
        else:
            s = "Transferring"
        perc = f"({amount / original_amount_to_sort * 100:.1f}%) " if original_amount_to_sort else ""
        print(f"{s} {amount:.2f} EUR {perc}to {to_account_alias} "
              f"({to_account_type} account {to_iban})")
        if not simulate:
            max_retries = 5
            retry_delay = 10  # seconds
            retry_count = 0
            success = False
            while retry_count < max_retries and not success:
                try:
                    # Code that you want to retry until it succeeds without exception
                    # Replace the following line with your actual code
                    Payment.create(
                        amount=Amount("{:.2f}".format(amount), "EUR"),
                        counterparty_alias=Pointer("IBAN", to_iban, name=to_account_alias),
                        description=description,
                        monetary_account_id=from_account_id
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

        main_account: MonetaryAccount = MonetaryAccount.get(id_).value
        return Decimal(main_account.get_referenced_object().balance.value)

    def get_balance_by_iban(self, *, iban: str):
        if not self.is_connected:
            raise Exception("Not connected. Please call connect first")

        if not self.accounts:
            self.get_accounts()

        accounts = self.accounts
        for _, account_info in accounts.items():
            if account_info["iban"] == iban:
                return Decimal(account_info["balance"])

    def get_accounts(self):
        accounts = {}
        for account in MonetaryAccount.list().value:
            object_type, account = next((key, value) for key, value in vars(account).items() if value is not None)
            if account.status == 'ACTIVE':
                accounts[account.id_] = {
                    "description": account.description,
                    "balance": float(account.balance.value),
                    "iban": account.alias[0].value,
                    "type": object_type[16:].lower()
                }
        self.accounts = accounts

