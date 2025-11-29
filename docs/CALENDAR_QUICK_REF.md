# Quick Calendar Reference

## Most Common Commands

### Today's Schedule
```bash
# PS customer meetings only (default)
task_planner --calendar --today

# All meetings today
task_planner --calendar --today --all

# Specific customers today
task_planner --calendar --today --customer "Goupil,REE"
```

### Future Events
```bash
# Next 7 days (default, PS customers)
task_planner --calendar

# Next 14 days, all events
task_planner --calendar --days 14 --all

# Tomorrow only
task_planner --calendar --days 1
```

### Past Events
```bash
# Yesterday
task_planner --calendar --days -1

# Last 7 days
task_planner --calendar --days -7 --all

# Last 30 days for specific customer
task_planner --calendar --days -30 --customer "Aston Martin"
```

## Key Differences

| Command | Time Range | Use Case |
|---------|------------|----------|
| `--today` | 00:00 → 23:59 today | Full day schedule (past + future) |
| `--days 1` | NOW → 23:59 today | Remaining events today |
| `--days -1` | 00:00 yesterday → NOW | Yesterday's events |

## Filtering

By default, **only PS customers** are shown. Use flags to change:

```bash
--all              # Show ALL calendar events
--customer "X,Y"   # Show specific customers only
```

## Examples

```bash
# What did I have with REE today?
task_planner --calendar --today --customer "REE"

# What's my schedule for rest of today?
task_planner --calendar --days 1 --all

# Review last week's customer meetings
task_planner --calendar --days -7

# Plan next 2 weeks
task_planner --calendar --days 14
```
