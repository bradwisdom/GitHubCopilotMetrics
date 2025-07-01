"""
GitHub Copilot Metrics Fetcher

This script fetches GitHub Copilot usage metrics from the GitHub API and processes them
for analysis and visualization. It supports incremental data fetching, automatic Domo
integration, and various run modes for different use cases.

Features:
- Incremental data fetching (only retrieves new data since last run)
- Automatic data flattening for analytics consumption
- Domo integration with append capability (default)
- Flexible run modes (normal, rerun, custom date ranges)
- Comprehensive logging and error handling
- Command-line interface for various scenarios

Requirements:
- GitHub Personal Access Token (GITHUB_PAT) with Copilot metrics access
- GitHub Enterprise/Organization name (GITHUB_ORG_NAME)
- Environment variables configured in ../config/.env
- domo_integration.py module for Domo uploads

Usage Examples:
    # Normal incremental run (default - appends to Domo)
    python get_metrics.py
    
    # Force rerun from last run date to yesterday
    python get_metrics.py --rerun
    
    # Rerun without uploading to Domo (writes timestamped file)
    python get_metrics.py --rerun --no-domo
    
    # Custom date range with Domo upload
    python get_metrics.py --rerun --start-date 2025-06-01 --end-date 2025-06-30
    
    # Custom date range without Domo upload
    python get_metrics.py --rerun --no-domo --start-date 2025-06-01 --end-date 2025-06-30

Command Line Arguments:
    --rerun              Force rerun ignoring up-to-date check
    --no-domo           Skip Domo upload, only write to output file
    --start-date YYYY-MM-DD  Override start date (requires --rerun)
    --end-date YYYY-MM-DD    Override end date (requires --rerun)

Output Files:
    - Normal runs: ../output/metrics.json
    - No-domo runs: ../output/metrics_rerun_YYYYMMDD_HHMMSS.json
    - Last run tracking: ../output/last_copilot_run.txt
    - Logs: ../logs/get_metrics.log

Data Processing:
    The script flattens the nested GitHub API response into a tabular format with these columns:
    - date, total_active_users, total_engaged_users
    - ide_completions_users, ide_chat_users, dotcom_chat_users, pr_users
    - editor, model, is_custom_model, language
    - code_suggestions, code_acceptances, lines_suggested, lines_accepted
    - chat_count, chat_insertions, chat_copies, pr_summaries, repository

API Limitations:
    - GitHub API returns data for up to 28 days per request
    - Data is only available up to yesterday (current date - 1)
    - Rate limits apply to API requests
"""

import requests
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import sys
import argparse

# Setup logging
LOGS_DIR = os.path.join(os.path.dirname(__file__), '../logs')
os.makedirs(LOGS_DIR, exist_ok=True)
log_file = os.path.join(LOGS_DIR, 'get_metrics.log')
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '../config/.env'))

# Import upload_to_domo from domo_integration.py
sys.path.append(os.path.dirname(__file__))
from domo_integration import upload_to_domo

# --- Configuration ---
GITHUB_PAT = os.environ.get("GITHUB_PAT")
GITHUB_ORG_NAME = os.environ.get("GITHUB_ORG_NAME")

# --- Constants ---
API_VERSION_HEADER = "2022-11-28" # Recommended API version for Copilot metrics
MAX_DAYS_PER_REQUEST = 27 # The API typically returns data for up to 27 days prior
LAST_RUN_FILE = os.path.join(os.path.dirname(__file__), '..', 'output', 'last_copilot_run.txt')

def get_last_run_date():
    """Reads the last successful run date from a file."""
    if os.path.exists(LAST_RUN_FILE):
        with open(LAST_RUN_FILE, 'r') as f:
            date_str = f.read().strip()
            if date_str:
                return datetime.strptime(date_str, "%Y-%m-%d").date()
    return None

def update_last_run_date(date):
    """Writes the current run date to a file."""
    os.makedirs(os.path.dirname(LAST_RUN_FILE), exist_ok=True)
    with open(LAST_RUN_FILE, 'w') as f:
        f.write(date.strftime("%Y-%m-%d"))

def fetch_copilot_metrics(start_date, end_date):
    """
    Fetches GitHub Copilot metrics for a given date range.
    The API typically provides data for the last 28 days.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_PAT}",
        "X-GitHub-Api-Version": API_VERSION_HEADER
    }

    # Construct the base URL for organization metrics
    base_url = f"https://api.github.com/enterprises/{GITHUB_ORG_NAME}/copilot/metrics"

    all_metrics = []
    current_start = start_date

    debug_first_response = None
    while current_start <= end_date:
        # The API only returns data up to yesterday.
        # Ensure we don't try to fetch data for today or the future.
        fetch_until = min(end_date, datetime.now().date() - timedelta(days=1))

        # Calculate days to fetch, up to MAX_DAYS_PER_REQUEST
        days_to_fetch = (fetch_until - current_start).days + 1
        if days_to_fetch > MAX_DAYS_PER_REQUEST:
            days_to_fetch = MAX_DAYS_PER_REQUEST

        # Adjust the end date for the current API call
        temp_end = current_start + timedelta(days=days_to_fetch - 1)

        params = {
            "since": current_start.isoformat(),
            "until": temp_end.isoformat(),
            "per_page": MAX_DAYS_PER_REQUEST # Max per_page is 28 for metrics
        }
        print(f"Fetching data from {current_start} to {temp_end}...")
        logging.info(f"Fetching data from {current_start} to {temp_end}...")

        response = requests.get(base_url, headers=headers, params=params)
        print(f"DEBUG: Request URL: {response.url}")
        print(f"DEBUG: Status Code: {response.status_code}")
        logging.debug(f"Request URL: {response.url}")
        logging.debug(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if debug_first_response is None:
                debug_first_response = data
                print("DEBUG: First API response sample:")
                print(json.dumps(data, indent=2)[:2000])  # Print first 2000 chars for inspection
                logging.debug(f"First API response sample: {json.dumps(data, indent=2)[:2000]}")

            if isinstance(data, dict) and "metrics" in data:
                all_metrics.extend(data["metrics"])
            elif isinstance(data, list):
                all_metrics.extend(data)
            else:
                print(f"DEBUG: Unexpected API response structure for {current_start} to {temp_end}: {data}")
                logging.warning(f"Unexpected API response structure for {current_start} to {temp_end}: {data}")
            current_start = temp_end + timedelta(days=1)
        else:
            print(f"Error fetching data: {response.status_code} - {response.text}")
            logging.error(f"Error fetching data: {response.status_code} - {response.text}")
            return None
    
    # Log the number of metrics retrieved
    logging.info(f"Retrieved {len(all_metrics)} raw metrics from API")
    
    if not all_metrics:
        print("DEBUG: No metrics returned from API for the requested date range.")
        logging.info("No metrics returned from API for the requested date range.")
        if debug_first_response is not None:
            print("DEBUG: Example API response (no metrics):")
            print(json.dumps(debug_first_response, indent=2)[:2000])
            logging.debug(f"Example API response (no metrics): {json.dumps(debug_first_response, indent=2)[:2000]}")
    return all_metrics

def flatten_metrics(metrics):
    """
    Flattens nested Copilot metrics into a list of dicts with the expected columns for Domo.
    """
    records = []
    for day in metrics:
        base = {
            "date": day.get("date"),
            "total_active_users": day.get("total_active_users", 0),
            "total_engaged_users": day.get("total_engaged_users", 0),
            "ide_completions_users": day.get("copilot_ide_code_completions", {}).get("total_engaged_users", 0),
            "ide_chat_users": day.get("copilot_ide_chat", {}).get("total_engaged_users", 0),
            "dotcom_chat_users": day.get("copilot_dotcom_chat", {}).get("total_engaged_users", 0),
            "pr_users": day.get("copilot_dotcom_pull_requests", {}).get("total_engaged_users", 0),
        }
        # IDE code completions by language/editor/model
        completions = day.get("copilot_ide_code_completions", {}).get("editors", [])
        for editor in completions:
            for model in editor.get("models", []):
                for lang in model.get("languages", []):
                    records.append({
                        **base,
                        "editor": editor.get("name", ""),
                        "model": model.get("name", ""),
                        "is_custom_model": model.get("is_custom_model", False),
                        "language": lang.get("name", ""),
                        "code_suggestions": lang.get("total_code_suggestions", 0),
                        "code_acceptances": lang.get("total_code_acceptances", 0),
                        "lines_suggested": lang.get("total_code_lines_suggested", 0),
                        "lines_accepted": lang.get("total_code_lines_accepted", 0),
                        "chat_count": 0,
                        "chat_insertions": 0,
                        "chat_copies": 0,
                        "pr_summaries": 0,
                        "repository": ""
                    })
        # IDE chat metrics
        ide_chat = day.get("copilot_ide_chat", {}).get("editors", [])
        for editor in ide_chat:
            for model in editor.get("models", []):
                records.append({
                    **base,
                    "editor": editor.get("name", ""),
                    "model": model.get("name", ""),
                    "is_custom_model": model.get("is_custom_model", False),
                    "language": "",
                    "code_suggestions": 0,
                    "code_acceptances": 0,
                    "lines_suggested": 0,
                    "lines_accepted": 0,
                    "chat_count": model.get("total_chats", 0),
                    "chat_insertions": model.get("total_chat_insertion_events", 0),
                    "chat_copies": model.get("total_chat_copy_events", 0),
                    "pr_summaries": 0,
                    "repository": ""
                })
        # Dotcom chat metrics
        dotcom_chat = day.get("copilot_dotcom_chat", {}).get("models", [])
        for model in dotcom_chat:
            records.append({
                **base,
                "editor": "",
                "model": model.get("name", ""),
                "is_custom_model": model.get("is_custom_model", False),
                "language": "",
                "code_suggestions": 0,
                "code_acceptances": 0,
                "lines_suggested": 0,
                "lines_accepted": 0,
                "chat_count": model.get("total_chats", 0),
                "chat_insertions": 0,
                "chat_copies": 0,
                "pr_summaries": 0,
                "repository": ""
            })
        # PR summaries
        pr_repos = day.get("copilot_dotcom_pull_requests", {}).get("repositories", [])
        for repo in pr_repos:
            for model in repo.get("models", []):
                records.append({
                    **base,
                    "editor": "",
                    "model": model.get("name", ""),
                    "is_custom_model": model.get("is_custom_model", False),
                    "language": "",
                    "code_suggestions": 0,
                    "code_acceptances": 0,
                    "lines_suggested": 0,
                    "lines_accepted": 0,
                    "chat_count": 0,
                    "chat_insertions": 0,
                    "chat_copies": 0,
                    "pr_summaries": model.get("total_pr_summaries_created", 0),
                    "repository": repo.get("name", "")
                })
    
    # Log the number of processed records
    logging.info(f"Processed {len(records)} flattened records from {len(metrics)} days of metrics")
    
    return records

def write_metrics_to_json(metrics_data, output_file, upload_to_domo_flag=True):
    """Writes the fetched metrics to a JSON file (flattened)."""
    if not metrics_data:
        print("No new metrics to write.")
        logging.info("No new metrics to write.")
        return
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Flatten before writing
    flattened = flatten_metrics(metrics_data)
    output_path = os.path.join(output_dir, output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(flattened, f, indent=2)
    print(f"Metrics written to {output_path}")
    logging.info(f"Metrics written to {output_path} - {len(flattened)} records")

    # --- Upload to Domo after writing JSON (only if flag is True) ---
    if upload_to_domo_flag:
        print("Uploading metrics to Domo...")
        logging.info("Uploading metrics to Domo...")
        success = upload_to_domo(flattened, append=True)
        if success:
            print("Metrics uploaded to Domo successfully.")
            logging.info("Metrics uploaded to Domo successfully.")
        else:
            print("Failed to upload metrics to Domo.")
            logging.error("Failed to upload metrics to Domo.")
    else:
        print("Skipping Domo upload as requested.")
        logging.info("Skipping Domo upload as requested.")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Fetch GitHub Copilot metrics and optionally upload to Domo')
    parser.add_argument('--rerun', action='store_true', 
                        help='Force rerun from last run date to yesterday, ignoring up-to-date check')
    parser.add_argument('--no-domo', action='store_true', 
                        help='Skip uploading to Domo, only write to output file')
    parser.add_argument('--start-date', type=str, 
                        help='Override start date (YYYY-MM-DD format). Only used with --rerun')
    parser.add_argument('--end-date', type=str,
                        help='Override end date (YYYY-MM-DD format). Only used with --rerun')
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    github_pat = os.getenv("GITHUB_PAT")
    github_org_name = os.getenv("GITHUB_ORG_NAME")
    if not github_pat:
        print("Error: GitHub Personal Access Token (GITHUB_PAT) not set as environment variable.")
        logging.error("GitHub Personal Access Token (GITHUB_PAT) not set as environment variable.")
        print("Please set it before running the script.")
        exit(1)
    if not github_org_name:
        print("Error: GitHub Organization Name (GITHUB_ORG_NAME) not set as environment variable.")
        logging.error("GitHub Organization Name (GITHUB_ORG_NAME) not set as environment variable.")
        print("Please set it before running the script.")
        exit(1)

    last_run_date = get_last_run_date()
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    # Determine if we should upload to Domo (default True unless --no-domo specified)
    upload_to_domo_flag = not args.no_domo

    if args.rerun:
        # Force rerun mode
        print("Running in rerun mode...")
        logging.info("Running in rerun mode...")
        
        if args.start_date and args.end_date:
            # Use custom date range
            try:
                start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
                end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
                print(f"Using custom date range: {start_date} to {end_date}")
                logging.info(f"Using custom date range: {start_date} to {end_date}")
            except ValueError as e:
                print(f"Error parsing dates: {e}")
                logging.error(f"Error parsing dates: {e}")
                exit(1)
        elif last_run_date:
            # Use last run date to yesterday
            start_date = last_run_date + timedelta(days=1)
            end_date = yesterday
            print(f"Rerunning from last run date + 1: {start_date} to {end_date}")
            logging.info(f"Rerunning from last run date + 1: {start_date} to {end_date}")
        else:
            # No last run date, fetch last MAX_DAYS_PER_REQUEST days
            start_date = yesterday - timedelta(days=MAX_DAYS_PER_REQUEST - 1)
            if start_date < datetime(2023, 1, 1).date():
                start_date = datetime(2023, 1, 1).date()
            end_date = yesterday
            print(f"No last run date found, fetching last {MAX_DAYS_PER_REQUEST} days: {start_date} to {end_date}")
            logging.info(f"No last run date found, fetching last {MAX_DAYS_PER_REQUEST} days: {start_date} to {end_date}")
    else:
        # Normal mode - check if up to date
        if last_run_date:
            # If last run was yesterday or today, no new data to fetch for previous days
            if last_run_date >= yesterday:
                print("Already up-to-date with Copilot metrics. Last run was today or yesterday.")
                logging.info("Already up-to-date with Copilot metrics. Last run was today or yesterday.")
                print("Use --rerun flag to force rerun.")
                return
            # Start fetching from the day after the last run and go until yesterday
            start_date = last_run_date + timedelta(days=1)
            end_date = yesterday
        else:
            # First run or no last run date found, fetch data for the last MAX_DAYS_PER_REQUEST days
            start_date = yesterday - timedelta(days=MAX_DAYS_PER_REQUEST - 1)
            if start_date < datetime(2023, 1, 1).date():
                start_date = datetime(2023, 1, 1).date()
            end_date = yesterday

    print(f"Attempting to fetch Copilot metrics from {start_date} to {end_date}...")
    logging.info(f"Attempting to fetch Copilot metrics from {start_date} to {end_date}...")
    metrics = fetch_copilot_metrics(start_date, end_date)

    if metrics:
        metrics_with_date = [m for m in metrics if "date" in m or "day" in m]
        if not metrics_with_date:
            print("No valid metrics with 'date' or 'day' field found in API response. Example response:", metrics[0] if metrics else "No data")
            logging.warning("No valid metrics with 'date' or 'day' field found in API response.")
            return
        
        # Determine output filename
        if args.no_domo:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"metrics_rerun_{timestamp}.json"
        else:
            output_file = "metrics.json"
        
        metrics_with_date.sort(key=lambda x: x.get("date") or x.get("day"))
        write_metrics_to_json(metrics_with_date, output_file, upload_to_domo_flag)
        
        # Update last run date only if not in no-domo mode (to avoid affecting normal runs)
        if not args.no_domo:
            latest = metrics_with_date[-1]
            latest_date_str = latest.get("date") or latest.get("day")
            try:
                latest_day = datetime.strptime(latest_date_str, "%Y-%m-%d").date()
                update_last_run_date(latest_day)
                print(f"Last run date updated to {latest_day}.")
                logging.info(f"Last run date updated to {latest_day}.")
            except Exception as e:
                print(f"DEBUG: Could not parse latest date from metrics: {latest_date_str} ({e})")
                logging.error(f"Could not parse latest date from metrics: {latest_date_str} ({e})")
        else:
            print("Skipping last run date update for no-domo run.")
            logging.info("Skipping last run date update for no-domo run.")
    else:
        print("Failed to retrieve any new Copilot metrics.")
        logging.error("Failed to retrieve any new Copilot metrics.")

if __name__ == "__main__":
    main()