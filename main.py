import os
from dotenv import load_dotenv
import warnings
import json
from google.cloud import secretmanager
import functions_framework

from src.allocation import FireStore
from src.automate import AutomateAllocations
from src.bunq import BunqLib


def get_secret_value(secret_name, project_id):
    client = secretmanager.SecretManagerServiceClient()
    secret_version_name = client.secret_version_path(project_id, secret_name, 'latest')
    response = client.access_secret_version(name=secret_version_name)
    return response.payload.data.decode('UTF-8')


warnings.filterwarnings('ignore')
load_dotenv(override=True)


PROJECT_ID = os.getenv("PROJECT_ID")
API_KEY = get_secret_value('bunq_api_key', PROJECT_ID)
GOOGLE_FIRESTORE_CONFIG = json.loads(get_secret_value('firebase_service_account', PROJECT_ID))
API_CONTEXT_FILE_PATH = os.getenv("BUNQ_FILE_NAME")
ENVIRONMENT = os.getenv("ENVIRONMENT")
DEVICE_DESCRIPTION = os.getenv("DESCRIPTION")
SIMULATE = os.getenv("SIMULATE", 'False').lower() in ('true', '1', 't')


@functions_framework.http
def main():
    try:
        store_ = FireStore(config=GOOGLE_FIRESTORE_CONFIG)
    except Exception as error:
        print("An error occurred:", type(error).__name__, "–", error)
        print("Are you on VPN maybe?")
        exit(1)
    bunq_ = BunqLib(
        api_key=API_KEY,
        environment_type=ENVIRONMENT,
        device_description=DEVICE_DESCRIPTION,
        api_context_file_path=API_CONTEXT_FILE_PATH,
    )
    bunq_.connect()
    bunq_.get_accounts()
    AutomateAllocations(bunq=bunq_, store=store_, simulate=SIMULATE).run()
    return "Success"


if __name__ == "__main__":
    main()
