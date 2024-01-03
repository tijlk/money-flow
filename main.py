import os
from itertools import groupby
from dotenv import load_dotenv
import warnings
import json
from google.cloud import secretmanager

from src.allocation import FireStore
from src.bunq import BunqLib
from src.strategies import all_strategies
warnings.filterwarnings('ignore')


load_dotenv()


def get_secret_value(secret_name, project_id):
    client = secretmanager.SecretManagerServiceClient()
    secret_version_name = client.secret_version_path(project_id, secret_name, 'latest')
    response = client.access_secret_version(name=secret_version_name)
    return response.payload.data.decode('UTF-8')


PROJECT_ID = os.getenv("PROJECT_ID")
API_KEY = get_secret_value('bunq_api_key', PROJECT_ID)
GOOGLE_FIRESTORE_CONFIG = json.loads(get_secret_value('firebase_service_account', PROJECT_ID))
API_CONTEXT_FILE_PATH = os.getenv("BUNQ_FILE_NAME")
ENVIRONMENT = os.getenv("ENVIRONMENT")
DEVICE_DESCRIPTION = os.getenv("DESCRIPTION")
SIMULATE = os.getenv("SIMULATE", 'False').lower() in ('true', '1', 't')


class AutomateAllocations:
    def __init__(self, bunq: BunqLib, store: FireStore):
        self.bunq = bunq
        self.store = store
        self.main_account_balance = None

    def run(self):
        allocations = self.store.get_allocations(self.bunq.accounts)
        sorted_allocations = sorted(allocations, key=lambda x: x.priority)
        grouped_allocations = groupby(sorted_allocations, key=lambda x: x.priority)
        main_account_settings = self.store.get_main_account_settings()
        self.main_account_balance = self.bunq.get_balance_by_id(id_=main_account_settings.id)
        remainder = self.main_account_balance
        print(f"{remainder} EUR to sort...")

        for _, group in grouped_allocations:
            allocations = list(group)
            for allocation in filter(lambda a: a.strategy != "percentage", allocations):
                remainder = self._process_allocation(
                    allocation, main_account_settings, remainder
                )

            original_remainder = remainder
            for allocation in filter(lambda a: a.strategy == "percentage", allocations):
                remainder = self._process_allocation(
                    allocation,
                    main_account_settings,
                    remainder,
                    original_remainder=original_remainder,
                )

    def _process_allocation(
        self, allocation, main_account_settings, remainder, *, original_remainder=None
    ):
        strategy = all_strategies.get(allocation.strategy)
        amount = strategy(
            allocation,
            original_remainder if original_remainder else remainder,
            bunq=self.bunq,
        )
        if amount > 0:
            self.bunq.make_payment(
                from_account_id=main_account_settings.id,
                to_account_alias=allocation.description,
                to_account_type=allocation.account_type,
                amount=amount,
                description=f"Deel salaris voor {allocation.description}",
                to_iban=allocation.iban,
                simulate=SIMULATE,
                original_amount_to_sort=self.main_account_balance
            )
            remainder -= amount
        return remainder


if __name__ == "__main__":
    store_ = FireStore(config=GOOGLE_FIRESTORE_CONFIG)
    bunq_ = BunqLib(
        api_key=API_KEY,
        environment_type=ENVIRONMENT,
        device_description=DEVICE_DESCRIPTION,
        api_context_file_path=API_CONTEXT_FILE_PATH,
    )
    bunq_.connect()
    bunq_.get_accounts()
    AutomateAllocations(bunq=bunq_, store=store_).run()
