# GitHub User Data Collection Script Documentation

## Overview

The `load_github_user_domo.py` script is a comprehensive data collection tool that fetches GitHub Copilot user information from a GitHub Enterprise and uploads it to Domo for analytics and reporting. This script combines user data collection, team relationship mapping, and automated Domo integration into a single workflow.

## What the Script Does

### 1. **GitHub API Data Collection**
- Fetches all GitHub Copilot users from the enterprise billing seats API
- Retrieves comprehensive user profile information including:
  - User identifiers (ID, login, name, email)
  - Copilot seat details (creation date, plan type, activity)
  - Team assignments from the seat data
- Collects all enterprise teams and their memberships
- Maps users to their team relationships

### 2. **Data Processing & Transformation**
- Flattens nested data structures for analytics consumption
- Creates user-team relationship records
- Handles users with multiple team memberships
- Processes users with no team assignments
- Validates and formats data for Domo compatibility

### 3. **Domo Integration**
- Automatically uploads processed data to Domo dataset
- Uses REPLACE mode to ensure data consistency
- Includes schema validation and error handling
- Provides detailed logging for troubleshooting

## Script Execution Flow

```
1. Load environment variables and configuration
2. Fetch Copilot users from GitHub Enterprise API
3. Fetch all enterprise teams
4. Map team members to users
5. Flatten data for Domo compatibility
6. Save data locally (JSON files)
7. Upload to Domo dataset (if configured)
8. Log results and completion status
```

## Output Files Generated

The script generates two distinct output files with different purposes:

### 1. `github_org_users.json` - **Original User Data**

**Purpose**: Complete, unmodified user records as returned by the GitHub API

**Structure**: Array of user objects with full GitHub API response data

**Key Characteristics**:
- ✅ **One record per user** (114 users = 114 records)
- ✅ **Complete API data** including all GitHub fields
- ✅ **Assigning team information** from the Copilot seat
- ✅ **Preserves original data structure** for reference
- ✅ **Ideal for** backup, debugging, and API response analysis

**Sample Record**:
```json
{
  "user_id": 212026935,
  "login": "dwayne-hill_Apiture",
  "name": "",
  "email": "",
  "avatar_url": "https://avatars.githubusercontent.com/u/212026935?v=4",
  "html_url": "https://github.com/dwayne-hill_Apiture",
  "site_admin": false,
  "copilot_enabled": "Yes",
  "seat_created_at": "2025-05-16T12:40:52-05:00",
  "pending_cancellation_date": null,
  "plan_type": "business",
  "last_activity_at": "2025-07-02T07:46:52-05:00",
  "last_activity_editor": "vscode/1.101.1/copilot-chat/0.28.2",
  "assigning_team_id": 80547,
  "assigning_team_name": "Platform",
  "assigning_team_slug": "platform",
  "assigning_team_html_url": "https://github.com/enterprises/Apiture-EMU/teams/platform",
  "has_team_assignment": true
}
```

### 2. `github_users_flattened.json` - **Domo-Ready Analytics Data**

**Purpose**: Flattened, analytics-optimized data for Domo consumption

**Structure**: Array of user-team relationship records

**Key Characteristics**:
- ✅ **One record per user-team relationship** (can be multiple records per user)
- ✅ **Flattened structure** optimized for SQL queries and dashboards
- ✅ **Team relationship mapping** from enterprise team API
- ✅ **Consistent schema** for Domo dataset compatibility
- ✅ **Ideal for** analytics, reporting, and team-based insights

**Sample Record**:
```json
{
  "user_id": 212026935,
  "login": "dwayne-hill_Apiture",
  "name": "",
  "email": "",
  "avatar_url": "https://avatars.githubusercontent.com/u/212026935?v=4",
  "html_url": "https://github.com/dwayne-hill_Apiture",
  "site_admin": false,
  "copilot_enabled": "Yes",
  "seat_created_at": "2025-05-16T12:40:52-05:00",
  "pending_cancellation_date": null,
  "plan_type": "business",
  "last_activity_at": "2025-07-02T07:46:52-05:00",
  "last_activity_editor": "vscode/1.101.1/copilot-chat/0.28.2",
  "team_id": 80547,
  "team_name": "Platform",
  "team_slug": "platform",
  "team_html_url": "https://github.com/enterprises/Apiture-EMU/teams/platform",
  "has_team_assignment": true
}
```

## Key Differences Between Output Files

| Aspect | `github_org_users.json` | `github_users_flattened.json` |
|--------|-------------------------|--------------------------------|
| **Purpose** | Original API data preservation | Analytics and reporting |
| **Record Count** | 1 record per user (114) | 1+ records per user (varies) |
| **Data Source** | GitHub Copilot Seats API only | Seats API + Teams API |
| **Team Data** | Assigning team from seat | All team memberships |
| **Structure** | Nested/Complex | Flat/Tabular |
| **Use Case** | Backup, debugging, reference | Domo analytics, dashboards |
| **Schema** | GitHub API response format | Domo-optimized format |
| **Relationships** | User → Assigning Team | User → All Teams |

## Team Relationship Handling

### Assigning Team vs. All Teams
- **Assigning Team**: The team that assigned the Copilot seat to the user (from seats API)
- **All Teams**: Complete list of teams the user belongs to (from teams API)

### Data Processing Logic
```
IF user has team memberships from teams API:
    CREATE one record per team membership
ELSE:
    CREATE one record with assigning team data (from seat)
    IF no assigning team:
        CREATE one record with empty team fields
```

## Environment Variables Required

```bash
# GitHub Configuration
GITHUB_PAT=your_github_personal_access_token
GITHUB_ORG_NAME=your_enterprise_name

# Domo Configuration  
DOMO_CLIENT_ID=your_domo_client_id
DOMO_CLIENT_SECRET=your_domo_client_secret
GITHUB_USERS_DATASET_ID=your_domo_dataset_id  # Optional for upload
```

## Usage Examples

### Basic Execution
```bash
# Collect data and upload to Domo
python3 load_github_user_domo.py
```

### Expected Output
```
============================================================
Starting GitHub User Data Collection and Domo Upload
============================================================
Fetching Copilot users for enterprise: Apiture-EMU
Found 114 Copilot users
Fetching teams for enterprise: Apiture-EMU
Found 6 teams
Team 'Platform' (ID: 80547): 10 members
Team 'Architecture' (ID: 80554): 13 members
Team 'QA' (ID: 80555): 17 members
Team 'Development' (ID: 80556): 68 members
Team 'Development-Contractors' (ID: 80850): 25 members
Team 'Enterprise-Owners' (ID: 80851): 3 members
Flattened 114 users into 137 records for Domo
Original user data saved to output/github_org_users.json
Flattened user data saved to output/github_users_flattened.json
SUCCESS: GitHub user data uploaded to Domo
Users processed: 114
Teams processed: 6
Flattened records: 137
============================================================
```

## Analytics Use Cases

### Original Data (`github_org_users.json`)
- **API Response Analysis**: Understanding GitHub API structure
- **Data Backup**: Complete user information preservation
- **Debugging**: Troubleshooting API issues
- **Audit Trail**: Historical record of seat assignments

### Flattened Data (`github_users_flattened.json`)
- **Team Analytics**: Users per team, team distribution
- **Copilot Adoption**: Seat utilization by team
- **Activity Tracking**: Last activity analysis by team
- **User Management**: Team membership reporting
- **Cross-Team Analysis**: Users in multiple teams

## Domo Dashboard Possibilities

With the flattened data, you can create:
- **Team Distribution Charts**: Users by team
- **Activity Heatmaps**: Last activity by team
- **Adoption Metrics**: Copilot usage by team
- **User Directory**: Searchable user listings
- **Team Relationships**: Multi-team user analysis

## Troubleshooting

### Common Issues
1. **No Domo Upload**: Check `GITHUB_USERS_DATASET_ID` environment variable
2. **Empty Teams**: Verify GitHub token has enterprise team permissions
3. **Missing Users**: Ensure users have active Copilot seats
4. **Schema Errors**: Validate Domo dataset schema matches expected format

### Log Files
- **Main Logs**: `logs/load_github_user_domo.log`
- **Domo Integration**: `logs/domo_integration.log`

## Related Scripts

- **`get_github_users.py`**: Data collection only (no Domo upload)
- **`test_github_connection.py`**: GitHub API connectivity testing
- **`test_domo_connection.py`**: Domo API connectivity testing
- **`create_domo_dataset_v2.py`**: Create Domo datasets from JSON files

## Best Practices

1. **Run Weekly**: User and team data changes periodically
2. **Monitor Logs**: Check for API rate limits or permission issues
3. **Validate Output**: Ensure record counts match expectations
4. **Backup Data**: Keep local JSON files for reference
5. **Schema Consistency**: Maintain consistent Domo dataset structure
