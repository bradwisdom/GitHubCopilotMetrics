"""
DEPRECATED: This script has been replaced by create_domo_dataset_v2.py

The v2 version provides:
- Better schema inference from JSON data
- Support for any JSON structure (not just metrics)
- Improved error handling and validation
- Optional data upload functionality

Please use create_domo_dataset_v2.py instead:

Usage examples:
    python3 create_domo_dataset_v2.py metrics.json "GitHub Copilot Metrics"
    python3 create_domo_dataset_v2.py github_users_flattened.json "GitHub Users" "User-team data" --upload-data

For legacy compatibility, the original functionality is preserved below.
"""

import os
import sys

def main():
    print("⚠️  DEPRECATED: create_domo_dataset.py has been replaced")
    print("📄 Please use create_domo_dataset_v2.py instead")
    print("")
    print("New usage:")
    print("  python3 create_domo_dataset_v2.py <json_file> <dataset_name> [description] [--upload-data]")
    print("")
    print("Examples:")
    print("  python3 create_domo_dataset_v2.py metrics.json 'GitHub Copilot Metrics'")
    print("  python3 create_domo_dataset_v2.py github_users_flattened.json 'GitHub Users' 'User-team relationships' --upload-data")
    print("")
    
    # Provide automatic migration if arguments are provided
    if len(sys.argv) >= 3:
        print("🔄 Attempting to run create_domo_dataset_v2.py with your arguments...")
        import subprocess
        
        # Map old arguments to new format
        old_args = sys.argv[1:]  # Remove script name
        new_script = os.path.join(os.path.dirname(__file__), 'create_domo_dataset_v2.py')
        
        try:
            result = subprocess.run(['python3', new_script] + old_args, 
                                  capture_output=False, 
                                  text=True)
            sys.exit(result.returncode)
        except Exception as e:
            print(f"❌ Failed to run v2 script: {e}")
            print("Please run create_domo_dataset_v2.py manually")
            sys.exit(1)
    else:
        print("❌ No arguments provided")
        sys.exit(1)

if __name__ == "__main__":
    main()

# Original code preserved for reference (commented out)
"""
import os
import json
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../config/.env'))

DOMO_CLIENT_ID = os.getenv("DOMO_CLIENT_ID")
DOMO_CLIENT_SECRET = os.getenv("DOMO_CLIENT_SECRET")
DOMO_API_HOST = "https://api.domo.com"

# Reference columns from copilotmetrics/output/copilot_metrics_*.json
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
    "repository",
    # Optionally add more columns if present in your data
]

def get_domo_token():
    url = f"{DOMO_API_HOST}/oauth/token?grant_type=client_credentials&scope=data"
    resp = requests.post(url, auth=(DOMO_CLIENT_ID, DOMO_CLIENT_SECRET))
    resp.raise_for_status()
    return resp.json()["access_token"]

def flatten_json_records(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)
    # Use pandas.DataFrame to ensure columns order and fill missing columns with None
    df = pd.DataFrame(data)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = None
    df = df[COLUMNS]
    return df

def infer_schema_from_df(df):
    schema = []
    for col in df.columns:
        dtype = df[col].dtype
        if pd.api.types.is_integer_dtype(dtype):
            domo_type = "LONG"
        elif pd.api.types.is_float_dtype(dtype):
            domo_type = "DOUBLE"
        elif col == "is_custom_model":
            domo_type = "STRING"  # Boolean as STRING for Domo compatibility
        else:
            domo_type = "STRING"
        schema.append({"name": col, "type": domo_type})
    return schema

def create_domo_dataset(dataset_name, schema):
    token = get_domo_token()
    url = f"{DOMO_API_HOST}/v1/datasets"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": dataset_name,
        "description": "Daily GitHub Copilot metrics dataset (flattened, 22 columns, copilotmetrics compatible)",
        "rows": 0,
        "schema": {"columns": schema}
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["id"]

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python create_domo_dataset.py <metrics_json_path> <dataset_name>")
        exit(1)
    metrics_json_path = sys.argv[1]
    dataset_name = sys.argv[2]
    df = flatten_json_records(metrics_json_path)
    schema = infer_schema_from_df(df)
    dataset_id = create_domo_dataset(dataset_name, schema)
    print(f"Created Domo dataset '{dataset_name}' with ID: {dataset_id}")
    print("Columns:")
    for col in schema:
        print(f"  - {col['name']} ({col['type']})")
"""