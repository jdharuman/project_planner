
import json
import re
from datetime import datetime, timedelta
import unicodedata

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
                if fix_versions:
                    # Assuming we take the releaseDate of the first fix version
                    for version in fix_versions:
                        if version.get('releaseDate'):
                            fix_version_date = datetime.strptime(version['releaseDate'], '%Y-%m-%d')
                            break # Take the first one found

                task_info = {
                    'customer': customer['name'],
                    'packet': packet['name'],
                    'task': task['name'],
                    'start_date': start_date,
                    'due_date': datetime.strptime(task['due_date'], '%Y-%m-%d'),
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
                    'fix_version_date': fix_version_date # Add fix version date
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
            if conflicting_tasks_details:
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
            'fix_version_date': task['fix_version_date'] # Pass fix version date to final schedule
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
    column_names = ['Resource', 'Customer', 'Task', 'Priority', 'Task Status', 'Estimation (Hour)', 'Start Date', 'Due Date', 'Fix Version', 'Schedule Status', 'Conflicts']
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

        fix_version_display_plain = entry['fix_version_date'].strftime('%Y-%m-%d') if entry['fix_version_date'] else "N/A"

        max_col_widths['Resource'] = max(max_col_widths['Resource'], get_display_width(resource_display_name_plain))
        max_col_widths['Customer'] = max(max_col_widths['Customer'], get_display_width(customer_display_name_plain))
        max_col_widths['Task'] = max(max_col_widths['Task'], get_display_width(task_display_name_plain))
        max_col_widths['Priority'] = max(max_col_widths['Priority'], get_display_width(priority_display_plain))
        max_col_widths['Task Status'] = max(max_col_widths['Task Status'], get_display_width(task_status_display_with_ball))
        max_col_widths['Estimation (Hour)'] = max(max_col_widths['Estimation (Hour)'], get_display_width(estimated_hours_display))
        max_col_widths['Start Date'] = max(max_col_widths['Start Date'], get_display_width(entry['start_date'].strftime('%Y-%m-%d') if entry['start_date'] else "N/A"))
        max_col_widths['Fix Version'] = max(max_col_widths['Fix Version'], get_display_width(fix_version_display_plain))
        max_col_widths['Due Date'] = max(max_col_widths['Due Date'], get_display_width(entry['due_date'].strftime('%Y-%m-%d')))
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
        issue_type = entry.get('issue_type', 'Unknown') # Default to 'Unknown' if None
        task_health_status = entry.get('task_health_status', 'Unknown')
        
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

                # Estimation (Hour)
                estimated_hours_display = str(entry['estimated_hours']) if entry['estimated_hours'] is not None else "N/A"
                current_display_width = get_display_width(estimated_hours_display)
                padding = max_col_widths['Estimation (Hour)'] - current_display_width
                row_parts.append(f"{estimated_hours_display}{' ' * padding}")

                # Start Date
                start_date_str = entry['start_date'].strftime('%Y-%m-%d') if entry['start_date'] else "N/A"
                current_display_width = get_display_width(start_date_str)
                padding = max_col_widths['Start Date'] - current_display_width
                row_parts.append(f"{start_date_str}{' ' * padding}")

                # Due Date
                due_date_str = entry['due_date'].strftime('%Y-%m-%d')
                current_display_width = get_display_width(due_date_str)
                padding = max_col_widths['Due Date'] - current_display_width
                row_parts.append(f"{due_date_str}{' ' * padding}")

                # Fix Version
                fix_version_str = entry['fix_version_date'].strftime('%Y-%m-%d') if entry['fix_version_date'] else "N/A"
                current_display_width = get_display_width(fix_version_str)
                padding = max_col_widths['Fix Version'] - current_display_width
                row_parts.append(f"{fix_version_str}{' ' * padding}")

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
