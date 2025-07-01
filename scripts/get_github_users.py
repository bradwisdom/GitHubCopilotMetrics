import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../config/.env'))

GITHUB_PAT = os.getenv("GITHUB_PAT")
GITHUB_ORG_NAME = os.getenv("GITHUB_ORG_NAME")

def get_all_users(org, token):
    """Get all users for an org using the /members endpoint (paginated)."""
    users = []
    page = 1
    per_page = 100
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    while True:
        url = f"https://api.github.com/orgs/{org}/members?per_page={per_page}&page={page}"
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"Failed to fetch users: {resp.status_code} {resp.text}")
            break
        batch = resp.json()
        if not batch:
            break
        users.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return users

def get_user_profile(username, token):
    """Get detailed user profile."""
    url = f"https://api.github.com/users/{username}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"Failed to fetch profile for {username}: {resp.status_code} {resp.text}")
        return None

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
    while True:
        params = {"per_page": per_page, "page": page}
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            print(f"Failed to fetch Copilot seats: {resp.status_code} {resp.text}")
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
                    "name": assignee.get("name"),
                    "email": assignee.get("email"),
                    "avatar_url": assignee.get("avatar_url"),
                    "html_url": assignee.get("html_url"),
                    "site_admin": assignee.get("site_admin"),
                    "copilot_enabled": "Yes",
                    "seat_created_at": seat.get("created_at"),
                    "pending_cancellation_date": seat.get("pending_cancellation_date"),
                    "plan_type": seat.get("plan_type"),
                    "last_activity_at": seat.get("last_activity_at"),
                    "last_activity_editor": seat.get("last_activity_editor", "")
                }
                assigning_team = seat.get("assigning_team")
                if isinstance(assigning_team, dict):
                    user["assigning_team_id"] = assigning_team.get("id")
                    user["assigning_team_name"] = assigning_team.get("name")
                    user["assigning_team_slug"] = assigning_team.get("slug")
                    user["assigning_team_html_url"] = assigning_team.get("html_url")
                users.append(user)
        if len(batch) < per_page:
            break
        page += 1
    return users

def get_enterprise_teams(enterprise, token):
    """Fetch all teams for a GitHub Enterprise using the REST API."""
    url = f"https://api.github.com/enterprises/{enterprise}/teams"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    teams = []
    page = 1
    per_page = 100
    while True:
        params = {"per_page": per_page, "page": page}
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            print(f"Failed to fetch enterprise teams: {resp.status_code} {resp.text}")
            break
        batch = resp.json()
        if not batch:
            break
        teams.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return teams

def get_enterprise_team_members(enterprise, team_id, token):
    """
    Fetch all members for a given enterprise team using team ID.
    Use the enterprise team memberships endpoint with team ID.
    """
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
            print(f"Failed to fetch memberships for team {team_id}: {resp.status_code} {resp.text}")
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
    """
    Flatten user data for Domo upload compatibility.
    Creates one record per user-team combination, or one record if no teams.
    """
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
        # User with no team assignments
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
            "has_team_assignment": bool(user.get("assigning_team_id"))
        }
        flattened_records.append(record)
    
    return flattened_records

def main():
    if not GITHUB_PAT or not GITHUB_ORG_NAME:
        print("GITHUB_PAT or GITHUB_ORG_NAME not set in .env")
        return
    print(f"Fetching all Copilot users for enterprise: {GITHUB_ORG_NAME}")
    users = get_all_users_enterprise(GITHUB_ORG_NAME, GITHUB_PAT)
    print(f"Found {len(users)} Copilot users. Writing profiles...")
    
    print(f"Fetching all teams for enterprise: {GITHUB_ORG_NAME}")
    teams = get_enterprise_teams(GITHUB_ORG_NAME, GITHUB_PAT)
    print(f"Found {len(teams)} teams.")
    
    # Map team members to users if needed
    team_mapping = {}  # user_login -> list of team objects
    for team in teams:
        team_id = team.get("id")
        team_name = team.get("name")
        if not team_id:
            continue
        members = get_enterprise_team_members(GITHUB_ORG_NAME, team_id, GITHUB_PAT)
        print(f"Team '{team_name}' (ID: {team_id}): {len(members)} members")
        
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
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Write original user data to JSON
    output_file = os.path.join(output_dir, "github_org_users.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)
    print(f"User profiles written to {output_file}")
    print(f"Total users written: {len(users)}")
    
    # Write flattened data for Domo
    flattened_output_file = os.path.join(output_dir, "github_users_flattened.json")
    with open(flattened_output_file, "w", encoding="utf-8") as f:
        json.dump(flattened_users, f, indent=2)
    print(f"Flattened user data for Domo written to {flattened_output_file}")
    print(f"Total flattened records: {len(flattened_users)}")

if __name__ == "__main__":
    main()
