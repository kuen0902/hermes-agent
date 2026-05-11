import subprocess
import urllib.request
import urllib.parse
import ssl
import os

# Configuration (Replace with actual values)
BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    data = urllib.parse.urlencode(payload).encode("utf-8")
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10, context=ctx)
        return True
    except:
        return False

def run_script(path):
    try:
        result = subprocess.run(['python3', path], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else ""
    except:
        return ""

def main():
    # Indicators (Relative or absolute paths)
    adri = run_script("tw_night_monitor_adri.py")
    futures = run_script("tw_night_session_hourly.py")
    
    if adri and futures:
        # Merge into a single "War Room" update
        send_telegram(f"{adri}\n\n{futures}")
    elif adri or futures:
        send_telegram(adri or futures)

if __name__ == "__main__":
    main()
