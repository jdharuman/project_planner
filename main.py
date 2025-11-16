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

    # Ensure workspace directory exists
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

    # Load planner configuration
    CONFIG = planner.load_config(PLANNER_CONFIG_FILE)
    JIRA_URL = CONFIG.get('jira_url')
    JQL_QUERY_FILE = CONFIG.get('jql_query_file')

    if not JIRA_URL or not JQL_QUERY_FILE:
        print("Error: 'jira_url' or 'jql_query_file' not found in planner_config.json.")
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
    planner.generate_and_print_schedule(
        projects_file=PROJECTS_JSON_FILE,
        raw_issues_file=RAW_JIRA_ISSUES_JSON_FILE,
        config_file=PLANNER_CONFIG_FILE
    )

if __name__ == "__main__":
    main()
