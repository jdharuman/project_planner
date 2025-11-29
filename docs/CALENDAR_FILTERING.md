# Calendar Customer Filtering - Updated Behavior

## Overview

The Google Calendar integration now **automatically filters by Professional Services (PS) customers** by default. Customer names are dynamically extracted from the PS JQL query file, and only aliases need to be configured in `planner_config.json`.

## Default Behavior

When you run `--calendar`, it will:
1. **Automatically extract** customer names from `config/jql_ps_query.txt`
2. **Filter meetings** to show only those matching PS customers
3. **Use aliases** from `customer_meeting_filters` for fuzzy matching

## Configuration

### Minimal Configuration Required

Only add entries to `customer_meeting_filters` for customers whose **meeting titles differ from their JQL names**:

```json
"customer_meeting_filters": {
  "JCB UK": ["JCB", "JCU-01"],
  "Goupil": ["GPL-01", "Goupil"],
  "Aston Martin": ["AML", "Aston Martin"],
  "Noam (Segula)": ["Segula", "Noam", "Convergence"],
  ...
}
```

### How It Works

1. **Customer Names**: Extracted from `config/jql_ps_query.txt`:
   ```
   "customers[...]" IN ("JCB UK", Goupil, REE, RASCO, ...)
   ```

2. **Aliases**: If a customer name exists in `customer_meeting_filters`, those patterns are used for matching. Otherwise, the customer name itself is used.

3. **Matching**: Uses regex and substring matching (case-insensitive)

## Usage

### Show PS customer meetings (default)
```bash
task_planner --calendar                    # Next 7 days, PS customers only
task_planner --calendar --days 14          # Next 14 days, PS customers only
```

### Show ALL calendar events
```bash
task_planner --calendar --all              # Disable customer filtering
task_planner --calendar --days 30 --all    # Next 30 days, all events
```

### Filter by specific customers
```bash
task_planner --calendar --customer "Goupil,RASCO"
task_planner --calendar --days 14 --customer "Aston Martin"
```

## Examples

### Default PS Filtering
```bash
$ task_planner --calendar --days 7
Filtering by 14 PS customers (use --all to show all events)
Fetching calendar events for the next 7 days (filtered for 14 customers)...

Meeting Title                                      | Date         | Start    | End      | Attendees 
------------------------------------------------------------------------------------------------------------------------
Goupil <> Sibros | Weekly Project Alignment        | 2025-12-02   | 10:30    | 11:00    | 5  
RASCO <> Sibros - Weekly Sync                      | 2025-12-03   | 10:30    | 11:00    | 9
REE <> Sibros | Weekly                             | 2025-12-04   | 11:00    | 12:00    | 11
------------------------------------------------------------------------------------------------------------------------
Total meetings: 3
```

### Show All Events
```bash
$ task_planner --calendar --days 1 --all
Fetching calendar events for the next 1 days (all events)...

Meeting Title                                      | Date         | Start    | End      | Attendees 
------------------------------------------------------------------------------------------------------------------------
Lunch                                              | 2025-11-27   | All Day  | All Day  | 0
Morning routine slots                              | 2025-11-27   | 08:30    | 09:30    | 0
Goupil <> Sibros | Weekly Project Alignment        | 2025-11-27   | 10:30    | 11:00    | 5
Personal Meeting                                   | 2025-11-27   | 14:00    | 15:00    | 2
------------------------------------------------------------------------------------------------------------------------
Total meetings: 4
```

## Adding Customer Aliases

If a customer's meeting titles don't match their JQL name:

1. **Check the Pattern**: Look at your calendar for that customer's meetings
2. **Add Alias**: Edit `config/planner_config.json`:
   ```json
   "customer_meeting_filters": {
     "Customer Name from JQL": ["Pattern1", "Pattern2", "Alias"]
   }
   ```
3. **Test**: Run `task_planner --calendar --customer "Customer Name from JQL"`

### Example: Noam (Segula)

The JQL has `"Noam (Segula)"` but meetings may contain:
- "Segula" → "Réunion Convergence Sybros-Segula"
- "Noam" → "[Noam] Project Meeting"
- "Convergence" → "Convergence Weekly Sync"

Configuration:
```json
"Noam (Segula)": ["Segula", "Noam", "Convergence"]
```

## Benefits

✅ **Automatic**: No need to manually list all customers
✅ **Synchronized**: Always matches your PS JQL query
✅ **Flexible**: Add aliases only when needed
✅ **Simple**: `--all` flag for unfiltered view
✅ **Efficient**: Only configure exceptions, not defaults
