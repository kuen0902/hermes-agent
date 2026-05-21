import os
import json
import subprocess
from datetime import datetime, timedelta

# Configuration
BASE_DIR = os.path.expanduser("~/Documents/Reports/2026_Q1")
CALENDAR_FILE = os.path.expanduser("~/.hermes/data/earnings_calendar.json")
PORTFOLIO = ["0050", "0052", "00965", "00981A", "1513", "2002", "2049", "2313", "2327", "2330", "2382", "2395", "2413", "2454", "3037", "3260", "3709", "5347"]

def load_calendar():
    if os.path.exists(CALENDAR_FILE):
        with open(CALENDAR_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_calendar(data):
    os.makedirs(os.path.dirname(CALENDAR_FILE), exist_ok=True)
    with open(CALENDAR_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def run_daily_download():
    calendar = load_calendar()
    today = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(BASE_DIR, exist_ok=True)
    
    # Identify stocks that should have released reports today or recently but aren't downloaded
    to_check = []
    for symbol, info in calendar.items():
        report_date = info.get("next_report_date")
        if report_date and report_date <= today:
            if not info.get("downloaded_q1"):
                to_check.append((symbol, info.get("name", symbol)))
    
    if not to_check:
        print("Today: No reports scheduled for download.")
        return

    # For the agent to handle: This script will output the list of stocks to download
    # Then the agent will use web_search to find the actual PDF links.
    print(f"TRIGGER_DOWNLOAD: {json.dumps(to_check)}")

def run_weekly_scan():
    # This will be called on Sunday to set up the plan for the week.
    print("TRIGGER_WEEKLY_SCAN: True")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "scan": run_weekly_scan()
        elif sys.argv[1] == "download": run_daily_download()
    else:
        run_daily_download()
