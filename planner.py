
import json
import re
from datetime import datetime, timedelta
import unicodedata
import pytz

# ANSI escape codes for colors
COLOR_CODES = {
    "blue-gray": "\033[90m",  # Gray (for To Do)
    "yellow": "\033[92m",     # Green (User requested 'In Progress' yellow to be green)
    "green": "\033[92m",      # Green
    "red": "\033[91m",        # Red
    "blue": "\033[94m",       # Blue (User requested 'Triage' to be blue)
    "purple": "\033[93m",     # Yellow (User requested 'Review' to be yellow, using purple for now as a placeholder for 'Review' status category)
    "orange": "\033[33m",     # Orange (using dark yellow)
    "medium-green": "\033[92m", # Green
    "dark-green": "\033[92m", # Green
    "dark-red": "\033[91m",   # Red
    "light-blue": "\033[94m", # Blue
    "light-green": "\033[92m",# Green
    "light-red": "\033[91m",  # Red
    "light-yellow": "\033[93m",# Yellow
    "light-purple": "\033[93m",# Yellow (Mapping purple to yellow for 'Review')
    "light-gray": "\033[90m", # Gray
    "dark-gray": "\033[90m",  # Gray
    "black": "\033[30m",      # Black
    "white": "\033[97m",      # White
    None: "\033[0m"           # Reset color
}
RESET_COLOR = "\033[0m"

# Schedule Status Colors
SCHEDULE_STATUS_COLORS = {
    "On Time": "\033[92m",    # Green
    "Late": "\033[93m",       # Yellow
    "Conflict!": "\033[91m",  # Red
    "Overdue": "\033[91m",    # Red
    "Error": "\033[91m",      # Red
    None: "\033[0m"           # Reset
}

# Priority Colors
PRIORITY_COLORS = {
    "P0": "red",
    "P1": "orange",
    "P2": "blue",
    "P3": "light-gray",
    None: "light-gray" # Default for None or unknown priorities
}

# Priority Order Map (for sorting, higher value means higher priority)
PRIORITY_ORDER_MAP = {
    "P0": 0,
    "P1": 1,
    "P2": 2,
    "P3": 3,
    None: 99 # Lower priority for None or unknown
}

# Regex to strip ANSI escape codes
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def get_display_width(text):
    """Calculates the display width of a string, ignoring ANSI escape codes and accounting for wide Unicode characters."""
    clean_text = ANSI_ESCAPE.sub('', text)
    width = 0
    for char in clean_text:
        if unicodedata.east_asian_width(char) in ('W', 'F'):
            width += 2
        else:
            width += 1
    return width

def get_colored_ball(color_name):
    """Returns a colored circle character using ANSI escape codes."""
    color_code = COLOR_CODES.get(color_name, COLOR_CODES[None])
    return f"{color_code}\u25CF{RESET_COLOR}" # Unicode for a solid circle

def get_schedule_status_colored_ball(status):
    """Returns a colored circle for schedule status."""
    color_code = SCHEDULE_STATUS_COLORS.get(status, SCHEDULE_STATUS_COLORS[None])
    return f"{color_code}\u25CF{RESET_COLOR}"

# Load configuration from planner_config.json
def load_config(config_filepath):
    """Loads configuration from a JSON file."""
    CONFIG = {}
    try:
        with open(config_filepath, 'r') as f:
            CONFIG = json.load(f)
    except FileNotFoundError:
        print(f"Error: {config_filepath} not found. Please ensure the file exists.")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"Error decoding {config_filepath}: {e}. Please check the file format.")
        exit(1)
    return CONFIG

# Load configuration from planner_config.json (this will be called by the new main function)
# CONFIG = load_config('planner_config.json') # This line will be removed or commented out
# RESOURCE_ALIASES = CONFIG.get('resource_aliases', {})
# CUSTOMER_ALIASES = CONFIG.get('customer_aliases', {})
# SORT_BY = CONFIG.get('sort_by', ['start_date']) # Default sort by start_date
# JIRA_BASE_URL = CONFIG.get('jira_base_url', "https://company.atlassian.net/browse/") # Default Jira URL

def load_data(filepath):
    """Loads project data from a JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def generate_plan(data, sort_by_fields, filters):
    """Generates a resource allocation plan, ignoring completed tasks and applying filters."""
    resource_schedules = {resource: [] for resource in data['resources']}
    
    all_tasks = []
    for customer in data['customers']:
        for packet in customer['work_packets']:
            for task in packet['tasks']: # This 'task' is the one being processed
                start_date_str = task.get('customfield_10015')
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
                
                fix_versions = task.get('fixVersions', [])
                fix_version_date = None
                fix_version_name = None
                if fix_versions:
                    # Assuming we take the releaseDate of the first fix version
                    for version in fix_versions:
                        if version.get('releaseDate'):
                            fix_version_date = datetime.strptime(version['releaseDate'], '%Y-%m-%d')
                            break # Take the first one found
                    if fix_versions and fix_versions[0].get('name'):
                        fix_version_name = fix_versions[0]['name']

                task_info = {
                    'customer': customer['name'],
                    'packet': packet['name'],
                    'task': task['name'],
                    'start_date': start_date,
                    'due_date': datetime.strptime(task['due_date'], '%Y-%m-%d') if task.get('due_date') else None,
                    'status': task.get('status', 'Pending'), # Default to Pending if not set
                    'assignee': task.get('assignee', 'Unassigned'), # Get assignee from task, default to Unassigned
                    'health_color': task.get('health_color'), # Get health color
                    'task_health_status': task.get('task_health_status'), # Get task health status
                    'issue_type': task.get('issue_type', 'Unknown'), # Add issue type, default to 'Unknown'
                    'is_subtask': task.get('is_subtask', False), # Add subtask status
                    'parent_key': task.get('parent_key'), # Add parent key
                    'estimated_hours': task.get('timeoriginalestimate'), # This value is already in hours
                    'priority': task.get('priority'), # Add priority name
                    'priority_value': PRIORITY_ORDER_MAP.get(task.get('priority'), PRIORITY_ORDER_MAP[None]), # Map priority name to numerical value
                    'fix_version_date': fix_version_date, # Add fix version date
                    'fix_version_name': fix_version_name,
                    'sprint_name': task.get('sprint_name'),
                    'sprint_state': task.get('sprint_state')
                }
                all_tasks.append(task_info)

    # Apply initial filters (resource, priority, task_status, customers, from_start_date, to_end_date)
    filtered_tasks = []
    from_start_date_filter = datetime.strptime(filters['from_start_date'], '%Y-%m-%d') if filters.get('from_start_date') and filters['from_start_date'] else None
    to_end_date_filter = datetime.strptime(filters['to_end_date'], '%Y-%m-%d') if filters.get('to_end_date') and filters['to_end_date'] else None

    for task in all_tasks:
        keep_task = True
        if filters.get('resource') and task['assignee'] not in filters['resource']:
            keep_task = False
        if filters.get('priority') and task['priority'] not in filters['priority']:
            keep_task = False
        if filters.get('task_status') and task['status'] not in filters['task_status']:
            keep_task = False
        if filters.get('customers') and task['customer'] not in filters['customers']:
            keep_task = False
        if from_start_date_filter and task['start_date'] and task['start_date'] < from_start_date_filter:
            keep_task = False
        if to_end_date_filter and task['fix_version_date'] and task['fix_version_date'] > to_end_date_filter: # Use fix_version_date as end date for filtering
            keep_task = False
        
        if keep_task:
            filtered_tasks.append(task)
    all_tasks = filtered_tasks

    # Apply sorting based on CONFIG
    def get_sort_key(task_item):
        keys = []
        for sort_field in sort_by_fields:
            if sort_field == 'start_date':
                # Handle None for start_date by treating it as a very late date
                start_date = task_item['start_date']
                keys.append(start_date if start_date is not None else datetime.max)
            elif sort_field == 'customer':
                keys.append(task_item['customer'])
            elif sort_field == 'resource':
                keys.append(task_item['assignee']) # Use assignee for resource sorting
            elif sort_field == 'priority':
                keys.append(task_item['priority_value']) # Use numerical priority for sorting
            # Add other sort fields here if needed
        return tuple(keys)

    all_tasks.sort(key=get_sort_key)

    # First pass: Populate resource_all_tasks_for_conflict_check with all tasks for each resource
    resource_all_tasks_for_conflict_check = {resource: [] for resource in data['resources']}
    for task in all_tasks:
        assigned_resource = task['assignee']
        if assigned_resource not in resource_all_tasks_for_conflict_check:
            resource_all_tasks_for_conflict_check[assigned_resource] = []

        task_effective_end_date = None
        if task['fix_version_date'] and (not task['start_date'] or task['fix_version_date'] >= task['start_date']):
            task_effective_end_date = task['fix_version_date']
        elif task['due_date']:
            task_effective_end_date = task['due_date']
        elif task['start_date']:
            task_effective_end_date = task['start_date'] + timedelta(days=1)

        if task['start_date'] and task_effective_end_date:
            resource_all_tasks_for_conflict_check[assigned_resource].append({
                'start': task['start_date'],
                'end': task_effective_end_date,
                'key': task['task'].split(' ')[0], # Store only the key here
                'issue_type': task['issue_type'],
                'parent_key': task['parent_key']
            })

    final_schedule = []
    for task in all_tasks:
        assigned_resource = task['assignee']
        schedule_status = "On Time"
        conflicting_tasks_details = []

        # Only schedule tasks that are not completed
        if task['status'] != 'Completed':
            # Determine the effective end date for the current task for conflict checking
            task_effective_end_date = None
            if task['fix_version_date'] and (not task['start_date'] or task['fix_version_date'] >= task['start_date']):
                task_effective_end_date = task['fix_version_date']
            elif task['due_date']:
                task_effective_end_date = task['due_date']
            elif task['start_date']:
                task_effective_end_date = task['start_date'] + timedelta(days=1)

            # Extract only the Jira key from task['task'] for comparison
            current_task_key_only = task['task'].split(' ')[0]

            # Check for conflicts with other tasks assigned to the same resource
            is_free = True
            for scheduled_task_info in resource_all_tasks_for_conflict_check.get(assigned_resource, []):
                scheduled_start = scheduled_task_info['start']
                scheduled_end = scheduled_task_info['end']
                scheduled_task_key = scheduled_task_info['key']
                scheduled_issue_type = scheduled_task_info['issue_type']
                scheduled_parent_key = scheduled_task_info['parent_key']

                if scheduled_task_key == current_task_key_only: # Don't compare a task with itself
                    continue

                # Ensure both tasks have valid start and effective end dates for comparison
                if task['start_date'] and task_effective_end_date and \
                   scheduled_start and scheduled_end and \
                   task['start_date'] < scheduled_end and task_effective_end_date > scheduled_start:
                    # Hierarchical conflict logic:
                    hierarchical_conflict_condition = (task['parent_key'] and task['parent_key'] == scheduled_task_key) or \
                                                      (scheduled_parent_key and scheduled_parent_key == current_task_key_only) or \
                                                      (task['issue_type'] == 'Epic' and scheduled_parent_key == current_task_key_only) or \
                                                      (scheduled_issue_type == 'Epic' and task['parent_key'] == scheduled_task_key)
                    
                    if hierarchical_conflict_condition:
                        continue # No conflict due to hierarchy
                    
                    is_free = False
                    # Store only the conflicting Jira key as requested
                    conflicting_tasks_details.append(scheduled_task_key)
            
            # Decide schedule_status based on conflicts and dates
            if not task['due_date']:
                schedule_status = "Error"
            elif conflicting_tasks_details:
                schedule_status = "Conflict!"
            else:
                # Overdue check (using due_date as end date)
                if task['due_date'] and task['due_date'].date() < datetime.now().date():
                    schedule_status = "Overdue"
                # "Late" check using fix_version_date vs due_date
                elif task['fix_version_date'] and task['due_date'] and task['fix_version_date'] > task['due_date']:
                    schedule_status = "Late"
        
        final_schedule.append({
            'resource': assigned_resource,
            'customer': task['customer'],
            'task': task['task'],
            'start_date': task['start_date'],
            'due_date': task['due_date'],
            'task_status': task['status'],
            'schedule_status': schedule_status,
            'health_color': task['health_color'], # Pass health color to final schedule
            'task_health_status': task['task_health_status'], # Pass task health status to final schedule
            'conflicting_tasks': conflicting_tasks_details, # Pass conflicting tasks details
            'issue_type': task['issue_type'], # Pass issue type to final schedule
            'estimated_hours': task['estimated_hours'], # Pass estimated hours to final schedule
            'priority': task['priority'], # Pass priority name to final schedule
            'fix_version_date': task['fix_version_date'], # Pass fix version date to final schedule
            'fix_version_name': task['fix_version_name'],
            'sprint_name': task['sprint_name'],
            'sprint_state': task['sprint_state']
        })

    # Apply post-generation filters (schedule_status, conflict)
    post_filtered_schedule = []
    for entry in final_schedule:
        keep_entry = True
        if filters.get('schedule_status') and entry['schedule_status'] not in filters['schedule_status']:
            keep_entry = False
        if filters.get('conflict') == ["True"] and not entry['conflicting_tasks']: # Only show conflicts if "True" is explicitly in filter
            keep_entry = False
        if filters.get('conflict') == ["False"] and entry['conflicting_tasks']: # Only show non-conflicts if "False" is explicitly in filter
            keep_entry = False
        
        if keep_entry:
            post_filtered_schedule.append(entry)

    return post_filtered_schedule

def print_schedule(schedule):
    """Prints the generated schedule in a readable format with dynamic column widths."""
    
    # Define column names for iteration and initial header widths
    column_names = ['Resource', 'Customer', 'Task', 'Priority', 'Task Status', 'Estimation', 'Start Date', 'Due Date', 'Fix Version', 'Sprint', 'Schedule Status', 'Conflicts']
    max_col_widths = {name: get_display_width(name) for name in column_names}

    # First pass: Calculate maximum display width for each column based on content
    for entry in schedule:
        resource_display_name_plain = RESOURCE_ALIASES.get(entry['resource'], entry['resource'])
        customer_display_name_plain = CUSTOMER_ALIASES.get(entry['customer'], entry['customer'])
        
        task_display_name_plain = entry['task']
        if entry['task_health_status']:
            task_display_name_plain = f"{task_display_name_plain} ({entry['task_health_status']})"
        
        task_status_display_plain = entry['task_status'] # Plain status, no ball
        
        schedule_status_display_plain = entry['schedule_status'] # Plain status, no ball

        # Conflicts: now stored as a simple list of Jira keys
        conflicts_display_plain = ", ".join(entry['conflicting_tasks']) if entry['conflicting_tasks'] else ""

        # Calculate task_status_display_with_ball for width calculation
        health_ball_for_width = get_colored_ball(entry['health_color']) if entry['health_color'] else " "
        task_status_display_with_ball = f"{health_ball_for_width} {entry['task_status']}"

        # Calculate schedule_status_display_with_ball for width calculation
        schedule_status_ball_for_width = get_schedule_status_colored_ball(entry['schedule_status'])
        schedule_status_display_with_ball = f"{schedule_status_ball_for_width} {entry['schedule_status']}"

        # Format estimated hours for width calculation
        estimated_hours_display = str(entry['estimated_hours']) if entry['estimated_hours'] is not None else "N/A"

        priority_display_plain = entry['priority'] if entry['priority'] is not None else "N/A"

        fix_version_display_plain = entry['fix_version_name'] if entry.get('fix_version_name') else "N/A"
        sprint_display_plain = entry['sprint_name'] if entry.get('sprint_name') else "N/A"
        if entry.get('sprint_state'):
            sprint_display_plain += f" ({entry['sprint_state']})"

        max_col_widths['Resource'] = max(max_col_widths['Resource'], get_display_width(resource_display_name_plain))
        max_col_widths['Customer'] = max(max_col_widths['Customer'], get_display_width(customer_display_name_plain))
        max_col_widths['Task'] = max(max_col_widths['Task'], get_display_width(task_display_name_plain))
        max_col_widths['Priority'] = max(max_col_widths['Priority'], get_display_width(priority_display_plain))
        max_col_widths['Task Status'] = max(max_col_widths['Task Status'], get_display_width(task_status_display_with_ball))
        max_col_widths['Estimation'] = max(max_col_widths['Estimation'], get_display_width(estimated_hours_display))
        max_col_widths['Start Date'] = max(max_col_widths['Start Date'], get_display_width(entry['start_date'].strftime('%Y-%m-%d') if entry['start_date'] else "N/A"))
        max_col_widths['Fix Version'] = max(max_col_widths['Fix Version'], get_display_width(fix_version_display_plain))
        max_col_widths['Sprint'] = max(max_col_widths['Sprint'], get_display_width(sprint_display_plain))
        max_col_widths['Due Date'] = max(max_col_widths['Due Date'], get_display_width(entry['due_date'].strftime('%Y-%m-%d') if entry['due_date'] else "N/A"))
        max_col_widths['Schedule Status'] = max(max_col_widths['Schedule Status'], get_display_width(schedule_status_display_with_ball))
        max_col_widths['Conflicts'] = max(max_col_widths['Conflicts'], get_display_width(conflicts_display_plain))

    # Add a minimum width to prevent very narrow columns, and a little extra padding
    # Add a minimum width to prevent very narrow columns
    for key in max_col_widths:
        max_col_widths[key] = max(max_col_widths[key], 5)

    # Construct header using dynamic widths
    header_parts = []
    for name in column_names:
        header_parts.append(f"{name:<{max_col_widths[name]}}")
    header = " | ".join(header_parts)
    
    # Group tasks for separate summaries
    grouped_schedule = {}
    for entry in schedule:
        issue_type = entry.get('issue_type') or 'Unknown'
        task_health_status = entry.get('task_health_status') or 'Unknown'
        
        if issue_type not in grouped_schedule:
            grouped_schedule[issue_type] = {}
        if task_health_status not in grouped_schedule[issue_type]:
            grouped_schedule[issue_type][task_health_status] = []
        grouped_schedule[issue_type][task_health_status].append(entry)

    # Print summaries
    # Define the desired order of issue types
    issue_type_order = ["CODE", "BUG", "TASK", "EPIC"]
    
    # Get all unique issue types from the grouped schedule
    all_issue_types = list(grouped_schedule.keys())
    
    # Sort them according to the desired order, placing unknown types at the end
    sorted_issue_types = sorted(all_issue_types, key=lambda x: (issue_type_order.index(x.upper()) if x.upper() in issue_type_order else len(issue_type_order)))

    for issue_type in sorted_issue_types:
        health_groups = grouped_schedule[issue_type]
        
        # if issue_type.upper() == "EPIC":
        # print("\n" + "=" * (sum(max_col_widths.values()) + (len(column_names) - 1) * 3)) # Adjust separator width
        # print("=" * (sum(max_col_widths.values()) + (len(column_names) - 1) * 3)) # Adjust separator width
    
        print("\n===================================")
        print(f"\033[1;38;5;208m--- Issue Type: [{issue_type.upper()}] ---\033[0m")
        print("===================================")

        health_status_order = ["🟢 On Track", "🟡 At Risk", "🔴 Off Track", "🟣 Postponed"]
        sorted_health_statuses = sorted(health_groups.keys(), key=lambda x: (health_status_order.index(x) if x in health_status_order else len(health_status_order)))
        for health_status in sorted_health_statuses:
            tasks = health_groups[health_status]

            print("\n" + "="*50)
            print(f"\033[1;96m>>>   HEALTH STATUS: {health_status.upper()}   <<<\033[0m")
            print("="*50)

            separator_row_parts = []
            for name in column_names:
                separator_row_parts.append("-" * max_col_widths[name])
            print("-" * (sum(max_col_widths.values()) + (len(column_names) - 1) * 3))
            # Print header row
            header_row_parts = []
            for name in column_names:
                header_row_parts.append(f"{name:<{max_col_widths[name]}}")
            print(" | ".join(header_row_parts))

            # Print separator row
            print("-" * (sum(max_col_widths.values()) + (len(column_names) - 1) * 3))
            
            for entry in tasks:
                resource_display_name = RESOURCE_ALIASES.get(entry['resource'], entry['resource'])
                customer_display_name = CUSTOMER_ALIASES.get(entry['customer'], entry['customer'])
                
                health_ball = get_colored_ball(entry['health_color']) if entry['health_color'] else " "
                
                # Combine task name and task health status
                task_display_name = entry['task']
                if entry['task_health_status']:
                    task_display_name = f"{task_display_name} ({entry['task_health_status']})"

                # Adjust task status column width to accommodate the ball
                task_status_display = f"{health_ball} {entry['task_status']}"

                # Add color ball to schedule status
                schedule_status_ball = get_schedule_status_colored_ball(entry['schedule_status'])
                schedule_status_display = f"{schedule_status_ball} {entry['schedule_status']}"

                # Format conflicting tasks: show only Jira keys in the conflicts column
                conflicts_display = ", ".join(entry['conflicting_tasks']) if entry['conflicting_tasks'] else ""
                
                # Print row, calculating padding dynamically
                row_parts = []
                
                # Resource
                current_display_width = get_display_width(resource_display_name)
                padding = max_col_widths['Resource'] - current_display_width
                row_parts.append(f"{resource_display_name}{' ' * padding}")

                # Customer
                current_display_width = get_display_width(customer_display_name)
                padding = max_col_widths['Customer'] - current_display_width
                row_parts.append(f"{customer_display_name}{' ' * padding}")

                # Task
                current_display_width = get_display_width(task_display_name)
                padding = max_col_widths['Task'] - current_display_width
                row_parts.append(f"{task_display_name}{' ' * padding}")

                # Priority
                priority_name = entry['priority']
                priority_color = PRIORITY_COLORS.get(priority_name, None)
                priority_ball = get_colored_ball(priority_color)
                priority_display = f"{priority_ball} {priority_name}" if priority_name is not None else "N/A"
                current_display_width = get_display_width(priority_display)
                padding = max_col_widths['Priority'] - current_display_width
                row_parts.append(f"{priority_display}{' ' * padding}")

                # Task Status
                current_display_width = get_display_width(task_status_display)
                padding = max_col_widths['Task Status'] - current_display_width
                row_parts.append(f"{task_status_display}{' ' * padding}")

                # Estimation
                estimated_hours_display = str(entry['estimated_hours']) if entry['estimated_hours'] is not None else "N/A"
                current_display_width = get_display_width(estimated_hours_display)
                padding = max_col_widths['Estimation'] - current_display_width
                row_parts.append(f"{estimated_hours_display}{' ' * padding}")

                # Start Date
                start_date_str = entry['start_date'].strftime('%Y-%m-%d') if entry['start_date'] else "N/A"
                current_display_width = get_display_width(start_date_str)
                padding = max_col_widths['Start Date'] - current_display_width
                row_parts.append(f"{start_date_str}{' ' * padding}")

                # Due Date
                due_date_str = entry['due_date'].strftime('%Y-%m-%d') if entry['due_date'] else "N/A"
                current_display_width = get_display_width(due_date_str)
                padding = max_col_widths['Due Date'] - current_display_width
                row_parts.append(f"{due_date_str}{' ' * padding}")

                # Fix Version
                fix_version_str = entry['fix_version_name'] if entry.get('fix_version_name') else "N/A"
                current_display_width = get_display_width(fix_version_str)
                padding = max_col_widths['Fix Version'] - current_display_width
                row_parts.append(f"{fix_version_str}{' ' * padding}")

                # Sprint
                sprint_str = entry['sprint_name'] if entry.get('sprint_name') else "N/A"
                if entry.get('sprint_state'):
                    sprint_str += f" ({entry['sprint_state']})"
                current_display_width = get_display_width(sprint_str)
                padding = max_col_widths['Sprint'] - current_display_width
                row_parts.append(f"{sprint_str}{' ' * padding}")

                # Schedule Status
                current_display_width = get_display_width(schedule_status_display)
                padding = max_col_widths['Schedule Status'] - current_display_width
                row_parts.append(f"{schedule_status_display}{' ' * padding}")

                # Conflicts
                current_display_width = get_display_width(conflicts_display)
                padding = max_col_widths['Conflicts'] - current_display_width
                row_parts.append(f"{conflicts_display}{' ' * padding}")

                print(" | ".join(row_parts))
            print("-" * (sum(max_col_widths.values()) + (len(column_names) - 1) * 3))

def generate_and_print_schedule(projects_file, raw_issues_file, config_file):
    """
    Generates and prints the project schedule based on provided data files and configuration.
    """
    global RESOURCE_ALIASES, CUSTOMER_ALIASES, JIRA_BASE_URL

    CONFIG = load_config(config_file)
    
    RESOURCE_ALIASES = CONFIG.get('resource_aliases', {})
    CUSTOMER_ALIASES = CONFIG.get('customer_aliases', {})
    SORT_BY = CONFIG.get('sort_by', ['start_date']) # Default sort by start_date
    JIRA_BASE_URL = CONFIG.get('jira_base_url', "https://company.atlassian.net/browse/")
    JQL_QUERY_FILE = CONFIG.get('jql_query_file', "config/jql_query.txt")
    FILTERS = CONFIG.get('filter', {}) # Load filter configuration
    
    try:
        project_data = load_data(projects_file)
        raw_jira_issues = load_data(raw_issues_file)

        # Create a mapping from Jira issue key to relevant Jira fields
        jira_issue_details = {}
        for issue in raw_jira_issues:
            key = issue['key']
            jira_issue_details[key] = {
                'timeoriginalestimate': round(issue['fields'].get('timeoriginalestimate') / 3600, 2) if issue['fields'].get('timeoriginalestimate') is not None else None,
                'customfield_10015': issue['fields'].get('customfield_10015'),
                'fixVersions': issue['fields'].get('fixVersions', [])
            }

        # Enrich project_data with estimated_hours, customfield_10015, and fixVersions
        for customer in project_data['customers']:
            for packet in customer['work_packets']:
                for task in packet['tasks']:
                    task_key = task['name'].split(' ')[0] # Assuming task name starts with Jira key
                    details = jira_issue_details.get(task_key, {})
                    task['timeoriginalestimate'] = details.get('timeoriginalestimate')
                    task['customfield_10015'] = details.get('customfield_10015')
                    task['fixVersions'] = details.get('fixVersions', [])

        project_schedule = generate_plan(project_data, SORT_BY, FILTERS) # Pass FILTERS to generate_plan
        print_schedule(project_schedule)
    except FileNotFoundError as e:
        print(f"Error: {e.filename} not found. Please ensure the file exists.")
        exit(1)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error processing JSON files: {e}. Please check the file formats and ensure required fields are present.")
        exit(1)

def print_pdm_schedule(raw_issues_file, config_file):
    """
    Prints PDM schedule grouped by customer.
    
    Args:
        raw_issues_file: Path to raw Jira issues JSON
        config_file: Path to planner config JSON
    """
    from collections import defaultdict
    
    # Load config
    CONFIG = load_config(config_file)
    JIRA_BASE_URL = CONFIG.get('jira_base_url', "https://sibros.atlassian.net/browse/")
    
    # Load raw issues
    with open(raw_issues_file, 'r') as f:
        raw_issues = json.load(f)
    
    # Priority mapping for sorting (P0 is highest)
    PRIORITY_ORDER = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}
    
    # Group by customer
    customer_releases = defaultdict(list)
    
    for issue in raw_issues:
        key = issue['key']
        fields = issue['fields']
        
        # Build URL
        if not JIRA_BASE_URL.endswith('/'):
            JIRA_BASE_URL += '/'
        ticket_url = f"{JIRA_BASE_URL}{key}"
        
        # Extract customer
        customers_field = fields.get('customfield_10080', [])
        priority_name = fields.get('priority', {}).get('name', 'P3')
        
        if customers_field:
            for customer in customers_field:
                customer_name = customer.get('value', 'Unknown')
                customer_releases[customer_name].append({
                    'key': key,
                    'summary': fields.get('summary', 'N/A'),
                    'fw_version': fields.get('customfield_10168', {}).get('value', 'N/A') if isinstance(fields.get('customfield_10168'), dict) else 'N/A',
                    'planned_due_date': fields.get('customfield_10150', 'N/A'),
                    'due_date': fields.get('duedate', 'N/A'),
                    'health': fields.get('customfield_10119', {}).get('value', 'N/A') if isinstance(fields.get('customfield_10119'), dict) else 'N/A',
                    'priority': priority_name,
                    'priority_order': PRIORITY_ORDER.get(priority_name, 99),
                    'status': fields.get('status', {}).get('name', 'N/A'),
                    'risk': fields.get('customfield_10134', {}).get('value', 'N/A') if isinstance(fields.get('customfield_10134'), dict) else 'N/A',
                    'url': ticket_url,
                })
        else:
            # No customer assigned
            customer_releases['Unassigned'].append({
                'key': key,
                'summary': fields.get('summary', 'N/A'),
                'fw_version': fields.get('customfield_10168', {}).get('value', 'N/A') if isinstance(fields.get('customfield_10168'), dict) else 'N/A',
                'planned_due_date': fields.get('customfield_10150', 'N/A'),
                'due_date': fields.get('duedate', 'N/A'),
                'health': fields.get('customfield_10119', {}).get('value', 'N/A') if isinstance(fields.get('customfield_10119'), dict) else 'N/A',
                'priority': priority_name,
                'priority_order': PRIORITY_ORDER.get(priority_name, 99),
                'status': fields.get('status', {}).get('name', 'N/A'),
                'risk': fields.get('customfield_10134', {}).get('value', 'N/A') if isinstance(fields.get('customfield_10134'), dict) else 'N/A',
                'url': ticket_url,
            })
    
    # Print schedule
    print("\n" + "=" * 200)
    print("PDM SCHEDULE - CUSTOMER RELEASES")
    print("=" * 200)
    
    def get_display_width(text):
        """Calculate the display width of text, accounting for wide characters like emojis"""
        width = 0
        for char in str(text):
            # Emojis and other wide characters typically take 2 columns
            if ord(char) > 0x1F300:  # Emoji range starts around here
                width += 2
            else:
                width += 1
        return width
    
    def pad_text(text, target_width):
        """Pad text to target width, accounting for emoji display width"""
        text = str(text)
        current_width = get_display_width(text)
        padding_needed = target_width - current_width
        if padding_needed > 0:
            return text + ' ' * padding_needed
        return text
    
    for customer in sorted(customer_releases.keys()):
        releases = customer_releases[customer]
        
        # Sort by priority (P0 first, then P1, P2, P3)
        releases.sort(key=lambda x: x['priority_order'])
        
        print(f"\n{'='*200}")
        print(f"CUSTOMER: {customer}")
        print(f"{'='*200}")
        print(f"{'Priority':<10} | {'Status':<15} | {'FW Version':<15} | {'Planned Due':<12} | {'Due Date':<12} | {'Health':<25} | {'Risk':<25} | {'URL':<67}")
        print("-" * 200)
        
        for release in releases:
            # Convert None to 'N/A' for display
            priority = release['priority'] or 'N/A'
            status = release['status'] or 'N/A'
            fw_version = release['fw_version'] or 'N/A'
            planned_due_date = release['planned_due_date'] or 'N/A'
            due_date = release['due_date'] or 'N/A'
            health = release['health'] or 'N/A'
            risk = release['risk'] or 'N/A'
            url = release['url'] or 'N/A'
            
            # Use custom padding for emoji-containing fields
            priority_str = f"{priority:<10}"
            status_str = f"{status:<15}"
            fw_version_str = f"{fw_version:<15}"
            planned_str = f"{planned_due_date:<12}"
            due_str = f"{due_date:<12}"
            health_str = pad_text(health, 25)
            risk_str = pad_text(risk, 25)
            url_str = f"{url:<67}"
            
            print(f"{priority_str} | {status_str} | {fw_version_str} | {planned_str} | {due_str} | {health_str} | {risk_str} | {url_str}")
        
        print("-" * 200)
    
    print("\n")



def print_ps_schedule(raw_issues_file, config_file, show_status=False):
    """
    Prints Professional Services schedule grouped by customer.
    
    Args:
        raw_issues_file: Path to raw Jira issues JSON
        config_file: Path to planner config JSON
        show_status: If True, show last worklog date/time
    """
    from collections import defaultdict
    from datetime import datetime
    import re
    
    # Load config
    CONFIG = load_config(config_file)
    JIRA_BASE_URL = CONFIG.get('jira_base_url', "https://sibros.atlassian.net/browse/")
    PS_SUMMARY_FILTER = CONFIG.get('ps_summary_filter', None)
    TIMEZONE = CONFIG.get('timezone', 'UTC')
    
    # Load raw issues
    with open(raw_issues_file, 'r') as f:
        raw_issues = json.load(f)
    
    # Group issues by customer
    customer_services = defaultdict(list)
    
    for issue in raw_issues:
        fields = issue.get('fields', {})
        key = issue.get('key')
        summary = fields.get('summary', 'No Summary')
        
        # Apply summary filter if configured
        if PS_SUMMARY_FILTER:
            if not re.search(PS_SUMMARY_FILTER, summary, re.IGNORECASE):
                continue
        
        # Get customer info
        customers_field = fields.get('customfield_10080', [])  # Customers field
        if not customers_field:
            customers_field = [{"value": "Unassigned Customer"}]
        
        # Get last worklog if status requested
        last_worklog = None
        time_logged = None
        if show_status:
            worklog_data = fields.get('worklog', {})
            worklogs = worklog_data.get('worklogs', [])

            if worklogs:
                # Sort by 'started' field to get the most recent worklog
                sorted_worklogs = sorted(worklogs, key=lambda w: w.get('started', ''), reverse=True)
                latest = sorted_worklogs[0]

                # Parse the timestamp from the 'started' field
                started_str = latest.get('started', '')
                if started_str:
                    dt = None
                    try:
                        # Handles formats like: 2025-10-09T05:40:11.465-0700
                        dt = datetime.strptime(started_str, '%Y-%m-%dT%H:%M:%S.%f%z')
                    except ValueError:
                        try:
                            # Fallback for UTC 'Z' format: 2024-11-26T10:30:00.000Z
                            dt = datetime.strptime(started_str, '%Y-%m-%dT%H:%M:%S.%fZ')
                            # Attach UTC timezone info
                            dt = dt.replace(tzinfo=pytz.utc)
                        except (ValueError, TypeError):
                            # If all parsing fails, use fallback display
                            last_worklog = started_str[:16].replace('T', ' ')
                    
                    if dt:
                        # Convert to the configured timezone
                        target_tz = pytz.timezone(TIMEZONE)
                        dt_converted = dt.astimezone(target_tz)
                        
                        # Format for display, e.g., "November 27, 2025 at 12:00 PM"
                        last_worklog = dt_converted.strftime('%B %d, %Y at %I:%M %p')
                        
                # Get time spent for the latest worklog
                time_spent_seconds = latest.get('timeSpentSeconds', 0)
                if time_spent_seconds:
                    hours = time_spent_seconds // 3600
                    minutes = (time_spent_seconds % 3600) // 60
                    
                    if hours > 0:
                        time_logged = f"logged {hours}h {minutes}m"
                    else:
                        time_logged = f"logged {minutes}m"
                else:
                    time_logged = "logged 0m"
        
        for customer_obj in customers_field:
            customer_name = customer_obj.get('value', 'Unknown Customer')
            customer_services[customer_name].append({
                'key': key,
                'summary': summary,
                'url': f"{JIRA_BASE_URL}{key}",
                'last_worklog': last_worklog,
                'time_logged': time_logged
            })
    
    # Sort customer names
    sorted_customers = sorted(customer_services.keys())
    
    # Print header
    print("\n" + "=" * 140)
    print("PROFESSIONAL SERVICES SCHEDULE")
    print("=" * 140)
    
    # Print services grouped by customer
    for customer in sorted_customers:
        services = customer_services[customer]
        
        print("\n" + "=" * 140)
        print(f"CUSTOMER: {customer}")
        print("=" * 140)
        
        if show_status:
            print(f"{'Professional Service':<50} | {'Last Worklog':<35} | {'Time Logged':<15}")
        else:
            print(f"{'Professional Service':<50} | {'URL':<67}")
        print("-" * 140)
        
        for service in services:
            # Convert None to 'N/A' for display
            key = service['key'] or 'N/A'
            summary = service['summary'] or 'N/A'
            url = service['url'] or 'N/A'
            last_worklog = service.get('last_worklog') or 'Never'
            time_logged = service.get('time_logged') or '-'
            
            # Create display string first, then truncate if needed
            ps_display = f"{key} - {summary}"
            if len(ps_display) > 50:
                ps_display = ps_display[:47] + "..."
            
            if show_status:
                print(f"{ps_display:<50} | {last_worklog:<35} | {time_logged:<15}")
            else:
                print(f"{ps_display:<50} | {url:<67}")
        
    
    print("\n")


def print_sprint_schedule(raw_issues_file, config_file):
    """
    Prints Sprint schedule listing ticket number, title, and current status.
    
    Args:
        raw_issues_file: Path to raw Jira issues JSON
        config_file: Path to planner config JSON
    """
    # Load raw issues
    with open(raw_issues_file, 'r') as f:
        raw_issues = json.load(f)
        
    print("\n" + "=" * 160)
    print("SPRINT REPORT")
    print("=" * 160)
    
    # Header
    print(f"{'Ticket':<15} | {'Status':<20} | {'Sprint':<40} | {'Title':<80}")
    print("-" * 160)
    
    for issue in raw_issues:
        key = issue.get('key', 'N/A')
        fields = issue.get('fields', {})
        summary = fields.get('summary', 'No Summary')
        status = fields.get('status', {}).get('name', 'N/A')
        
        # Filter for active sprints and get name
        sprint_field = fields.get('customfield_10020')
        active_sprint_name = "N/A"
        is_active_sprint = False
        if sprint_field and isinstance(sprint_field, list):
            for sprint in sprint_field:
                if sprint.get('state') == 'active':
                    is_active_sprint = True
                    active_sprint_name = sprint.get('name', 'Unknown Sprint')
                    break
        
        if not is_active_sprint:
            continue
        
        # Color code status
        status_color = ""
        if status in ["In Progress", "In Review"]:
            status_color = "\033[94m" # Blue
        elif status in ["Done", "Resolved", "Closed"]:
            status_color = "\033[92m" # Green
        elif status in ["To Do", "Open"]:
            status_color = "\033[90m" # Gray
            
        reset_color = "\033[0m"
        
        print(f"{key:<15} | {status_color}{status:<20}{reset_color} | {active_sprint_name:<40} | {summary:<80}")
        
    print("-" * 160)
    print("\n")

def log_work_from_calendar(raw_issues_file, calendar_events_file, config_file):
    """
    Reads calendar events and logs work to matching PS tickets in Jira.
    
    Args:
        raw_issues_file: Path to raw Jira issues JSON
        calendar_events_file: Path to saved calendar events JSON
        config_file: Path to planner config JSON
    """
    import os
    import requests
    from collections import defaultdict
    
    # Load configuration
    CONFIG = load_config(config_file)
    JIRA_BASE_URL = CONFIG.get('jira_base_url', "https://sibros.atlassian.net/browse/").replace('/browse/', '')
    PS_SUMMARY_FILTER = CONFIG.get('ps_summary_filter', None)
    TIMEZONE = CONFIG.get('timezone', 'UTC')
    
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
            if not re.search(PS_SUMMARY_FILTER, summary, re.IGNORECASE):
                continue
        
        # Get customers
        customers_field = fields.get('customfield_10080', [])
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
        
        # Extract customer name from title
        matched_customer = None
        for customer_name in customer_tickets.keys():
            if customer_name.lower() in title.lower():
                matched_customer = customer_name
                break
        
        if not matched_customer:
            print(f"⊘ Skipped: No matching PS customer found")
            skipped_count += 1
            continue
        
        tickets = customer_tickets[matched_customer]
        if not tickets:
            print(f"⊘ Skipped: No PS tickets for {matched_customer}")
            skipped_count += 1
            continue
        
        ticket = tickets[0]  # Use first ticket
        ticket_key = ticket['key']
        issue_data = ticket['issue']
        
        print(f"✓ Matched: {ticket_key} ({matched_customer})")
        
        # Calculate duration
        if start_time != 'All Day' and end_time != 'All Day':
            try:
                start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
                end_dt = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
                duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
                
                # Check existing worklogs
                worklog_data = issue_data['fields'].get('worklog', {})
                existing_worklogs = worklog_data.get('worklogs', [])
                
                already_logged = False
                for wl in existing_worklogs:
                    wl_started = wl.get('started', '')
                    if date in wl_started:
                        already_logged = True
                        print(f"⊘ Skipped: Already logged on {date}")
                        break
                
                if already_logged:
                    skipped_count += 1
                    continue
                
                # Log work
                # Convert local time to UTC for Jira
                local_tz = pytz.timezone(TIMEZONE)
                local_dt = local_tz.localize(start_dt)
                utc_dt = local_dt.astimezone(pytz.utc)
                
                # Format for Jira: 2025-11-27T10:00:00.000+0000
                started_str = utc_dt.strftime('%Y-%m-%dT%H:%M:%S.000+0000')
                
                print(f"   (Time: {start_time} {TIMEZONE} -> {started_str} UTC)")

                worklog_payload = {
                    "timeSpent": f"{duration_minutes}m",
                    "started": started_str,
                    "comment": {
                        "type": "doc",
                        "version": 1,
                        "content": [{
                            "type": "paragraph",
                            "content": [{
                                "type": "text",
                                "text": f"Meeting: {title}"
                            }]
                        }]
                    }
                }
                
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
                    print(f"✗ Error: {response.status_code} - {response.text[:100]}")
                    error_count += 1
                    
            except Exception as e:
                print(f"✗ Error: {e}")
                error_count += 1
        else:
            print(f"⊘ Skipped: All-day event")
            skipped_count += 1
    
    print(f"\n{'='*100}")
    print(f"SUMMARY")
    print(f"{'='*100}")
    print(f"✓ Logged:  {logged_count}")
    print(f"⊘ Skipped: {skipped_count}")
    print(f"✗ Errors:  {error_count}")
    print()



def print_ticket_details(ticket_key, raw_issues_file, config_file):
    """
    Prints detailed information about a specific Jira ticket.
    """
    try:
        raw_issues = load_data(raw_issues_file)
        CONFIG = load_config(config_file)
        jira_base_url = CONFIG.get('jira_base_url', "https://company.atlassian.net/browse/")
    except FileNotFoundError as e:
        print(f"Error: {e.filename} not found. Please ensure the file exists.")
        return
    except json.JSONDecodeError:
        print(f"Error decoding file. Please check the file format.")
        return

    issue = next((i for i in raw_issues if i.get('key') == ticket_key), None)

    if not issue:
        print(f"Ticket {ticket_key} not found.")
        return

    fields = issue.get('fields', {})
    
    # Helper to safely get field values
    def get_val(data, key, default="N/A"):
        val = data.get(key)
        return val if val is not None else default

    summary = get_val(fields, 'summary')
    status = get_val(get_val(fields, 'status', {}), 'name')
    status_color = get_val(get_val(get_val(fields, 'status', {}), 'statusCategory', {}), 'colorName')
    priority = get_val(get_val(fields, 'priority', {}), 'name')
    assignee = get_val(get_val(fields, 'assignee', {}), 'displayName', "Unassigned")
    reporter = get_val(get_val(fields, 'reporter', {}), 'displayName')
    created = get_val(fields, 'created')
    updated = get_val(fields, 'updated')
    description = get_val(fields, 'description', "No description provided.")
    
    # New fields
    # Customer (customfield_10080)
    customers_field = get_val(fields, 'customfield_10080', [])
    customers = ", ".join([c.get('value') for c in customers_field]) if customers_field != "N/A" else "N/A"

    # Health Status (customfield_10001 or customfield_10119)
    # Using customfield_10119 as it seems to be 'Task Health Status' in fetch_jira_issues.py
    # But let's check both or stick to what fetch_jira_issues uses.
    # fetch_jira_issues uses 10119 for "task_health_status" and 10001 for "health".
    # The user asked for "Health status". Let's try 10119 first as it matches the schedule view.
    health_status = get_val(get_val(fields, 'customfield_10119', {}), 'value', "N/A")
    
    # Estimation (timeoriginalestimate in seconds)
    estimation_seconds = get_val(fields, 'timeoriginalestimate', None)
    estimation_hours = f"{estimation_seconds / 3600:.1f}h" if estimation_seconds is not None else "N/A"

    # Start Date (customfield_10015 or created)
    start_date = get_val(fields, 'customfield_10015', "N/A")

    # Due Date (duedate)
    due_date = get_val(fields, 'duedate', "N/A")

    # Fix Version
    fix_versions_field = get_val(fields, 'fixVersions', [])
    fix_versions = ", ".join([fv.get('name') for fv in fix_versions_field]) if fix_versions_field != "N/A" else "N/A"

    # Sprint
    sprint_field = get_val(fields, 'customfield_10020', [])
    sprint_info = "N/A"
    if sprint_field != "N/A" and isinstance(sprint_field, list):
        # Find active sprint, then future, then closed
        active_sprints = [s for s in sprint_field if s.get('state') == 'active']
        future_sprints = [s for s in sprint_field if s.get('state') == 'future']
        closed_sprints = [s for s in sprint_field if s.get('state') == 'closed']
        
        selected_sprint = None
        if active_sprints:
            selected_sprint = active_sprints[0]
        elif future_sprints:
            selected_sprint = future_sprints[0]
        elif closed_sprints:
            selected_sprint = closed_sprints[0]
            
        if selected_sprint:
            sprint_info = f"{selected_sprint.get('name')} ({selected_sprint.get('state')})"

    # Ensure base URL ends with / if not present (though usually it's just the base)
    # But usually jira_base_url is like "https://company.atlassian.net/browse/"
    # If it doesn't end with browse/, we might need to append it or just append the key if it's a full browse URL.
    # Let's assume the config provides "https://company.atlassian.net/browse/" as per default.
    if not jira_base_url.endswith('/'):
        jira_base_url += '/'
    ticket_url = f"{jira_base_url}{ticket_key}"

    print("\n" + "="*60)
    print(f"  TICKET DETAILS: {ticket_key}")
    print("="*60)
    print(f"URL:          {ticket_url}")
    print(f"Summary:      {summary}")
    print(f"Type:         {get_val(get_val(fields, 'issuetype', {}), 'name')}")
    print(f"Status:       {get_colored_ball(status_color)} {status}")
    print(f"Priority:     {priority}")
    print(f"Customer:     {customers}")
    print(f"Health:       {health_status}")
    print(f"Estimation:   {estimation_hours}")
    print(f"Start Date:   {start_date}")
    print(f"Due Date:     {due_date}")
    print(f"Fix Version:  {fix_versions}")
    print(f"Sprint:       {sprint_info}")
    print(f"Assignee:     {assignee}")
    print(f"Reporter:     {reporter}")
    print(f"Created:      {created}")
    print(f"Updated:      {updated}")
    # Format description if it's a rich text object (Jira v3) or string
    description_text = ""
    if isinstance(description, dict):
        def parse_adf(node):
            text = ""
            node_type = node.get('type')
            content = node.get('content', [])
            
            if node_type == 'text':
                text = node.get('text', '')
                # Check for link marks
                for mark in node.get('marks', []):
                    if mark.get('type') == 'link':
                        href = mark.get('attrs', {}).get('href')
                        if href:
                            text = f"{text} ({href})"
                return text
            
            elif node_type == 'paragraph':
                for child in content:
                    text += parse_adf(child)
                text += "\n\n"
            
            elif node_type == 'heading':
                level = node.get('attrs', {}).get('level', 1)
                # Simple markdown-like headers
                prefix = '#' * level + ' '
                for child in content:
                    text += parse_adf(child)
                text = f"\n{prefix}{text}\n"

            elif node_type == 'bulletList':
                for child in content:
                    text += parse_adf(child)
            
            elif node_type == 'orderedList':
                for i, child in enumerate(content, 1):
                    # We need to pass the index down or handle it here. 
                    # For simplicity, let's just treat ordered list items similar to bullet but maybe with a number if we could.
                    # But parse_adf for listItem doesn't take index. Let's just use a generic marker or try to handle it.
                    # Actually, let's just iterate and prepend.
                    item_text = parse_adf(child)
                    # listItem usually adds a newline, so we might need to strip and reformat
                    text += item_text # listItem will handle its own formatting
            
            elif node_type == 'listItem':
                # content of listItem is usually paragraph
                item_content = ""
                for child in content:
                    item_content += parse_adf(child)
                # Indent and bullet
                text += f"  - {item_content.strip()}\n"

            elif node_type == 'hardBreak':
                text += "\n"
            
            elif node_type == 'inlineCard':
                url = node.get('attrs', {}).get('url')
                if url:
                    text += f" {url} "
            
            elif node_type == 'blockCard':
                url = node.get('attrs', {}).get('url')
                if url:
                    text += f"\n{url}\n"

            else:
                # Fallback for other types (doc, etc) - just recurse
                for child in content:
                    text += parse_adf(child)
            
            return text

        try:
            description_text = parse_adf(description)
        except Exception as e:
            description_text = f"Error parsing description: {e}"
    else:
        description_text = str(description)

    print("-" * 60)
    print("Description:")
    print(description_text.strip())
    print("="*60 + "\n")
