"""
Test GitHub API connectivity and enterprise access.
"""

import os
import sys
from dotenv import load_dotenv

# Add scripts directory to path - we're already in scripts/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from github_client import GitHubClient

def test_github_connection():
    """Test GitHub API connectivity and access."""
    
    # Load environment variables
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))
    
    token = os.getenv('GITHUB_COPILOT_PAT')
    org_name = os.getenv('GITHUB_ENTERPRISE_OR_ORG_SLUG')
    
    if not token:
        print("❌ GitHub token not found in environment variables")
        return False
    
    if not org_name:
        print("❌ Organization/Enterprise name not found in environment variables")
        return False
    
    print("🔍 Testing GitHub API connectivity...")
    print(f"Organization/Enterprise: {org_name}")
    
    try:
        # Initialize GitHub client
        client = GitHubClient(token)
        
        # Test basic authentication
        import requests
        response = requests.get("https://api.github.com/user", 
                              headers={"Authorization": f"Bearer {token}"})
        
        if response.status_code == 200:
            user_data = response.json()
            print("✅ GitHub API connection successful!")
            print(f"Authenticated as: {user_data.get('login')}")
            print(f"Name: {user_data.get('name')}")
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            return False
        
        # Test token scopes
        scope_info = client.validate_token_scopes()
        if scope_info.get("has_required_scopes"):
            print("✅ Token has required scopes")
            print(f"Scopes: {', '.join(scope_info.get('current_scopes', []))}")
        else:
            print("⚠️  Token may be missing required scopes")
            print(f"Current scopes: {', '.join(scope_info.get('current_scopes', []))}")
            print(f"Missing scopes: {', '.join(scope_info.get('missing_scopes', []))}")
        
        # Detect organization type and test access
        detection_result = client.detect_org_type(org_name)
        
        if detection_result["accessible"]:
            print(f"✅ Successfully accessed {org_name} as {detection_result['type']}")
            
            if detection_result["type"] == "enterprise":
                # Test enterprise-specific endpoints
                try:
                    seats = client.fetch_enterprise_copilot_seats(org_name)
                    print(f"✅ Found {len(seats)} Copilot seats in enterprise")
                    
                    # Test user seats data extraction
                    user_seats = client.fetch_enterprise_user_seats(org_name)
                    print(f"✅ Found {len(user_seats)} individual users with Copilot access")
                    
                except Exception as e:
                    print(f"⚠️  Could not fetch enterprise Copilot data: {e}")
                    
            else:  # organization
                # Test organization-specific endpoints
                try:
                    org_info = client.test_organization_access(org_name)
                    if org_info["org_accessible"]:
                        print("✅ Organization access confirmed")
                    else:
                        print(f"⚠️  Organization access issues: {org_info.get('error')}")
                except Exception as e:
                    print(f"⚠️  Could not test organization access: {e}")
                    
        else:
            print(f"❌ Cannot access {org_name}")
            print(f"Error: {detection_result.get('error')}")
            
            # Try to get accessible organizations
            try:
                org_info = client.test_organization_access(org_name)
                if org_info.get("user_orgs"):
                    print(f"Your accessible organizations: {', '.join(org_info['user_orgs'])}")
            except Exception as e:
                print(f"Could not retrieve accessible organizations: {e}")
                
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing GitHub connection: {e}")
        return False

if __name__ == "__main__":
    success = test_github_connection()
    sys.exit(0 if success else 1)
