# `planner_config.json` Configuration

This file contains configuration settings for the project planner.

## Fields:

*   **`resource_aliases`**: (Object, optional)
    *   A dictionary mapping full resource names (as found in Jira) to shorter, more readable aliases for display in the planner report.
    *   Example: `{"Jayachandran Dharuman": "Jay"}`

*   **`customer_aliases`**: (Object, optional)
    *   A dictionary mapping full customer names (as found in Jira) to shorter, more readable aliases for display in the planner report.
    *   Example: `{"Aston Martin": "AM"}`

*   **`sort_by`**: (Array of Strings, optional)
    *   A list of fields by which to sort the tasks in the planner report. Tasks will be sorted in the order specified.
    *   Supported fields: `"start_date"`, `"customer"`, `"resource"`.
    *   Default: `["start_date"]`
    *   Example: `["customer", "start_date"]`

*   **`jira_base_url`**: (String, optional)
    *   The base URL for your Jira instance. This is used to construct hyperlinks for Jira issues in the report (though the current version of the script does not generate hyperlinks, this field is kept for future enhancements or external usage).
    *   Default: `"https://company.atlassian.net/browse/"`

*   **`jira_url`**: (String, required)
    *   The base URL for your Jira instance's API. This is used by `fetch_jira_issues.py` to connect to Jira.
    *   Example: `"https://company.atlassian.net"`

*   **`jql_query_file`**: (String, required)
    *   The path to a file containing the JQL (Jira Query Language) query used to fetch issues. This allows for complex JQL queries to be managed in a separate file without needing to escape characters in JSON.
    *   Example: `"config/jql_query.txt"`

*   **`filter`**: (Object, optional)
    *   A section to define various filters to apply to the fetched Jira issues.
    *   **`resource`**: (String, optional)
        *   Filters tasks by the assigned resource. Case-insensitive.
        *   Example: `"Jay"`
    *   **`priority`**: (String, optional)
        *   Filters tasks by priority. Case-insensitive.
        *   Example: `"High"`
    *   **`task_status`**: (String, optional)
        *   Filters tasks by their current status. Case-insensitive.
        *   Example: `"In Progress"`
    *   **`schedule_status`**: (String, optional)
        *   Filters tasks by their schedule status (e.g., "On Track", "At Risk", "Off Track", "Postponed"). Case-insensitive.
        *   Example: `"At Risk"`
    *   **`conflict`**: (Boolean, optional)
        *   If `true`, filters to show only tasks with conflicts. If `false`, shows only tasks without conflicts.
        *   Example: `true`
    *   **`customers`**: (Array of Strings, optional)
        *   Filters tasks by customer names. Tasks belonging to any of the listed customers will be included. Case-insensitive.
        *   Example: `["AML", "BMW"]`
    *   **`from_start_date`**: (String, optional)
        *   Filters tasks that start on or after this date. Format: `YYYY-MM-DD`.
        *   Example: `"2023-01-01"`
    *   **`to_end_date`**: (String, optional)
        *   Filters tasks that end on or before this date. Format: `YYYY-MM-DD`. Note: This now refers to the `fix_version_date`.
        *   Example: `"2023-12-31"`

## Example `planner_config.json`:

```json
{
  "resource_aliases": {
    "Jayachandran Dharuman": "Jay",
  },
  "customer_aliases": {
    "Aston Martin": "AML",
  },
  "sort_by": ["customer", "start_date"],
  "jira_base_url": "https://your-jira-instance.atlassian.net/browse/",
  "jira_url": "https://your-jira-instance.atlassian.net",
  "jql_query_file": "config/jql_query.txt",
  "filter": {
    "resource": "Jay",
    "priority": "High",
    "task_status": "In Progress",
    "schedule_status": "On Track",
    "conflict": false,
    "customers": ["AML"],
    "from_start_date": "2023-01-01",
    "to_end_date": "2023-12-31"
  }
}
```

## `config/jql_query.txt` Example:

```
project = FW AND assignee IN (currentUser()) AND status NOT IN (Done, Closed) ORDER BY created DESC
```

