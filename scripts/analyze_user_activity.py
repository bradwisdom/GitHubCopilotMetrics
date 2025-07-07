import json
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict

def analyze_user_activity():
    """Analyze GitHub user activity patterns from the collected data."""
    
    # Load the user data
    data_file = os.path.join(os.path.dirname(__file__), '..', 'output', 'github_org_users.json')
    
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        print("Run load_github_user_domo.py first to collect user data")
        return
    
    with open(data_file, 'r') as f:
        users = json.load(f)
    
    print(f"📊 Analyzing {len(users)} GitHub Copilot users")
    print("=" * 60)
    
    # Activity statistics
    active_users = [u for u in users if u.get('last_activity_at')]
    inactive_users = [u for u in users if not u.get('last_activity_at')]
    
    print(f"👥 Users with Activity Data: {len(active_users)} ({len(active_users)/len(users)*100:.1f}%)")
    print(f"😴 Users without Activity Data: {len(inactive_users)} ({len(inactive_users)/len(users)*100:.1f}%)")
    print()
    
    # Team breakdown
    team_stats = defaultdict(lambda: {'total': 0, 'active': 0, 'inactive': 0})
    
    for user in users:
        team_name = user.get('assigning_team_name', 'No Team')
        team_stats[team_name]['total'] += 1
        
        if user.get('last_activity_at'):
            team_stats[team_name]['active'] += 1
        else:
            team_stats[team_name]['inactive'] += 1
    
    print("📋 Activity by Team:")
    for team, stats in sorted(team_stats.items()):
        active_pct = stats['active'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"  {team:25} | Total: {stats['total']:3d} | Active: {stats['active']:3d} ({active_pct:5.1f}%) | Inactive: {stats['inactive']:3d}")
    print()
    
    # Recent activity analysis
    if active_users:
        # Create timezone-aware now object
        now = datetime.now(timezone.utc)
        cutoff_7d = now - timedelta(days=7)
        cutoff_30d = now - timedelta(days=30)
        
        recent_7d = []
        recent_30d = []
        older = []
        future_dates = []
        
        for user in active_users:
            try:
                # Try to handle any date format (with or without timezone)
                activity_str = user['last_activity_at']
                if activity_str.endswith('Z'):
                    activity_str = activity_str.replace('Z', '+00:00')
                
                # Parse the datetime with timezone info
                activity_date = datetime.fromisoformat(activity_str)
                
                # Make sure activity_date is timezone-aware
                if activity_date.tzinfo is None:
                    # If no timezone in string, assume local timezone
                    local_tz_offset = datetime.now().astimezone().utcoffset()
                    activity_date = activity_date.replace(tzinfo=timezone(local_tz_offset))
                
                # Handle future dates (test data often has dates in 2025)
                if activity_date > now:
                    future_dates.append(user)
                    # Consider this recent activity (within 7 days)
                    recent_7d.append(user)
                    continue
                
                # Now do the comparison with timezone-aware objects
                if activity_date >= cutoff_7d:
                    recent_7d.append(user)
                elif activity_date >= cutoff_30d:
                    recent_30d.append(user)
                else:
                    older.append(user)
                    
            except Exception as e:
                older.append(user)
        
        print("⏰ Activity Recency:")
        print(f"  Last 7 days:    {len(recent_7d):3d} users ({len(recent_7d)/len(users)*100:.1f}% of total)")
        print(f"  Last 30 days:   {len(recent_30d):3d} users ({len(recent_30d)/len(users)*100:.1f}% of total)")
        print(f"  Older than 30d: {len(older):3d} users ({len(older)/len(users)*100:.1f}% of total)")
        
        # Print notice about future dates if found
        if future_dates:
            print(f"\n⚠️  NOTICE: Found {len(future_dates)} users with future dates (likely test data)")
            print(f"   These users are counted as 'Last 7 days' activity")
        
        print()

    # Editor usage analysis
    if active_users:
        editors = defaultdict(int)
        for user in active_users:
            editor_info = user.get('last_activity_editor', '')
            if editor_info:
                editor = editor_info.split('/')[0] if '/' in editor_info else editor_info
                editors[editor] += 1
        
        print("🛠️  Editor Usage (among active users):")
        for editor, count in sorted(editors.items(), key=lambda x: x[1], reverse=True):
            pct = count / len(active_users) * 100
            print(f"  {editor:15} | {count:3d} users ({pct:5.1f}%)")
        print()
    
    # List inactive users by team
    print("😴 Inactive Users by Team:")
    team_inactive = defaultdict(list)
    for user in inactive_users:
        team_name = user.get('assigning_team_name', 'No Team')
        team_inactive[team_name].append(user['login'])
    
    for team, users_list in sorted(team_inactive.items()):
        print(f"  {team} ({len(users_list)} users):")
        for login in sorted(users_list):
            print(f"    - {login}")
        print()
    
    # Recommendations
    print("💡 Recommendations:")
    print("  1. Check if inactive users have Copilot properly installed and enabled")
    print("  2. Verify users are using supported editors (VS Code, JetBrains, etc.)")
    print("  3. Consider user training on Copilot features")
    print("  4. Review seat assignments for users who aren't using Copilot")
    print("  5. Some users may be legitimate non-users (managers, etc.)")

if __name__ == "__main__":
    analyze_user_activity()
