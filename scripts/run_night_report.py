import subprocess
import sys
import urllib.request
import urllib.parse
import os
import ssl
import pytz
from datetime import datetime

# Configuration
BOT_TOKEN = "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU"
# TARGET_CHATS: [Group only]
TARGET_CHATS = ["-1003744330314"] 
# SILENCED: -1003744330314 (高潮不斷) 

def send_telegram(message, chat_id):
    # Disable SSL verification
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, context=ctx, timeout=10)
        return True
    except Exception as e:
        print(f"Telegram Error: {e}")
        return False

def run_script(path):
    try:
        result = subprocess.run([sys.executable, path], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else ""
    except:
        return ""

def main():
    # 0. Gatekeeper: Ensure Taiwan Night Session is active
    try:
        gatekeeper_path = "/Users/bookid/.hermes/scripts/night_market_gatekeeper.py"
        result = subprocess.run([sys.executable, gatekeeper_path], capture_output=True)
        if result.returncode != 0:
            print("Taiwan Night Session is not active (Holiday or out of hours). Skipping.")
            return
    except Exception as e:
        print(f"Gatekeeper error: {e}. Defaulting to skip.")
        return

    # 1. Get ADRs/Lead Indicators
    adri_report = run_script("/Users/bookid/.hermes/scripts/tw_night_monitor_adri.py")
    
    # 2. Get Taiwan Futures Update
    futures_report = run_script("/Users/bookid/.hermes/scripts/tw_night_session_hourly.py")
    
    # Merge reports if at least one successful
    full_msg = ""
    if adri_report and futures_report:
        full_msg = adri_report + "\n\n" + futures_report
    else:
        full_msg = adri_report or futures_report

    if full_msg:
        # Add final status if not present (only if everything is healthy)
        if "健康檢查" not in full_msg:
            full_msg += "\n✅ 狀態：Healthy"
        
        print(f"DEBUG: Sending message:\n{full_msg}")
        # Send
        for cid in TARGET_CHATS:
            success = send_telegram(full_msg, cid)
            if success:
                print(f"Successfully sent combined night session report to {cid}.")
            else:
                print(f"Failed to send report to {cid}.")
    else:
        print("Failed to generate any report content.")

if __name__ == "__main__":
    main()
