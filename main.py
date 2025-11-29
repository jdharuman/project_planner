import os
import sys
from pathlib import Path

# Add the current directory to the Python path to allow importing sibling modules
sys.path.append(str(Path(__file__).parent))

import fetch_jira_issues
import planner

def main():
    # Define paths
    BASE_DIR = Path(__file__).parent
    CONFIG_DIR = BASE_DIR / "config"
    WORKSPACE_DIR = BASE_DIR / ".workspace"

    PLANNER_CONFIG_FILE = CONFIG_DIR / "planner_config.json"
    PROJECTS_JSON_FILE = WORKSPACE_DIR / "projects.json"
    RAW_JIRA_ISSUES_JSON_FILE = WORKSPACE_DIR / "raw_jira_issues.json"

    # Argument parsing
    import argparse
    parser = argparse.ArgumentParser(description="Project Planner CLI")
    parser.add_argument("--ticket", help="View details of a specific ticket")
    parser.add_argument("--firmware", action="store_true", help="Generate Firmware schedule (default)")
    parser.add_argument("--pdm", action="store_true", help="Generate PDM schedule")
    parser.add_argument("--ps", action="store_true", help="Generate Professional Services schedule")
    parser.add_argument("--sprint", action="store_true", help="Generate Sprint schedule")
    parser.add_argument("--status", action="store_true", help="Show last worklog date/time (use with --ps)")
    parser.add_argument("--log", action="store_true", help="Save calendar events to file (--calendar) or log work from file (--ps)")
    parser.add_argument("--calendar", action="store_true", help="Show Google Calendar meetings (filtered by PS customers by default)")
    parser.add_argument("--days", type=int, default=7, help="Number of days for calendar: positive=future (7=next 7 days), negative=past (-7=last 7 days)")
    parser.add_argument("--today", action="store_true", help="Show all events for today (00:00 to 23:59, overrides --days)")
    parser.add_argument("--customer", help="Filter calendar by specific customer(s), comma-separated (e.g., 'Goupil,RASCO')")
    parser.add_argument("--all", action="store_true", dest="show_all", help="Show all calendar events (disable customer filtering)")
    args = parser.parse_args()

    # Ensure workspace directory exists
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

    # Handle calendar view (doesn't need Jira data)
    if args.calendar:
        import fetch_google_calendar
        
        # Determine customer filter
        filter_customers = None
        
        if args.customer:
            # Manual customer filter specified
            filter_customers = [c.strip() for c in args.customer.split(',')]
        elif not args.show_all:
            # Default: filter by PS customers
            ps_jql_file = CONFIG_DIR / "jql_ps_query.txt"
            filter_customers = fetch_google_calendar.extract_customers_from_jql(str(ps_jql_file))
            if filter_customers:
                print(f"Filtering by {len(filter_customers)} PS customers (use --all to show all events)")
        
        # Determine days parameter
        days = 0 if args.today else args.days
        
        events = fetch_google_calendar.fetch_calendar_events(
            days_ahead=days, 
            filter_customers=filter_customers,
            show_full_day=args.today
        )
        fetch_google_calendar.print_calendar_events(events)
        
        # Save events to file if --log is specified
        if args.log:
            import json
            log_file = WORKSPACE_DIR / "calendar_events.json"
            with open(log_file, 'w') as f:
                json.dump(events, f, indent=2)
            print(f"\n✓ Saved {len(events)} events to {log_file}")
        
        # Only return if no other schedule flags are present
        if not (args.ps or args.pdm or args.firmware or args.ticket or args.sprint):
            return

    # Load planner configuration
    CONFIG = planner.load_config(PLANNER_CONFIG_FILE)
    JIRA_URL = CONFIG.get('jira_url')
    
    # Determine JQL query file based on arguments
    if args.pdm:
        JQL_QUERY_FILE = CONFIG.get('jql_pdm_query_file', 'config/jql_pdm_query.txt')
        print("Mode: PDM Schedule")
    elif args.ps:
        JQL_QUERY_FILE = CONFIG.get('jql_ps_query_file', 'config/jql_ps_query.txt')
        print("Mode: Professional Services Schedule")
    elif args.sprint:
        JQL_QUERY_FILE = CONFIG.get('jql_sprint_query_file', 'config/jql_sprint_query.txt')
        print("Mode: Sprint Schedule")
    else:
        # Default to firmware
        JQL_QUERY_FILE = CONFIG.get('jql_firmware_query_file', 'config/jql_firmware_query.txt')
        print("Mode: Firmware Schedule")
    
    # Convert to Path if it's a string
    if isinstance(JQL_QUERY_FILE, str):
        JQL_QUERY_FILE = CONFIG_DIR / JQL_QUERY_FILE.replace('config/', '')

    if not JIRA_URL or not JQL_QUERY_FILE.exists():
        print(f"Error: 'jira_url' not found in config or JQL file {JQL_QUERY_FILE} missing.")
        sys.exit(1)

    # Fetch Jira issues and save them to .workspace
    # Credentials can be passed as arguments or set as environment variables JIRA_EMAIL, JIRA_API_KEY
    fetch_jira_issues.fetch_and_save_jira_issues(
        output_filename=PROJECTS_JSON_FILE,
        raw_issues_debug_filename=RAW_JIRA_ISSUES_JSON_FILE,
        jira_url=JIRA_URL,
        jql_query_file=JQL_QUERY_FILE,
        # jira_email="your_email@example.com", # Uncomment and set if not using env vars
        # jira_api_token="your_api_token" # Uncomment and set if not using env vars
    )

    # Generate and print the schedule using the fetched data
    if args.ticket:
        planner.print_ticket_details(args.ticket, RAW_JIRA_ISSUES_JSON_FILE, PLANNER_CONFIG_FILE)
    elif args.pdm:
        # PDM view logic
        planner.print_pdm_schedule(RAW_JIRA_ISSUES_JSON_FILE, PLANNER_CONFIG_FILE)
    elif args.ps:
        # PS view logic
        if args.log:
            # Log work from calendar events file
            planner.log_work_from_calendar(RAW_JIRA_ISSUES_JSON_FILE, WORKSPACE_DIR / "calendar_events.json", PLANNER_CONFIG_FILE)
        else:
            # Normal PS schedule view
            planner.print_ps_schedule(RAW_JIRA_ISSUES_JSON_FILE, PLANNER_CONFIG_FILE, show_status=args.status)
    elif args.sprint:
        # Sprint view logic
        planner.print_sprint_schedule(RAW_JIRA_ISSUES_JSON_FILE, PLANNER_CONFIG_FILE)
    else:
        # Firmware view logic (default)
        planner.generate_and_print_schedule(
            projects_file=PROJECTS_JSON_FILE,
            raw_issues_file=RAW_JIRA_ISSUES_JSON_FILE,
            config_file=PLANNER_CONFIG_FILE
        )

if __name__ == "__main__":
    main()
