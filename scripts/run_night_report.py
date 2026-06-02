import subprocess
import sys
import urllib.request
import urllib.parse
import os
import ssl
import pytz
from datetime import datetime

# 📌 系統優化：提高當前進程最大可開啟檔案數 (File Descriptor Limit)，避免 Too many open files 錯誤
try:
    import resource
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    target_limit = min(hard, 245760) if hard != resource.RLIM_INFINITY else 245760
    if soft < target_limit:
        resource.setrlimit(resource.RLIMIT_NOFILE, (target_limit, hard))
except Exception:
    pass

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
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            pass
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
        sys.path.append("/Users/bookid/.hermes/scripts")
        from night_market_gatekeeper import is_night_session_active
        if not is_night_session_active():
            print("Taiwan Night Session is not active (Holiday or out of hours). Skipping.")
            return
    except Exception as e:
        print(f"Direct gatekeeper import failed: {e}. Falling back to subprocess check.")
        try:
            gatekeeper_path = "/Users/bookid/.hermes/scripts/night_market_gatekeeper.py"
            result = subprocess.run([sys.executable, gatekeeper_path], capture_output=True)
            if result.returncode != 0:
                print("Taiwan Night Session is not active (Holiday or out of hours). Skipping.")
                return
        except Exception as sub_e:
            print(f"Gatekeeper error: {sub_e}. Defaulting to skip.")
            return

    # 1. Get Taiwan Futures Update (NQ Futures)
    futures_report = run_script("/Users/bookid/.hermes/scripts/tw_night_session_hourly.py")

    # 2. Get ADRs/Lead Indicators (TSM, NVDA, SYNA, FITXP)
    adri_report = run_script("/Users/bookid/.hermes/scripts/tw_night_monitor_adri.py")
    
    # Merge reports into a single consolidated card with a single master header
    content_parts = []
    if futures_report:
        content_parts.append(futures_report)
    if adri_report:
        content_parts.append(adri_report)
        
    full_msg = ""
    if content_parts:
        taipei_tz = pytz.timezone('Asia/Taipei')
        now = datetime.now(taipei_tz).strftime("%Y-%m-%d %H:%M")
        
        full_msg = (
            f"🌌 **台股夜盤整點監測報告**\n"
            f"⏰ 監測時間：`{now}` (台北時間)\n"
            f"----------------------------\n"
            + "\n\n".join(content_parts) + "\n"
            f"----------------------------\n"
            f"🛡️ 狀態：`Healthy`"
        )

    if full_msg:
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
