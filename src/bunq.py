from decimal import Decimal
from os.path import isfile

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

        self._memoized_accounts = None

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

    def make_payment(
        self,
        *,
        amount: Decimal,
        description: str,
        iban: str,
        iban_name: str,
        account_id: int
    ):
        if not self.is_connected:
            raise Exception("Not connected. Please call connect first")

        Payment.create(
            amount=Amount("{:.2f}".format(amount), "EUR"),
            counterparty_alias=Pointer("IBAN", iban, name=iban_name),
            description=description,
            monetary_account_id=account_id,
        )

    def get_balance_by_id(self, *, id_: int):
        if not self.is_connected:
            raise Exception("Not connected. Please call connect first")

        main_account: MonetaryAccount = MonetaryAccount.get(id_).value
        return Decimal(main_account.get_referenced_object().balance.value)

    def get_balance_by_iban(self, *, iban: str):
        if not self.is_connected:
            raise Exception("Not connected. Please call connect first")

        if not self._memoized_accounts:
            self._memoized_accounts = MonetaryAccount.list().value

        accounts = self._memoized_accounts
        for account in accounts:
            referenced_object = account.get_referenced_object()
            for alias in referenced_object.alias:
                if alias.type_ == "IBAN" and alias.value == iban:
                    return Decimal(referenced_object.balance.value)
