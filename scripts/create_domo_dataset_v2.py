import os
import json
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../config/.env'))

DOMO_CLIENT_ID = os.getenv("DOMO_CLIENT_ID")
DOMO_CLIENT_SECRET = os.getenv("DOMO_CLIENT_SECRET")
DOMO_API_HOST = "https://api.domo.com"

def get_domo_token():
    """Get Domo API access token."""
    url = f"{DOMO_API_HOST}/oauth/token?grant_type=client_credentials&scope=data"
    resp = requests.post(url, auth=(DOMO_CLIENT_ID, DOMO_CLIENT_SECRET))
    if resp.status_code != 200:
        print(f"Failed to get Domo token: {resp.status_code} {resp.text}")
        resp.raise_for_status()
    return resp.json()["access_token"]

def load_and_flatten_json(json_path):
    """Load JSON file and convert to DataFrame for schema analysis."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Handle both list of objects and single object
    if isinstance(data, dict):
        data = [data]
    elif not isinstance(data, list):
        raise ValueError("JSON file must contain a list of objects or a single object")
    
    if not data:
        raise ValueError("JSON file is empty or contains no data")
    
    # Convert to DataFrame for easier schema inference
    df = pd.DataFrame(data)
    return df

def infer_domo_schema_from_df(df):
    """Infer Domo schema from DataFrame columns and data types."""
    schema = []
    
    for col in df.columns:
        # Get the column data type
        dtype = df[col].dtype
        sample_values = df[col].dropna().head(5).tolist()
        
        # Determine Domo data type based on pandas dtype and sample values
        if pd.api.types.is_integer_dtype(dtype):
            domo_type = "LONG"
        elif pd.api.types.is_float_dtype(dtype):
            domo_type = "DECIMAL"
        elif pd.api.types.is_bool_dtype(dtype):
            domo_type = "STRING"  # Domo handles booleans as strings
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            domo_type = "DATETIME"
        else:
            # Check if string column contains date-like values
            if col.lower() in ['date', 'created_at', 'updated_at', 'last_activity_at'] or 'date' in col.lower():
                # Sample a few values to see if they look like dates
                if sample_values and any('T' in str(val) or '-' in str(val) for val in sample_values[:3]):
                    if any('T' in str(val) and ':' in str(val) for val in sample_values[:3]):
                        domo_type = "DATETIME"
                    else:
                        domo_type = "DATE"
                else:
                    domo_type = "STRING"
            else:
                domo_type = "STRING"
        
        schema.append({
            "name": col,
            "type": domo_type
        })
    
    return schema

def create_domo_dataset(dataset_name, description, schema):
    """Create a new Domo dataset with the specified schema."""
    token = get_domo_token()
    url = f"{DOMO_API_HOST}/v1/datasets"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": dataset_name,
        "description": description,
        "rows": 0,
        "schema": {"columns": schema}
    }
    
    print(f"Creating Domo dataset: {dataset_name}")
    print(f"Description: {description}")
    print(f"Schema: {len(schema)} columns")
    
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 201:
        print(f"Failed to create dataset: {resp.status_code} {resp.text}")
        resp.raise_for_status()
    
    dataset = resp.json()
    return dataset["id"]

def upload_initial_data(dataset_id, df):
    """Upload the initial data from the JSON file to the newly created dataset."""
    token = get_domo_token()
    url = f"{DOMO_API_HOST}/v1/datasets/{dataset_id}/data"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "text/csv"
    }
    
    # Convert DataFrame to CSV
    csv_data = df.to_csv(index=False)
    
    print(f"Uploading {len(df)} rows of initial data...")
    resp = requests.put(url, headers=headers, data=csv_data.encode("utf-8"))
    
    if resp.status_code not in (200, 204):
        print(f"Failed to upload data: {resp.status_code} {resp.text}")
        resp.raise_for_status()
    
    print("✅ Initial data uploaded successfully")

def main():
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python create_domo_dataset_v2.py <json_file_path> <dataset_name> [description] [--upload-data]")
        print("Examples:")
        print("  python create_domo_dataset_v2.py output/github_org_users.json 'GitHub Users Dataset'")
        print("  python create_domo_dataset_v2.py output/github_users_flattened.json 'GitHub Users Flattened' 'User-team relationships' --upload-data")
        print("  python create_domo_dataset_v2.py output/metrics.json 'GitHub Copilot Metrics' 'Daily metrics' --upload-data")
        exit(1)
    
    json_file_path = sys.argv[1]
    dataset_name = sys.argv[2]
    description = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else f"Dataset created from {os.path.basename(json_file_path)}"
    upload_data = "--upload-data" in sys.argv
    
    # Handle relative paths - if path doesn't contain 'output/', prepend it
    if not os.path.isabs(json_file_path) and 'output/' not in json_file_path:
        json_file_path = os.path.join(os.path.dirname(__file__), '..', 'output', json_file_path)
    
    # Validate inputs
    if not os.path.exists(json_file_path):
        print(f"❌ JSON file not found: {json_file_path}")
        print("💡 Make sure to run data collection scripts first to generate JSON files in output/ directory")
        exit(1)
    
    if not DOMO_CLIENT_ID or not DOMO_CLIENT_SECRET:
        print("❌ Missing Domo credentials in .env file")
        print("Please set DOMO_CLIENT_ID and DOMO_CLIENT_SECRET")
        exit(1)
    
    try:
        # Load and analyze the JSON file
        print(f"📄 Loading JSON file: {json_file_path}")
        df = load_and_flatten_json(json_file_path)
        print(f"📊 Found {len(df)} records with {len(df.columns)} columns")
        
        # Infer schema
        schema = infer_domo_schema_from_df(df)
        
        # Create the dataset
        dataset_id = create_domo_dataset(dataset_name, description, schema)
        print(f"✅ Created Domo dataset '{dataset_name}' with ID: {dataset_id}")
        
        # Display schema
        print("\n📋 Dataset Schema:")
        for col in schema:
            print(f"  • {col['name']} ({col['type']})")
        
        # Upload initial data if requested
        if upload_data:
            upload_initial_data(dataset_id, df)
        
        print(f"\n🔧 Add this to your .env file:")
        print(f"# Dataset ID for {dataset_name}")
        env_var_name = dataset_name.upper().replace(' ', '_').replace('-', '_') + "_DATASET_ID"
        print(f"{env_var_name}={dataset_id}")
        
        print(f"\n🎉 Dataset creation completed successfully!")
        if not upload_data:
            print("💡 To upload the initial data, add --upload-data flag to your command")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
