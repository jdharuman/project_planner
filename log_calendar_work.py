import json
import os
import requests
from datetime import datetime
from collections import defaultdict

def log_work_from_calendar(raw_issues_file, calendar_events_file, config_file):
    """
    Reads calendar events and logs work to matching PS tickets in Jira.
    
    Args:
        raw_issues_file: Path to raw Jira issues JSON
        calendar_events_file: Path to saved calendar events JSON
        config_file: Path to planner config JSON
    """
    from planner import load_config
    
    # Load configuration
    CONFIG = load_config(config_file)
    JIRA_BASE_URL = CONFIG.get('jira_base_url', "https://sibros.atlassian.net/browse/").replace('/browse/', '')
    PS_SUMMARY_FILTER = CONFIG.get('ps_summary_filter', None)
    
    # Get Jira credentials from environment
    jira_email = os.getenv('JIRA_EMAIL')
    jira_api_token = os.getenv('JIRA_API_KEY')
    
    if not jira_email or not jira_api_token:
        print("Error: JIRA_EMAIL and JIRA_API_KEY environment variables must be set")
        return
    
    # Load calendar events
    try:
        with open(calendar_events_file, 'r') as f:
            calendar_events = json.load(f)
    except FileNotFoundError:
        print(f"Error: Calendar events file not found: {calendar_events_file}")
        print("Please run: task_planner --calendar --today --log first")
        return
    
    if not calendar_events:
        print("No calendar events found in file")
        return
    
    # Load PS tickets
    with open(raw_issues_file, 'r') as f:
        raw_issues = json.load(f)
    
    # Build customer -> ticket mapping
    customer_tickets = defaultdict(list)
    
    for issue in raw_issues:
        fields = issue.get('fields', {})
        key = issue.get('key')
        summary = fields.get('summary', '')
        
        # Apply summary filter
        if PS_SUMMARY_FILTER:
            import re
            if not re.search(PS_SUMMARY_FILTER, summary, re.IGNORECASE):
                continue
        
        # Get customers
        customers_field = fields.get('customfield_10109', [])
        if customers_field:
            for customer_obj in customers_field:
                customer_name = customer_obj.get('value', 'Unknown')
                customer_tickets[customer_name].append({
                    'key': key,
                    'summary': summary,
                    'issue': issue
                })
    
    print(f"\n{'='*100}")
    print(f"LOGGING WORK FROM CALENDAR EVENTS")
    print(f"{'='*100}\n")
    print(f"Found {len(calendar_events)} calendar events")
    print(f"Found {len(customer_tickets)} PS customers with tickets\n")
    
    # Process each calendar event
    logged_count = 0
    skipped_count = 0
    error_count = 0
    
    for event in calendar_events:
        title = event.get('title', 'No Title')
        date = event.get('date', '')
        start_time = event.get('start_time', '')
        end_time = event.get('end_time', '')
        
        print(f"-" * 100)
        print(f"Event: {title}")
        print(f"Time:  {date} {start_time} - {end_time}")
        
        # Extract customer name from title (simple approach)
        # Look for customer names in the title
        matched_customer = None
        for customer_name in customer_tickets.keys():
            if customer_name.lower() in title.lower():
                matched_customer = customer_name
                break
        
        if not matched_customer:
            print(f"⊘ Skipped: No matching PS customer found for this event")
            skip ped_count += 1
            continue
        
        tickets = customer_tickets[matched_customer]
        if not tickets:
            print(f"⊘ Skipped: No PS tickets found for customer: {matched_customer}")
            skipped_count += 1
            continue
        
        ticket = tickets[0]  # Use first ticket for this customer
        ticket_key = ticket['key']
        issue_data = ticket['issue']
        
        print(f"✓ Matched to ticket: {ticket_key} ({matched_customer})")
        
        # Calculate time spent (meeting duration in minutes)
        if start_time != 'All Day' and end_time != 'All Day':
            try:
                start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
                end_dt = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
                duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
                
                # Check if work is already logged for this time
                worklog_data = issue_data['fields'].get('worklog', {})
                existing_worklogs = worklog_data.get('worklogs', [])
                
                # Check if any worklog exists for this date
                already_logged = False
                for wl in existing_worklogs:
                    wl_started = wl.get('started', '')
                    if date in wl_started:
                        already_logged = True
                        print(f"⊘ Skipped: Work already logged on {date}")
                        break
                
                if already_logged:
                    skipped_count += 1
                    continue
                
                # Log the work
                worklog_payload = {
                    "timeSpent": f"{duration_minutes}m",
                    "started": f"{date}T{start_time}:00.000+0000",
                    "comment": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": f"Meeting: {title}"
                                    }
                                ]
                            }
                        ]
                    }
                }
                
                # Make API call to Jira
                url = f"{JIRA_BASE_URL}/rest/api/3/issue/{ticket_key}/worklog"
                response = requests.post(
                    url,
                    auth=(jira_email, jira_api_token),
                    headers={"Content-Type": "application/json"},
                    json=worklog_payload
                )
                
                if response.status_code == 201:
                    print(f"✓ Logged {duration_minutes}m to {ticket_key}")
                    logged_count += 1
                else:
                    print(f"✗ Error logging work: {response.status_code} - {response.text}")
                    error_count += 1
                    
            except Exception as e:
                print(f"✗ Error processing event: {e}")
                error_count += 1
        else:
            print(f"⊘ Skipped: All-day event, cannot determine duration")
            skipped_count += 1
    
    print(f"\n{'='*100}")
    print(f"SUMMARY")
    print(f"{'='*100}")
    print(f"✓ Logged:  {logged_count}")
    print(f"⊘ Skipped: {skipped_count}")
    print(f"✗ Errors:  {error_count}")
    print()
