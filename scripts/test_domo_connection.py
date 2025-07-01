import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../config/.env'))

DOMO_CLIENT_ID = os.getenv("DOMO_CLIENT_ID")
DOMO_CLIENT_SECRET = os.getenv("DOMO_CLIENT_SECRET")
DOMO_DATASET_ID = os.getenv("DOMO_DATASET_ID")
DOMO_API_HOST = "https://api.domo.com"

def get_domo_token():
    url = f"{DOMO_API_HOST}/oauth/token?grant_type=client_credentials&scope=data"
    resp = requests.post(url, auth=(DOMO_CLIENT_ID, DOMO_CLIENT_SECRET))
    print(f"Token request status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Failed to get Domo token: {resp.text}")
        return None
    return resp.json()["access_token"]

def get_dataset_info(token):
    url = f"{DOMO_API_HOST}/v1/datasets/{DOMO_DATASET_ID}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    print(f"Dataset info request status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Failed to get dataset info: {resp.text}")
        return None
    return resp.json()

if __name__ == "__main__":
    print("Validating Domo credentials and dataset access...")
    token = get_domo_token()
    if not token:
        print("Domo credentials are invalid or missing.")
        exit(1)
    print("Domo credentials are valid.")
    if not DOMO_DATASET_ID:
        print("DOMO_DATASET_ID is not set in your .env file.")
        exit(1)
    dataset_info = get_dataset_info(token)
    if dataset_info:
        print(f"\nDataset Name: {dataset_info.get('name')}")
        print(f"Dataset ID: {dataset_info.get('id')}")
        print("Columns:")
        for col in dataset_info.get("schema", {}).get("columns", []):
            print(f"  - {col['name']} ({col['type']})")
    else:
        print("Could not retrieve dataset info.")
