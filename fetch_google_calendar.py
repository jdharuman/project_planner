#!/usr/bin/env python3

import os
import json
import re
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def extract_customers_from_jql(jql_file_path):
    """
    Extract customer names from a JQL query file.
    Parses the 'customers[select list (multiple choices)]' IN clause.
    
    Args:
        jql_file_path: Path to JQL query file
    
    Returns:
        List of customer names
    """
    try:
        with open(jql_file_path, 'r') as f:
            jql_content = f.read()
        
        # Look for the customers IN clause
        # Pattern: "customers[...]" IN ("Customer1", Customer2, "Customer3")
        pattern = r'"customers\[select list \(multiple choices\)\]"\s+IN\s+\((.*?)\)(?:\s+AND|\s+ORDER|$)'
        match = re.search(pattern, jql_content, re.IGNORECASE | re.DOTALL)
        
        if not match:
            return []
        
        customers_str = match.group(1)
        
        # Use a smarter approach: split by comma, but respect quoted strings
        customers = []
        current = ""
        in_quotes = False
        
        for char in customers_str:
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                # End of current customer
                customer = current.strip().strip('"').strip()
                if customer and customer.upper() not in ['AND', 'OR', 'IN', 'NOT']:
                    customers.append(customer)
                current = ""
            else:
                current += char
        
        # Don't forget the last one
        customer = current.strip().strip('"').strip()
        if customer and customer.upper() not in ['AND', 'OR', 'IN', 'NOT']:
            customers.append(customer)
        
        return customers
        
    except FileNotFoundError:
        print(f"Warning: JQL file not found: {jql_file_path}")
        return []
    except Exception as e:
        print(f"Warning: Error parsing JQL file: {e}")
        return []

def load_customer_filters(config_file='config/planner_config.json'):
    """
    Load customer meeting filters from config file.
    Returns a dict mapping customer names to their filter patterns.
    """
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            return config.get('customer_meeting_filters', {})
    except FileNotFoundError:
        return {}

def matches_customer(title, customer_patterns):
    """
    Check if meeting title matches any of the customer patterns.
    
    Args:
        title: Meeting title to check
        customer_patterns: List of patterns/keywords to match
    
    Returns:
        bool: True if title matches any pattern
    """
    title_lower = title.lower()
    for pattern in customer_patterns:
        # Try as regex first, then as simple substring
        try:
            if re.search(pattern, title, re.IGNORECASE):
                return True
        except re.error:
            # If regex fails, use simple substring match
            if pattern.lower() in title_lower:
                return True
    return False

def get_calendar_credentials():
    """
    Retrieves or creates Google Calendar API credentials.
    Uses GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET from environment variables.
    """
    creds = None
    token_file = '.workspace/google_calendar_token.json'
    
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Get client ID and secret from environment variables
            client_id = os.getenv('GOOGLE_CLIENT_ID')
            client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
            
            if not client_id or not client_secret:
                raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables must be set")
            
            # Create client config from environment variables
            client_config = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uris": ["http://localhost"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            }
            
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    
    return creds

def fetch_calendar_events(days_ahead=7, calendar_id='primary', filter_customers=None, show_full_day=False):
    """
    Fetches Google Calendar events for the specified number of days.
    
    Args:
        days_ahead: Number of calendar days to fetch events for (default: 7)
                   Positive: future events (--days 7 = next 7 days from today)
                   Negative: past events (--days -7 = last 7 days until today)
                   --days 1 = today only (from now until end of today)
                   --days -1 = yesterday only (start of yesterday until now)
        calendar_id: Calendar ID to fetch from (default: 'primary')
        filter_customers: List of customer names to filter by (optional)
        show_full_day: If True, show full day (00:00 to 23:59) regardless of current time
    
    Returns:
        List of event dictionaries with title, date, start_time, end_time
    """
    try:
        creds = get_calendar_credentials()
        service = build('calendar', 'v3', credentials=creds)
        
        # Get current time in local timezone
        local_tz = datetime.now().astimezone().tzinfo
        now_local = datetime.now(local_tz)
        
        if show_full_day:
            # Full day: from start of today (00:00) to end of today (23:59)
            today_date = now_local.date()
            start_datetime = datetime.combine(today_date, datetime.min.time()).replace(tzinfo=local_tz)
            end_datetime = datetime.combine(today_date, datetime.max.time()).replace(tzinfo=local_tz)
            time_min = start_datetime.isoformat()
            time_max = end_datetime.isoformat()
            direction = "today (full day)"
        elif days_ahead > 0:
            # Future events: from now until end of Nth day
            time_min = now_local.isoformat()
            end_date = now_local.date() + timedelta(days=days_ahead - 1)
            end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=local_tz)
            time_max = end_datetime.isoformat()
            direction = "next"
        elif days_ahead < 0:
            # Past events: show full calendar days
            # --days -1 = yesterday (full day)
            # --days -2 = day before yesterday (full day)
            # --days -N = show last N days as full calendar days (not including today)
            abs_days = abs(days_ahead)
            
            # Start from N days ago at 00:00
            start_date = now_local.date() - timedelta(days=abs_days)
            start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=local_tz)
            
            # End at yesterday 23:59:59 (not including today)
            end_date = now_local.date() - timedelta(days=1)
            end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=local_tz)
            
            time_min = start_datetime.isoformat()
            time_max = end_datetime.isoformat()
            direction = "last"
        else:
            # days_ahead == 0, no events
            print("Invalid: --days cannot be 0")
            return []
        
        if filter_customers:
            if show_full_day:
                print(f'Fetching calendar events for {direction} (filtered for {len(filter_customers)} customers)...')
            else:
                print(f'Fetching calendar events for the {direction} {abs(days_ahead)} days (filtered for {len(filter_customers)} customers)...')
        else:
            if show_full_day:
                print(f'Fetching calendar events for {direction} (all events)...')
            else:
                print(f'Fetching calendar events for the {direction} {abs(days_ahead)} days (all events)...')
        
        # Fetch all events with pagination
        all_events = []
        page_token = None
        
        while True:
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=250,  # Increased from 100
                singleEvents=True,
                orderBy='startTime',
                pageToken=page_token
            ).execute()
            
            events = events_result.get('items', [])
            all_events.extend(events)
            
            page_token = events_result.get('nextPageToken')
            if not page_token:
                break
        
        if not all_events:
            print('No events found.')
            return []
        
        print(f'Found {len(all_events)} events from Google Calendar')
        
        # Load customer filters
        customer_filters = load_customer_filters()
        
        # Transform events to desired format
        formatted_events = []
        for event in all_events:
            title = event.get('summary', 'No Title')
            
            # Apply customer filter if specified
            if filter_customers:
                matched = False
                for customer in filter_customers:
                    # Get patterns for this customer, use customer name as fallback
                    patterns = customer_filters.get(customer, [customer])
                    if matches_customer(title, patterns):
                        matched = True
                        break
                if not matched:
                    continue
            
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            # Parse datetime
            if 'T' in start:  # DateTime format
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                
                formatted_events.append({
                    'title': title,
                    'date': start_dt.strftime('%Y-%m-%d'),
                    'start_time': start_dt.strftime('%H:%M'),
                    'end_time': end_dt.strftime('%H:%M'),
                    'location': event.get('location', 'N/A'),
                    'attendees': len(event.get('attendees', [])),
                })
            else:  # All-day event
                formatted_events.append({
                    'title': title,
                    'date': start,
                    'start_time': 'All Day',
                    'end_time': 'All Day',
                    'location': event.get('location', 'N/A'),
                    'attendees': len(event.get('attendees', [])),
                })
        
        return formatted_events
        
    except HttpError as error:
        print(f'An error occurred: {error}')
        return []

def print_calendar_events(events):
    """
    Prints calendar events in a formatted table.
    
    Args:
        events: List of event dictionaries
    """
    if not events:
        print("No events to display.")
        return
    
    print("\n" + "=" * 120)
    print("GOOGLE CALENDAR - UPCOMING MEETINGS")
    print("=" * 120)
    print(f"{'Meeting Title':<50} | {'Date':<12} | {'Start':<8} | {'End':<8} | {'Attendees':<10}")
    print("-" * 120)
    
    for event in events:
        title = event['title']
        if len(title) > 47:
            title = title[:44] + "..."
        
        print(f"{title:<50} | {event['date']:<12} | {event['start_time']:<8} | {event['end_time']:<8} | {event['attendees']:<10}")
    
    print("-" * 120)
    print(f"\nTotal meetings: {len(events)}")
    print("\n")

if __name__ == '__main__':
    # Test extracting customers from PS JQL
    customers = extract_customers_from_jql('config/jql_ps_query.txt')
    print(f"Found {len(customers)} customers in PS JQL:")
    for customer in customers:
        print(f"  - {customer}")
    
    # Test fetching events
    events = fetch_calendar_events(days_ahead=7, filter_customers=customers)
    print_calendar_events(events)
