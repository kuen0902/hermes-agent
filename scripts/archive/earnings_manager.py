import os
import json
import subprocess
from datetime import datetime, date

# Configuration
STORAGE_DIR = os.path.expanduser("~/Documents/Reports/Earnings_Tracker")
CALENDAR_FILE = os.path.expanduser("~/.hermes/data/earnings_calendar.json")
REPORT_DIR = os.path.expanduser("~/Documents/Reports/2026_Q1")
STOCKS = ["2330", "2454", "3037", "2382", "2313", "1513", "2002", "2049", "2327", "2395", "2413", "3260", "3709", "5347"]

def ensure_dirs():
    os.makedirs(STORAGE_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(CALENDAR_FILE), exist_ok=True)

def load_calendar():
    if os.path.exists(CALENDAR_FILE):
        try:
            with open(CALENDAR_FILE, 'r') as f:
                return json.load(f)
        except: return {}
    return {}

def save_calendar(data):
    with open(CALENDAR_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def log_event(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

# Note: This function will be called during the Sunday run to refresh dates
def update_dates_prompt():
    # This is a placeholder since the agent will handle the web searching
    # and provide the data via terminal or session context.
    pass

def check_and_download_past(calendar):
    """Identifies stocks whose earnings were announced on or before yesterday but reports haven't been downloaded."""
    today = date.today()
    to_download = []
    
    for symbol, info in calendar.items():
        event_date_str = info.get("next_report_date")
        if not event_date_str: continue
        
        try:
            event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
        except: continue
        
        downloaded = info.get("downloaded_q1", False)
        
        # Condition: Announcement was at least 1 day ago (event_date < today)
        if event_date < today and not downloaded:
            to_download.append(symbol)
            
    return to_download

if __name__ == "__main__":
    ensure_dirs()
    # Main logic will be orchestrated by the Hermes Agent tool calls
