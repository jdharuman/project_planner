
import json
import os
import getpass
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta

# --- Custom Field IDs (Update these if necessary) ---

# You might need to change these placeholder IDs to your actual custom field IDs

CUSTOM_FIELD_CUSTOMERS = "customfield_10080"

CUSTOM_FIELD_HEALTH = "customfield_10001"

# Map priority names to numerical values for sorting (P0 highest priority)
PRIORITY_MAP = {
    "P0": 0,
    "P1": 1,
    "P2": 2,
    "P3": 3,
    "P4": 4,
    "Highest": 0,
    "High": 1,
    "Medium": 2,
    "Low": 3,
    "Lowest": 4,
    None: 99 # Default for unassigned or unknown priority
}


def get_jira_credentials(jira_url, email=None, api_token=None):
    """
    Prompts the user for Jira email and API token, or gets them from
    environment variables JIRA_EMAIL and JIRA_API_KEY.
    Can also accept email and api_token as direct arguments.
    """
    print(f"Connecting to Jira instance: {jira_url}")
    
    if not email:
        email = os.environ.get('JIRA_EMAIL')
        if email:
            print(f"Using email from JIRA_EMAIL environment variable.")
        else:
            email = input("Enter your Jira email: ")

    if not api_token:
        api_token = os.environ.get('JIRA_API_KEY')
        if api_token:
            print("Using API token from JIRA_API_KEY environment variable.")
        else:
            api_token = getpass.getpass("Enter your Jira API token: ")
            
    return email, api_token

def fetch_jira_issues_manually(jira_url, jql_query_content, email, api_token):
    """
    Fetches Jira issues by making a direct POST request to the v3 search API.
    This bypasses the jira library's search method.
    """
    search_url = f"{jira_url}/rest/api/3/search/jql"
    
    auth = HTTPBasicAuth(email, api_token)
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    params = {
        # "fields": "*all" # Moved to payload
    }

    payload = json.dumps({
        "jql": jql_query_content,
        "fields": ["*all"] # Include all fields in the request body
    })
    
    try:
        print(f"Making direct API call to: {search_url}")
        response = requests.post(search_url, data=payload, headers=headers, auth=auth, params=params)
        response.raise_for_status()  # This will raise an exception for HTTP errors
        
        print("API call successful.")
        data = response.json()
        return data.get('issues', [])
        
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e.response.status_code} {e.response.reason}")
        print(f"Response body: {e.response.text}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def format_raw_issues(raw_issues):
    """Formats the raw JSON issue data from the API into our desired structure."""
    formatted_issues = []
    for issue in raw_issues:
        fields = issue.get('fields', {})
        
        # Helper to get field value safely from the dictionary
        def get_field(data, key, default=None):
            if data is None or not isinstance(data, dict):
                return default
            return data.get(key, default)

        # Extracting 'Customers'
        customers_field = get_field(fields, CUSTOM_FIELD_CUSTOMERS, [])
        customers = [c.get('value') for c in customers_field] if customers_field else []

        # Extracting 'Health'
        health_field = get_field(fields, CUSTOM_FIELD_HEALTH)
        health = health_field.get('value') if health_field else None

        # Extracting 'Sprint'
        sprint_name = None
        sprint_state = None
        sprint_field = get_field(fields, 'customfield_10020')
        if sprint_field and isinstance(sprint_field, list) and sprint_field:
            active_sprints = [s for s in sprint_field if s.get('state') == 'active']
            future_sprints = [s for s in sprint_field if s.get('state') == 'future']
            closed_sprints = [s for s in sprint_field if s.get('state') == 'closed']

            selected_sprint = None
            if active_sprints:
                active_sprints.sort(key=lambda s: s.get('startDate', ''), reverse=True)
                selected_sprint = active_sprints[0]
            elif future_sprints:
                future_sprints.sort(key=lambda s: s.get('startDate', ''))
                selected_sprint = future_sprints[0]
            elif closed_sprints:
                closed_sprints.sort(key=lambda s: s.get('endDate', ''), reverse=True)
                selected_sprint = closed_sprints[0]
            
            if selected_sprint:
                sprint_name = selected_sprint.get('name')
                sprint_state = selected_sprint.get('state')

        priority_name = get_field(get_field(fields, 'priority', {}), 'name')
        priority_value = PRIORITY_MAP.get(priority_name, PRIORITY_MAP[None])

        formatted_issues.append({
            "key": get_field(issue, 'key'),
            "summary": get_field(fields, 'summary'),
            "issue_type": get_field(get_field(fields, 'issuetype', {}), 'name'),
            "is_subtask": get_field(get_field(fields, 'issuetype', {}), 'subtask'),
            "parent_key": get_field(get_field(issue, 'parent', {}), 'key'), # Extract parent key
            "created": get_field(fields, 'created'),
            "updated": get_field(fields, 'updated'),
            "due": get_field(fields, 'duedate'),
            "assignee": get_field(get_field(fields, 'assignee', {}), 'displayName'),
            "reporter": get_field(get_field(fields, 'reporter', {}), 'displayName'),
            "priority": priority_name,
            "priority_value": priority_value,
            "status": get_field(get_field(fields, 'status', {}), 'name'),
            "status_color": get_field(get_field(get_field(fields, 'status', {}), 'statusCategory', {}), 'colorName'),
            "resolution": get_field(fields.get('resolution', {}), 'name'),
            "customers": customers,
            "fix_versions": [fv.get('name') for fv in get_field(fields, 'fixVersions', [])],
            "health": health,
            "sprint_name": sprint_name,
            "sprint_state": sprint_state,
            "task_health_status": get_field(get_field(fields, 'customfield_10119', {}), 'value') # Extract customfield_10119 value
        })
    return formatted_issues

def transform_jira_to_planner_format(jira_issues):
    """
    Transforms the formatted Jira issues into the structure expected by planner.py.
    """
    planner_data = {
        "resources": [],
        "customers": []
    }

    customer_map = {} # To group issues by customer
    all_assignees = set()

    for issue in jira_issues:
        # Ensure issue is a dictionary before proceeding
        if not isinstance(issue, dict):
            print(f"Warning: Skipping non-dictionary issue in formatted_issues: {issue}")
            continue

        assignee = issue.get('assignee')
        if assignee:
            all_assignees.add(assignee)
        else:
            all_assignees.add("Unassigned") # Add a default resource for unassigned tasks

        issue_customers = issue.get('customers', [])
        if not issue_customers:
            issue_customers = ["Unassigned Customer"] # Default customer

        for customer_name in issue_customers:
            if customer_name not in customer_map:
                customer_map[customer_name] = {
                    "name": customer_name,
                    "work_packets": []
                }
            
            # Ensure "Jira Issues" work packet exists for this customer
            work_packet = None
            for wp_item in customer_map[customer_name]["work_packets"]:
                if wp_item["name"] == "Jira Issues":
                    work_packet = wp_item
                    break
            if work_packet is None:
                work_packet = {
                    "name": "Jira Issues",
                    "tasks": []
                }
                customer_map[customer_name]["work_packets"].append(work_packet)

            # Map Jira issue to planner task format
            issue_key = issue.get('key')
            issue_summary = issue.get('summary')
            task_name = issue_key if issue_key else 'N/A'
            
            start_date_str = issue.get('created')
            if start_date_str:
                start_date = datetime.strptime(start_date_str.split('T')[0], '%Y-%m-%d')
            else:
                start_date = datetime.now() # Fallback to today if created date is missing

            due_date_str = issue.get('due')
            due_date = None
            duration_days = 7  # Default duration
            if due_date_str:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                duration_days = max(1, (due_date - start_date).days)  # Ensure at least 1 day duration
            else:
                # If no due date, duration is default and due_date remains None
                due_date = None

            # Use actual Jira status
            planner_status = issue.get('status', 'Pending')

            # Use status_color for health_color
            health_color = issue.get('status_color')
            
            work_packet["tasks"].append({
                "name": task_name,
                "start_date": start_date.strftime('%Y-%m-%d'),
                "duration_days": duration_days,
                "due_date": due_date.strftime('%Y-%m-%d') if due_date else None,
                "status": planner_status,
                "assignee": assignee if assignee else "Unassigned", # Add assignee to the task
                "health_color": health_color, # Add health color
                "task_health_status": issue.get('task_health_status'), # Add task health status
                "issue_type": issue.get('issue_type'), # Add issue type
                "is_subtask": issue.get('is_subtask'), # Add subtask status
                "parent_key": issue.get('parent_key'), # Add parent key
                "priority": issue.get('priority'), # Add priority name
                "priority_value": issue.get('priority_value'), # Add numerical priority value
                "sprint_name": issue.get('sprint_name'),
                "sprint_state": issue.get('sprint_state')
            })
    
    planner_data["resources"] = sorted(list(all_assignees))
    planner_data["customers"] = list(customer_map.values())

    return planner_data


def fetch_and_save_jira_issues(output_filename, raw_issues_debug_filename, jira_url, jql_query_file, jira_email=None, jira_api_token=None):


    """


    Fetches Jira issues, formats them, transforms them, and saves them to specified files.


    """


    email, api_token = get_jira_credentials(jira_url, jira_email, jira_api_token)


    if not email or not api_token:


        print("Email or API token not provided. Exiting.")


        return





    try:


        with open(jql_query_file, 'r') as f:


            jql_query_content = f.read().strip()


    except FileNotFoundError:


        print(f"Error: JQL query file not found at {jql_query_file}")


        return


    except Exception as e:


        print(f"Error reading JQL query file {jql_query_file}: {e}")


        return





    raw_issues = fetch_jira_issues_manually(jira_url, jql_query_content, email, api_token)


    if raw_issues is None:


        print("Failed to fetch issues from Jira. Exiting.")


        return


        


    print(f"Found {len(raw_issues)} issues.")





    # Save raw issues for debugging


    with open(raw_issues_debug_filename, 'w') as f:


        json.dump(raw_issues, f, indent=2)


    print(f"Raw Jira issues saved to {raw_issues_debug_filename} for debugging.")





    if len(raw_issues) == 0:


        print("\nNOTE: The script ran successfully but found 0 issues.")


        print("This could be due to a few reasons:")


        print("1. The JQL query returned no results. Please check the query in Jira.")


        print("2. The user associated with the API token may not have permission to view the requested issues.")


        print("3. The custom field IDs for 'Customers' or 'Health' might be incorrect.")





    formatted_issues = format_raw_issues(raw_issues)


    planner_data = transform_jira_to_planner_format(formatted_issues)





    with open(output_filename, 'w') as f:


        json.dump(planner_data, f, indent=2)


    print(f"Successfully generated {output_filename} with {len(formatted_issues)} issues transformed.")


    print("Remember to check and potentially update custom field IDs in the script for 'Customers' and 'Health'.")
