# GitHub Copilot Metrics Collection and Domo Integration

This project collects GitHub Copilot usage metrics and uploads them to Domo for analysis and visualization. It supports both GitHub Enterprise and Organization setups with automated data collection and flattened data structures optimized for Domo analytics.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Project Structure](#project-structure)
- [Script Execution Sequence](#script-execution-sequence)
- [Scripts Overview](#scripts-overview)
- [Command Line Options](#command-line-options)
- [Troubleshooting](#troubleshooting)
- [Data Schema](#data-schema)

## 🔧 Prerequisites

### Required Accounts & Access
- **GitHub Enterprise/Organization** with Copilot enabled
- **GitHub Personal Access Token** with appropriate scopes:
  - `read:enterprise` (for enterprise accounts)
  - `read:org` (for organization accounts)
  - `manage_billing:copilot` (for Copilot metrics)
- **Domo Instance** with API access
- **Domo API Credentials** (Client ID and Secret)

### Required Software
- Python 3.8+
- Required Python packages (install with `pip install -r requirements.txt`):
  - `requests`
  - `pandas`
  - `python-dotenv`

## 📁 Project Structure

```
GitHubCopilotMetricsProd/
├── config/
│   ├── .env.example          # Environment variables template
│   ├── .env                  # Your environment variables (create from example)
│   └── README.md
├── docs/
│   └── README.md             # Legacy documentation
├── logs/                     # Log files from script execution
│   ├── get_metrics.log
│   ├── load_github_user_domo.log
│   └── domo_integration.log
├── output/                   # Generated JSON data files
│   ├── github_org_users.json
│   ├── github_users_flattened.json
│   ├── metrics.json
│   └── last_copilot_run.txt
├── scripts/                  # All executable scripts
│   ├── test_github_connection.py      # GitHub API connectivity test
│   ├── test_domo_connection.py        # Domo API connectivity test
│   ├── get_github_users.py            # Collect GitHub user data
│   ├── load_github_user_domo.py       # User data + Domo upload
│   ├── get_metrics.py                 # Collect Copilot metrics
│   ├── create_domo_dataset_v2.py      # Create Domo datasets
│   ├── create_domo_dataset.py         # DEPRECATED - use _v2
│   ├── domo_integration.py            # Domo utilities
│   └── github_client.py               # GitHub API client utilities
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## ⚙️ Setup Instructions

### 1. Clone and Configure Environment

```bash
# Navigate to the project directory
cd /Users/brad.wisdom/Library/CloudStorage/OneDrive-Apiture,Inc/MyDevProjects/GitHubCopilotMetricsProd

# Create required directories
mkdir -p config logs output

# Copy and configure environment variables
cp config/.env.example config/.env
```

### 2. Configure Environment Variables

Edit `config/.env` with your credentials:

```env
# GitHub Configuration - Update these variable names based on your github_client.py
GITHUB_COPILOT_PAT=your_github_personal_access_token
GITHUB_ENTERPRISE_OR_ORG_SLUG=your_enterprise_or_org_name

# Legacy variable names (if used by other scripts)
GITHUB_PAT=your_github_personal_access_token
GITHUB_ORG_NAME=your_enterprise_or_org_name

# Domo Configuration
DOMO_CLIENT_ID=your_domo_client_id
DOMO_CLIENT_SECRET=your_domo_client_secret
DOMO_API_HOST=https://api.domo.com

# Dataset IDs (will be populated after dataset creation)
DOMO_DATASET_ID=
GITHUB_USERS_DATASET_ID=
```

## 🚀 Script Execution Sequence

Follow this sequence for initial setup and ongoing operations:

### Phase 1: Validation & Testing

#### Step 1: Test GitHub Connection
```bash
python3 test_github_connection.py
```
**Expected Output:** ✅ GitHub API connection successful

#### Step 2: Test Domo Connection
```bash
python3 test_domo_connection.py
```
**Expected Output:** ✅ Domo API connection successful

### Phase 2: Initial Dataset Creation

#### Step 3: Collect Sample User Data
```bash
python3 get_github_users.py
```
**Expected Output:** 
- `output/github_org_users.json` (original user data)
- `output/github_users_flattened.json` (Domo-ready format)

#### Step 4: Create Domo Datasets

Create GitHub Users dataset:
```bash
python3 create_domo_dataset_v2.py output/github_users_flattened.json "GitHub Copilot Users" "Flattened user-team relationship data" --upload-data
```

Create Copilot Metrics dataset:
```bash
python3 get_metrics.py  # This generates output/metrics.json
python3 create_domo_dataset_v2.py output/metrics.json "GitHub Copilot Metrics" "Daily Copilot usage metrics" --upload-data
```

#### Step 5: Update Environment Variables
After dataset creation, update your `.env` file with the new Dataset IDs provided by the scripts:
```env
DOMO_DATASET_ID=your_copilot_metrics_dataset_id
GITHUB_USERS_DATASET_ID=your_github_users_dataset_id
```

### Phase 3: Production Data Collection

#### Step 6: Full User Data Collection and Upload
```bash
python3 load_github_user_domo.py
```
**Expected Output:** ✅ GitHub user data uploaded to Domo (REPLACE mode)

#### Step 7: Copilot Metrics Collection
```bash
python3 get_metrics.py
```
**Expected Output:** ✅ Metrics uploaded to Domo successfully

### Phase 4: Ongoing Operations

For regular data updates, run these scripts on a schedule:

**Daily (recommended):**
```bash
# Collect latest Copilot metrics (default: append to Domo)
python3 get_metrics.py
```

**Weekly or as needed:**
```bash
# Update user data (team changes, new users, etc.)
python3 load_github_user_domo.py
```

## 📁 Scripts Overview

### Core Data Collection Scripts

| Script | Purpose | Output Location | Frequency |
|--------|---------|-----------------|-----------|
| `get_github_users.py` | Collects user and team data from GitHub Enterprise | `output/github_org_users.json`, `output/github_users_flattened.json` | Weekly |
| `load_github_user_domo.py` | Combined GitHub user collection + Domo upload | `output/` + Domo dataset update | Weekly |
| `get_metrics.py` | Collects Copilot usage metrics | `output/metrics.json` + Domo upload | Daily |

### Utility Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `test_github_connection.py` | Validates GitHub API access | Initial setup, troubleshooting |
| `test_domo_connection.py` | Validates Domo API access | Initial setup, troubleshooting |
| `create_domo_dataset_v2.py` | Creates Domo datasets from JSON | Initial setup, schema changes |

### Deprecated Scripts

| Script | Status | Replacement |
|--------|--------|-------------|
| `create_domo_dataset.py` | ⚠️ DEPRECATED | Use `create_domo_dataset_v2.py` |

### Support/Library Scripts

| Script | Purpose |
|--------|---------|
| `domo_integration.py` | Core Domo API functions |
| `github_client.py` | GitHub API client utilities |

## 🛠️ Command Line Options

### get_metrics.py

The `get_metrics.py` script supports several command line options for flexible operation:

#### Basic Usage
```bash
# Normal run (default: append to Domo, fetch new data since last run)
python3 get_metrics.py
```

#### Rerun Options
```bash
# Force rerun from last run date to yesterday
python3 get_metrics.py --rerun

# Rerun with custom date range
python3 get_metrics.py --rerun --start-date 2025-06-01 --end-date 2025-06-30
```

#### Output-Only Options
```bash
# Run without uploading to Domo (creates timestamped output file)
python3 get_metrics.py --no-domo

# Rerun specific date range without Domo upload
python3 get_metrics.py --rerun --no-domo --start-date 2025-06-01 --end-date 2025-06-30
```

#### Command Line Arguments

| Argument | Description | Usage |
|----------|-------------|-------|
| `--rerun` | Force rerun ignoring up-to-date check | Fetches from last run date to yesterday |
| `--no-domo` | Skip Domo upload, only write to output file | Creates `metrics_rerun_YYYYMMDD_HHMMSS.json` |
| `--start-date` | Override start date (YYYY-MM-DD) | Only works with `--rerun` |
| `--end-date` | Override end date (YYYY-MM-DD) | Only works with `--rerun` |

#### Examples

**Daily automation (recommended):**
```bash
python3 get_metrics.py
```
*Fetches new data since last run and appends to Domo*

**Backfill missing data:**
```bash
python3 get_metrics.py --rerun --start-date 2025-05-01 --end-date 2025-05-31
```
*Fetches specific date range and appends to Domo*

**Data analysis without affecting production:**
```bash
python3 get_metrics.py --rerun --no-domo --start-date 2025-06-01 --end-date 2025-06-15
```
*Creates separate output file without uploading to Domo or updating last run date*

**Force refresh recent data:**
```bash
python3 get_metrics.py --rerun
```
*Re-fetches from last successful run to yesterday*

## 🔍 Troubleshooting

### Common Issues

1. **"Already up-to-date" message**
   - Use `--rerun` flag to force execution
   - Check `output/last_copilot_run.txt` for last run date

2. **GitHub API errors**
   - Verify GitHub PAT has correct permissions
   - Check rate limits and API quotas

3. **Domo upload failures**
   - Verify Domo credentials in `.env`
   - Check dataset permissions
   - Use `--no-domo` flag to test data collection separately

4. **No metrics returned**
   - Verify organization/enterprise name
   - Ensure Copilot is enabled and has usage data
   - Check date ranges (API only returns up to yesterday)

5. **Empty records in output**
   - This is normal for incomplete data structures
   - Records are created for each metric type combination

### Log Files

All scripts write detailed logs to the `logs/` directory:
- `get_metrics.log` - Copilot metrics collection
- `domo_integration.log` - Domo upload operations
- `load_github_user_domo.log` - User data operations

## 📊 Data Schema

### Copilot Metrics Dataset

| Field | Type | Description |
|-------|------|-------------|
| `date` | STRING | Date of metrics (YYYY-MM-DD) |
| `total_active_users` | LONG | Total active Copilot users |
| `total_engaged_users` | LONG | Total engaged users |
| `ide_completions_users` | LONG | Users with IDE completions |
| `ide_chat_users` | LONG | Users with IDE chat |
| `dotcom_chat_users` | LONG | Users with GitHub.com chat |
| `pr_users` | LONG | Users with PR summaries |
| `editor` | STRING | Editor name (vscode, etc.) |
| `model` | STRING | Model name (default, etc.) |
| `is_custom_model` | BOOLEAN | Whether model is custom |
| `language` | STRING | Programming language |
| `code_suggestions` | LONG | Code suggestions count |
| `code_acceptances` | LONG | Code acceptances count |
| `lines_suggested` | LONG | Lines of code suggested |
| `lines_accepted` | LONG | Lines of code accepted |
| `chat_count` | LONG | Chat interactions |
| `chat_insertions` | LONG | Chat code insertions |
| `chat_copies` | LONG | Chat code copies |
| `pr_summaries` | LONG | PR summaries created |
| `repository` | STRING | Repository name |

## 📈 Directory Cleanup Summary

**Changes Made:**
1. ✅ **Output Organization**: All JSON files now go to `output/` directory
2. ✅ **Script Consistency**: Fixed `Scripts/` vs `scripts/` directory inconsistency
3. ✅ **Deprecated Scripts**: Clearly marked `create_domo_dataset.py` as deprecated
4. ✅ **Path Updates**: Updated all scripts to use consistent `output/` directory
5. ✅ **README Accuracy**: Updated documentation to reflect actual project structure
6. ✅ **Command Line Features**: Added flexible options for data collection and output

**Files to Move Manually:**
- Move any existing `*.json` files to `output/` directory
- Move `Scripts/get_metrics.py` to `scripts/get_metrics.py` (fix case)
- Create `output/` directory if it doesn't exist

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review log files in the `logs/` directory  
3. Validate your GitHub token permissions and Domo dataset access
4. Ensure all JSON files are in the `output/` directory
5. Use command line options to isolate issues (`--no-domo` for testing data collection)