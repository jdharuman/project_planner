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
    args = parser.parse_args()

    # Ensure workspace directory exists
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

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
        planner.print_ps_schedule(RAW_JIRA_ISSUES_JSON_FILE, PLANNER_CONFIG_FILE)
    else:
        # Firmware view logic (default)
        planner.generate_and_print_schedule(
            projects_file=PROJECTS_JSON_FILE,
            raw_issues_file=RAW_JIRA_ISSUES_JSON_FILE,
            config_file=PLANNER_CONFIG_FILE
        )

if __name__ == "__main__":
    main()
