import os
import json
import subprocess
from datetime import datetime, timedelta

# Configuration
BASE_DIR = os.path.expanduser("~/Documents/Reports/2026_Q1")
CALENDAR_FILE = os.path.expanduser("~/.hermes/data/earnings_calendar.json")

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
    
    to_check = []
    for symbol, info in calendar.items():
        report_date = info.get("next_report_date")
        if report_date and report_date <= today:
            if not info.get("downloaded_q1"):
                to_check.append((symbol, info.get("name", symbol)))
    
    if to_check:
        print(f"REPORT_READY: {json.dumps(to_check)}")
    else:
        print("Everything up to date.")

if __name__ == "__main__":
    run_daily_download()
