# Google Calendar Integration

## Setup

1. **Install required packages:**
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Set up Google OAuth credentials:**
   
   You need to create OAuth 2.0 credentials in Google Cloud Console:
   
   a. Go to [Google Cloud Console](https://console.cloud.google.com/)
   b. Create a new project or select an existing one
   c. Enable the Google Calendar API
   d. Go to "Credentials" → "Create Credentials" → "OAuth client ID"
   e. Choose "Desktop app" as the application type
   f. Download the credentials or copy the Client ID and Client Secret
   
3. **Set environment variables:**
   ```bash
   export GOOGLE_CLIENT_ID="your_client_id_here"
   export GOOGLE_CLIENT_SECRET="your_client_secret_here"
   ```

4. **First-time authentication:**
   
   The first time you run the calendar command, it will open a browser window for you to authorize access to your Google Calendar. After authorization, the token will be saved to `.workspace/google_calendar_token.json` for future use.

## Usage

### View upcoming calendar events (next 7 days)
```bash
task_planner --calendar
```

### View calendar events for a specific number of days
```bash
task_planner --calendar --days 14
```

## Output Format

The calendar view displays:
- Meeting Title
- Date (YYYY-MM-DD)
- Start Time (HH:MM)
- End Time (HH:MM)
- Number of Attendees

## Configuration

Edit `config/calendar_config.json` to customize:
- `calendar_id`: Which calendar to fetch from (default: "primary")
- `days_ahead`: Default number of days to look ahead
- `show_attendees`: Whether to show attendee count
- `show_location`: Whether to show meeting location
