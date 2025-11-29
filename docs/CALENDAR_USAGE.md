# Calendar Usage Guide - Updated with Past Events Support

## Overview

The Google Calendar integration now supports both **past and future events** with automatic pagination to fetch all events (no 100-event limit).

## Days Parameter

The `--days` parameter accepts **positive or negative values**:

### Positive Values (Future Events)
```bash
--days 1    # Today only (from now until end of today)
--days 7    # Next 7 days (today through 7 days from now)
--days 30   # Next 30 days
```

### Negative Values (Past Events)
```bash
--days -1   # Yesterday only (start of yesterday until now)
--days -7   # Last 7 days (7 days ago until now)
--days -30  # Last 30 days
```

### Invalid Values
```bash
--days 0    # ERROR: Cannot be 0
```

## Complete Usage Examples

### Future Events

```bash
# Today's remaining events (PS customers only)
task_planner --calendar --days 1

# Next 7 days (PS customers only - default)
task_planner --calendar

# Next 14 days, all events
task_planner --calendar --days 14 --all

# Next 30 days for specific customers
task_planner --calendar --days 30 --customer "Goupil,RASCO"
```

### Past Events

```bash
# Yesterday's events (PS customers only)
task_planner --calendar --days -1

# Last 7 days (PS customers only)
task_planner --calendar --days -7

# Last 30 days, all events
task_planner --calendar --days -30 --all

# Last 14 days for specific customers
task_planner --calendar --days -14 --customer "Aston Martin,KTM"
```

## Event Pagination

The system now automatically fetches **ALL events** using pagination:
- No longer limited to 100 events
- Fetches in batches of 250
- Continues until all events are retrieved
- Shows total count: `Found X events from Google Calendar`

### Example Output

```bash
$ task_planner --calendar --days -7 --all
Fetching calendar events for the last 7 days (all events)...
Found 49 events from Google Calendar

========================================================================================================================
GOOGLE CALENDAR - UPCOMING MEETINGS
========================================================================================================================
...
Total meetings: 49
```

## Filtering Examples

### PS Customers (Default Behavior)
```bash
# Last 7 days of PS customer meetings
$ task_planner --calendar --days -7
Filtering by 14 PS customers (use --all to show all events)
Fetching calendar events for the last 7 days (filtered for 14 customers)...
Found 49 events from Google Calendar
...
Total meetings: 12  # Filtered results
```

### All Events
```bash
# Last 30 days, ALL calendar events
$ task_planner --calendar --days -30 --all
Fetching calendar events for the last 30 days (all events)...
Found 156 events from Google Calendar
...
Total meetings: 156
```

### Specific Customers
```bash
# Next 14 days for Goupil and RASCO
$ task_planner --calendar --days 14 --customer "Goupil,RASCO"
Fetching calendar events for the next 14 days (filtered for 2 customers)...
Found 78 events from Google Calendar
...
Total meetings: 8
```

## Common Use Cases

### Review Past Week's Customer Meetings
```bash
task_planner --calendar --days -7
```

### Plan Next Month
```bash
task_planner --calendar --days 30
```

### Check Yesterday's Meetings
```bash
task_planner --calendar --days -1 --all
```

### Audit Past Month for Specific Customer
```bash
task_planner --calendar --days -30 --customer "Aston Martin"
```

## Tips

✅ **Large Date Ranges**: The system handles large ranges (e.g., --days 365 or --days -365)
✅ **No Event Limit**: Automatically paginates to fetch all events
✅ **Smart Filtering**: Apply customer filters to narrow down results
✅ **Fast Queries**: Uses local timezone for accurate day calculations
