import os
import requests
import json
import pandas as pd
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../config/.env'))

# GitHub configuration
GITHUB_PAT = os.getenv("GITHUB_PAT")
GITHUB_ORG_NAME = os.getenv("GITHUB_ORG_NAME")

# Domo configuration
DOMO_CLIENT_ID = os.getenv("DOMO_CLIENT_ID")
DOMO_CLIENT_SECRET = os.getenv("DOMO_CLIENT_SECRET")
DOMO_API_HOST = "https://api.domo.com"

# Set up logging
LOGS_DIR = os.path.join(os.path.dirname(__file__), '../logs')
os.makedirs(LOGS_DIR, exist_ok=True)
log_file = os.path.join(LOGS_DIR, 'load_github_user_domo.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_domo_token():
    """Get Domo API access token."""
    url = f"{DOMO_API_HOST}/oauth/token?grant_type=client_credentials&scope=data"
    logger.info("Requesting Domo token...")
    resp = requests.post(url, auth=(DOMO_CLIENT_ID, DOMO_CLIENT_SECRET))
    if resp.status_code != 200:
        logger.error(f"Failed to get Domo token: {resp.status_code} {resp.text}")
        resp.raise_for_status()
    logger.info("Successfully obtained Domo token")
    return resp.json()["access_token"]

def get_all_users_enterprise(enterprise, token):
    """Get all Copilot users for an enterprise from the Copilot billing seats API."""
    url = f"https://api.github.com/enterprises/{enterprise}/copilot/billing/seats"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    users = []
    page = 1
    per_page = 100
    
    logger.info(f"Fetching Copilot users for enterprise: {enterprise}")
    
    while True:
        params = {"per_page": per_page, "page": page}
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            logger.error(f"Failed to fetch Copilot seats: {resp.status_code} {resp.text}")
            break
        
        # Parse the response - it's a dict with 'seats' array, not a direct array
        response_data = resp.json()
        if isinstance(response_data, dict) and 'seats' in response_data:
            batch = response_data['seats']
        else:
            batch = response_data if isinstance(response_data, list) else []
        
        if not batch:
            break
        
        # Only include seat records with a valid user assignee
        for seat in batch:
            if not isinstance(seat, dict):
                continue
            assignee = seat.get("assignee")
            if isinstance(assignee, dict) and assignee.get("type") == "User":
                user = {
                    "user_id": assignee.get("id"),
                    "login": assignee.get("login"),
                    "name": assignee.get("name", ""),
                    "email": assignee.get("email", ""),
                    "avatar_url": assignee.get("avatar_url", ""),
                    "html_url": assignee.get("html_url", ""),
                    "site_admin": assignee.get("site_admin", False),
                    "copilot_enabled": "Yes",
                    "seat_created_at": seat.get("created_at", ""),
                    "pending_cancellation_date": seat.get("pending_cancellation_date", ""),
                    "plan_type": seat.get("plan_type", ""),
                    "last_activity_at": seat.get("last_activity_at", ""),
                    "last_activity_editor": seat.get("last_activity_editor", "")
                }
                # Add assigning team info if present
                assigning_team = seat.get("assigning_team")
                if isinstance(assigning_team, dict):
                    user["assigning_team_id"] = assigning_team.get("id", "")
                    user["assigning_team_name"] = assigning_team.get("name", "")
                    user["assigning_team_slug"] = assigning_team.get("slug", "")
                    user["assigning_team_html_url"] = assigning_team.get("html_url", "")
                    user["has_team_assignment"] = True
                else:
                    user["assigning_team_id"] = ""
                    user["assigning_team_name"] = ""
                    user["assigning_team_slug"] = ""
                    user["assigning_team_html_url"] = ""
                    user["has_team_assignment"] = False
                users.append(user)
        
        if len(batch) < per_page:
            break
        page += 1
    
    logger.info(f"Found {len(users)} Copilot users")
    return users

def get_enterprise_teams(enterprise, token):
    """Fetch all teams for a GitHub Enterprise."""
    url = f"https://api.github.com/enterprises/{enterprise}/teams"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    teams = []
    page = 1
    per_page = 100
    
    logger.info(f"Fetching teams for enterprise: {enterprise}")
    
    while True:
        params = {"per_page": per_page, "page": page}
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            logger.error(f"Failed to fetch enterprise teams: {resp.status_code} {resp.text}")
            break
        batch = resp.json()
        if not batch:
            break
        teams.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    
    logger.info(f"Found {len(teams)} teams")
    return teams

def get_enterprise_team_members(enterprise, team_id, token):
    """Fetch all members for a given enterprise team using team ID."""
    url = f"https://api.github.com/enterprises/{enterprise}/teams/{team_id}/memberships"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    members = []
    page = 1
    per_page = 100
    
    while True:
        params = {"per_page": per_page, "page": page}
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            logger.warning(f"Failed to fetch memberships for team {team_id}: {resp.status_code}")
            break
        batch = resp.json()
        if not batch:
            break
        # Extract user info from memberships
        for membership in batch:
            if isinstance(membership, dict) and 'user' in membership:
                members.append(membership['user'])
        if len(batch) < per_page:
            break
        page += 1
    
    return members

def flatten_user_for_domo(user, teams_list):
    """Flatten user data for Domo upload compatibility."""
    flattened_records = []
    
    if teams_list:
        # Create one record per team membership
        for team in teams_list:
            record = {
                "user_id": user.get("user_id"),
                "login": user.get("login"),
                "name": user.get("name", ""),
                "email": user.get("email", ""),
                "avatar_url": user.get("avatar_url", ""),
                "html_url": user.get("html_url", ""),
                "site_admin": user.get("site_admin", False),
                "copilot_enabled": user.get("copilot_enabled", "Yes"),
                "seat_created_at": user.get("seat_created_at", ""),
                "pending_cancellation_date": user.get("pending_cancellation_date", ""),
                "plan_type": user.get("plan_type", ""),
                "last_activity_at": user.get("last_activity_at", ""),
                "last_activity_editor": user.get("last_activity_editor", ""),
                "team_id": team.get("id"),
                "team_name": team.get("name"),
                "team_slug": team.get("slug"),
                "team_html_url": team.get("html_url", ""),
                "has_team_assignment": True
            }
            flattened_records.append(record)
    else:
        # User with no team assignments or use assigning_team from seat
        record = {
            "user_id": user.get("user_id"),
            "login": user.get("login"),
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "avatar_url": user.get("avatar_url", ""),
            "html_url": user.get("html_url", ""),
            "site_admin": user.get("site_admin", False),
            "copilot_enabled": user.get("copilot_enabled", "Yes"),
            "seat_created_at": user.get("seat_created_at", ""),
            "pending_cancellation_date": user.get("pending_cancellation_date", ""),
            "plan_type": user.get("plan_type", ""),
            "last_activity_at": user.get("last_activity_at", ""),
            "last_activity_editor": user.get("last_activity_editor", ""),
            "team_id": user.get("assigning_team_id", ""),
            "team_name": user.get("assigning_team_name", ""),
            "team_slug": user.get("assigning_team_slug", ""),
            "team_html_url": user.get("assigning_team_html_url", ""),
            "has_team_assignment": user.get("has_team_assignment", False)
        }
        flattened_records.append(record)
    
    return flattened_records

def get_dataset_schema(dataset_id):
    """Get the schema of an existing Domo dataset."""
    token = get_domo_token()
    url = f"{DOMO_API_HOST}/v1/datasets/{dataset_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        dataset_info = resp.json()
        schema = dataset_info.get("schema", {}).get("columns", [])
        logger.info(f"Dataset schema has {len(schema)} columns")
        for col in schema:
            logger.debug(f"  {col.get('name')} ({col.get('type')})")
        return schema
    else:
        logger.error(f"Failed to get dataset schema: {resp.status_code} {resp.text}")
        return None

def validate_data_against_schema(data, schema):
    """Validate data structure against Domo dataset schema."""
    if not schema:
        logger.warning("No schema provided for validation")
        return data
    
    schema_columns = {col['name']: col['type'] for col in schema}
    df = pd.DataFrame(data)
    
    # Add missing columns with appropriate default values
    for col_name, col_type in schema_columns.items():
        if col_name not in df.columns:
            if col_type in ['LONG', 'DECIMAL']:
                df[col_name] = 0
            elif col_type == 'STRING':
                df[col_name] = ""
            else:
                df[col_name] = None
            logger.info(f"Added missing column '{col_name}' with default value")
    
    # Remove extra columns not in schema
    extra_columns = set(df.columns) - set(schema_columns.keys())
    if extra_columns:
        logger.warning(f"Removing extra columns not in schema: {extra_columns}")
        df = df.drop(columns=list(extra_columns))
    
    # Reorder columns to match schema order
    schema_order = [col['name'] for col in schema]
    df = df[schema_order]
    
    # Convert data types
    for col in schema:
        col_name = col['name']
        col_type = col['type']
        
        if col_name in df.columns:
            try:
                if col_type == 'LONG':
                    df[col_name] = pd.to_numeric(df[col_name], errors='coerce').fillna(0).astype(int)
                elif col_type == 'DECIMAL':
                    df[col_name] = pd.to_numeric(df[col_name], errors='coerce').fillna(0.0)
                elif col_type == 'STRING':
                    df[col_name] = df[col_name].astype(str).fillna("")
                elif col_type in ['DATE', 'DATETIME']:
                    # Keep as string for Domo upload
                    df[col_name] = df[col_name].astype(str).fillna("")
            except Exception as e:
                logger.warning(f"Failed to convert column '{col_name}' to type '{col_type}': {e}")
    
    logger.info(f"Data validated and formatted for schema compliance")
    return df.to_dict('records')

def upload_to_domo_dataset(dataset_id, data):
    """Upload data to Domo dataset using REPLACE mode with schema validation."""
    if not data:
        logger.warning("No data to upload to Domo")
        return False
    
    # Get dataset schema first
    schema = get_dataset_schema(dataset_id)
    if not schema:
        logger.error("Could not retrieve dataset schema - upload may fail")
        # Continue anyway, but log the issue
    else:
        # Validate and format data against schema
        data = validate_data_against_schema(data, schema)
    
    token = get_domo_token()
    url = f"{DOMO_API_HOST}/v1/datasets/{dataset_id}/data?updateMethod=REPLACE"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "text/csv"
    }
    
    # Convert to DataFrame and then CSV
    df = pd.DataFrame(data)
    
    # Log data sample for debugging
    logger.debug(f"Data sample (first 3 rows):")
    for i, row in df.head(3).iterrows():
        logger.debug(f"  Row {i}: {dict(row)}")
    
    csv_data = df.to_csv(index=False)
    
    logger.info(f"Uploading {len(data)} records to Domo dataset {dataset_id} (REPLACE mode)")
    logger.debug(f"CSV Preview: {csv_data[:500]}")
    
    try:
        resp = requests.put(url, headers=headers, data=csv_data.encode("utf-8"))
        logger.info(f"Domo upload response status: {resp.status_code}")
        
        if resp.status_code in (200, 204):
            logger.info("Data upload to Domo successful")
            return True
        else:
            logger.error(f"Failed to upload data to Domo: {resp.status_code} {resp.text}")
            
            # Try to provide more helpful error information
            if resp.status_code == 400:
                logger.error("400 Bad Request usually indicates:")
                logger.error("  - Schema mismatch (column names/types don't match)")
                logger.error("  - Data format issues (invalid dates, etc.)")
                logger.error("  - Missing required columns")
                
                if schema:
                    logger.error("Expected schema:")
                    for col in schema:
                        logger.error(f"  {col['name']} ({col['type']})")
                
                logger.error("Actual data columns:")
                for col in df.columns:
                    logger.error(f"  {col} (sample: {df[col].iloc[0] if len(df) > 0 else 'N/A'})")
            
            return False
            
    except Exception as e:
        logger.exception(f"Exception during Domo upload: {e}")
        return False

def main():
    """Main function to pull GitHub data and upload to Domo."""
    if not GITHUB_PAT or not GITHUB_ORG_NAME:
        logger.error("GITHUB_PAT or GITHUB_ORG_NAME not set in .env")
        return False
    
    if not DOMO_CLIENT_ID or not DOMO_CLIENT_SECRET:
        logger.error("DOMO_CLIENT_ID or DOMO_CLIENT_SECRET not set in .env")
        return False
    
    try:
        # Fetch GitHub data
        logger.info("=" * 60)
        logger.info("Starting GitHub User Data Collection and Domo Upload")
        logger.info("=" * 60)
        
        users = get_all_users_enterprise(GITHUB_ORG_NAME, GITHUB_PAT)
        teams = get_enterprise_teams(GITHUB_ORG_NAME, GITHUB_PAT)
        
        # Map team members to users
        team_mapping = {}  # user_login -> list of team objects
        for team in teams:
            team_id = team.get("id")
            team_name = team.get("name")
            if not team_id:
                continue
            members = get_enterprise_team_members(GITHUB_ORG_NAME, team_id, GITHUB_PAT)
            logger.info(f"Team '{team_name}' (ID: {team_id}): {len(members)} members")
            
            for member in members:
                member_login = member.get("login")
                if member_login:
                    if member_login not in team_mapping:
                        team_mapping[member_login] = []
                    team_mapping[member_login].append(team)
        
        # Flatten data for Domo upload
        flattened_users = []
        for user in users:
            user_login = user.get("login")
            user_teams = team_mapping.get(user_login, [])
            user_records = flatten_user_for_domo(user, user_teams)
            flattened_users.extend(user_records)
        
        logger.info(f"Flattened {len(users)} users into {len(flattened_users)} records for Domo")
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        # Save data locally for reference
        output_file = os.path.join(output_dir, "github_org_users.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
        logger.info(f"Original user data saved to {output_file}")
        
        flattened_output_file = os.path.join(output_dir, "github_users_flattened.json")
        with open(flattened_output_file, "w", encoding="utf-8") as f:
            json.dump(flattened_users, f, indent=2)
        logger.info(f"Flattened user data saved to {flattened_output_file}")
        
        # Upload to Domo - Check for dataset ID environment variable
        github_users_dataset_id = os.getenv("GITHUB_USERS_DATASET_ID")
        if not github_users_dataset_id:
            logger.warning("GITHUB_USERS_DATASET_ID not set - skipping Domo upload")
            logger.info("To upload to Domo, set GITHUB_USERS_DATASET_ID in your .env file")
            return True
        
        success = upload_to_domo_dataset(github_users_dataset_id, flattened_users)
        
        if success:
            logger.info("=" * 60)
            logger.info("SUCCESS: GitHub user data uploaded to Domo")
            logger.info(f"Users processed: {len(users)}")
            logger.info(f"Teams processed: {len(teams)}")
            logger.info(f"Flattened records: {len(flattened_users)}")
            logger.info("=" * 60)
            return True
        else:
            logger.error("FAILED: Domo upload failed")
            return False
            
    except Exception as e:
        logger.exception(f"Error in main execution: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
