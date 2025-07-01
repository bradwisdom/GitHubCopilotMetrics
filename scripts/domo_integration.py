import requests
import json
import os
import pandas as pd
import logging
import sys

# Add dotenv loading to ensure environment variables are loaded
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../config/.env'))

# Setup logging (force handler if already set)
LOGS_DIR = os.path.join(os.path.dirname(__file__), '../logs')
os.makedirs(LOGS_DIR, exist_ok=True)
log_file = os.path.join(LOGS_DIR, 'domo_integration.log')

logger = logging.getLogger("domo_integration")
logger.setLevel(logging.DEBUG)
# Remove all handlers associated with the logger object (avoid duplicate logs)
for handler in logger.handlers[:]:
    logger.removeHandler(handler)
file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

DOMO_CLIENT_ID = os.getenv("DOMO_CLIENT_ID")
DOMO_CLIENT_SECRET = os.getenv("DOMO_CLIENT_SECRET")
DOMO_DATASET_ID = os.getenv("DOMO_DATASET_ID")
DOMO_API_HOST = "https://api.domo.com"

def get_domo_token():
    url = f"{DOMO_API_HOST}/oauth/token?grant_type=client_credentials&scope=data"
    print("Requesting Domo token...")
    logger.info("Requesting Domo token.")
    resp = requests.post(url, auth=(DOMO_CLIENT_ID, DOMO_CLIENT_SECRET))
    if resp.status_code != 200:
        print(f"Failed to get Domo token: {resp.text}")
        print(f"Check that your client_id and client_secret are correct and have the right permissions.")
        print(f"client_id: {DOMO_CLIENT_ID}")
        # Optionally, do not print client_secret for security reasons
        resp.raise_for_status()
    return resp.json()["access_token"]

# Add this list to match the 22-column schema used in copilotmetrics/output/copilot_metrics_*.json
COLUMNS = [
    "date",
    "total_active_users",
    "total_engaged_users",
    "ide_completions_users",
    "ide_chat_users",
    "dotcom_chat_users",
    "pr_users",
    "editor",
    "model",
    "is_custom_model",
    "language",
    "code_suggestions",
    "code_acceptances",
    "lines_suggested",
    "lines_accepted",
    "chat_count",
    "chat_insertions",
    "chat_copies",
    "pr_summaries",
    "repository"
    # Add more columns here if your dataset includes them
]

def upload_to_domo(json_data, append=False):
    print(f"Starting upload_to_domo, append={append}")
    logger.info(f"Starting upload_to_domo, append={append}")
    if not json_data or not isinstance(json_data, list) or len(json_data) == 0:
        print("No data provided to upload_to_domo. Aborting upload.")
        logger.warning("No data provided to upload_to_domo. Aborting upload.")
        return False
    token = get_domo_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "text/csv"
    }
    # Ensure DataFrame columns match the expected schema and fill missing columns with None
    df = pd.DataFrame(json_data)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = None
    df = df[COLUMNS]
    print(f"DataFrame shape: {df.shape}")
    logger.debug(f"DataFrame shape: {df.shape}")
    if df.empty:
        print("DataFrame is empty after conversion from json_data. Aborting upload.")
        logger.warning("DataFrame is empty after conversion from json_data. Aborting upload.")
        return False
    csv_data = df.to_csv(index=False)
    if append:
        url = f"{DOMO_API_HOST}/v1/datasets/{DOMO_DATASET_ID}/data?updateMethod=APPEND"
        print(f"Appending data to Domo dataset {DOMO_DATASET_ID}.")
        logger.info(f"Appending data to Domo dataset {DOMO_DATASET_ID}.")
    else:
        url = f"{DOMO_API_HOST}/v1/datasets/{DOMO_DATASET_ID}/data?updateMethod=REPLACE"
        print(f"Replacing data in Domo dataset {DOMO_DATASET_ID}.")
        logger.info(f"Replacing data in Domo dataset {DOMO_DATASET_ID}.")
    print(f"PUT URL: {url}")
    logger.debug(f"PUT URL: {url}")
    print(f"CSV Data Preview: {csv_data[:500]}")
    logger.debug(f"CSV Data Preview: {csv_data[:500]}")
    try:
        print("Uploading data to Domo...")
        resp = requests.put(url, headers=headers, data=csv_data.encode("utf-8"))
        print(f"Domo upload response status: {resp.status_code}")
        logger.info(f"Domo upload response status: {resp.status_code}")
        if resp.status_code not in (200, 204):
            print(f"Failed to upload data to Domo: {resp.text}")
            logger.error(f"Failed to upload data to Domo: {resp.text}")
        else:
            print("Data upload to Domo successful.")
            logger.info("Data upload to Domo successful.")
        if resp.status_code not in (200, 204):
            resp.raise_for_status()
        return resp.status_code in (200, 204)
    except Exception as e:
        print(f"Exception during upload_to_domo: {e}")
        logger.exception(f"Exception during upload_to_domo: {e}")
        return False
    finally:
        for handler in logger.handlers:
            handler.flush()

# Add this at the bottom to test logging and function call directly
if __name__ == "__main__":
    # Example test data with correct columns for Domo schema
    test_data = [{
        "date": "2025-06-11",
        "total_active_users": 53,
        "total_engaged_users": 45,
        "ide_completions_users": 37,
        "ide_chat_users": 34,
        "dotcom_chat_users": 0,
        "pr_users": 0,
        "editor": "vscode",
        "model": "default",
        "is_custom_model": False,
        "language": "typescript",
        "code_suggestions": 2940,
        "code_acceptances": 739,
        "lines_suggested": 4190,
        "lines_accepted": 542,
        "chat_count": 0,
        "chat_insertions": 0,
        "chat_copies": 0,
        "pr_summaries": 0,
        "repository": ""
    }]
    print("Running domo_integration.py as main, testing upload_to_domo with sample data.")
    logger.info("Running domo_integration.py as main, testing upload_to_domo with sample data.")
    upload_to_domo(test_data, append=False)