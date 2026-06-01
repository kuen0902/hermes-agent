import os
import json
import urllib.request
import urllib.parse
import ssl
import subprocess
import sys
from datetime import datetime
import pytz
import requests
import random
import time
from typing import Dict, Any


# 📌 系統優化：提高當前進程最大可開啟檔案數 (File Descriptor Limit)，避免 Too many open files 錯誤
try:
    import resource
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    target_limit = min(hard, 245760) if hard != resource.RLIM_INFINITY else 245760
    if soft < target_limit:
        resource.setrlimit(resource.RLIMIT_NOFILE, (target_limit, hard))
except Exception:
    pass

# 📌 全域 Session 重用，維持 Keep-Alive 以節省 TCP Socket 開銷
http_session = requests.Session()


def fetch_yahoo_minute_data(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
    params = {
        "range": "1d",
        "interval": "1m",
        "includePrePost": "true"
    }
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0"
    ]
    max_retries = 3
    base_delay = 1.0
    
    for attempt in range(max_retries):
        headers = {'User-Agent': random.choice(user_agents)}
        try:
            r = http_session.get(url, params=params, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                result = data["chart"]["result"][0]
                meta = result.get("meta", {})
                
                # Try to get previousClose from meta
                previous_close = meta.get("previousClose")
                if previous_close is None:
                    previous_close = meta.get("chartPreviousClose")
                
                timestamps = result.get("timestamp", [])
                closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
                opens = result.get("indicators", {}).get("quote", [{}])[0].get("open", [])
                
                records = []
                for t, c, o in zip(timestamps, closes, opens):
                    if c is not None and o is not None:
                        records.append({"timestamp": t, "close": float(c), "open": float(o)})
                if records:
                    return {
                        "records": records,
                        "previous_close": float(previous_close) if previous_close is not None else None,
                        "current_price": float(records[-1]["close"]),
                        "last_timestamp": int(records[-1]["timestamp"]),
                        "open_price": float(records[0]["open"])
                    }
            elif r.status_code == 429:
                pass
        except Exception as e:
            pass
            
        if attempt < max_retries - 1:
            time.sleep(base_delay * (2 ** attempt) + random.uniform(0.1, 0.5))
            
    return None


# Configuration
DATA_DIR = os.path.expanduser("~/.hermes/data")
STATE_FILE = os.path.join(DATA_DIR, "night_threshold_state.json")
BOT_TOKEN = "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU"
# TARGET_CHATS: [Group only]
TARGET_CHATS = ["-1003744330314"] 
# SILENCED: -1003744330314 (高潮不斷) 依據用戶指令恢復

THRESHOLDS = [1.5, 3.0, 5.0]

SYMBOLS = {
    "NQ=F": "小那斯達克期貨 (NQ)",
    "TSM": "台積電 ADR (TSM)"
}

def send_telegram(message, chat_id):
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

def load_state() -> Dict[str, Any]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_state(state):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def check_gatekeeper():
    try:
        gatekeeper_path = "/Users/bookid/.hermes/scripts/night_market_gatekeeper.py"
        result = subprocess.run([sys.executable, gatekeeper_path], capture_output=True)
        if result.returncode != 0:
            return False
        return True
    except:
        return False

def get_current_session_key():
    # Define session by date (if before 15:00, it belongs to previous day's session)
    taipei_tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(taipei_tz)
    
    if now.hour < 15:
        # Before 15:00, belongs to yesterday's night session
        # Example: 02:00 AM belongs to the night session starting at 15:00 yesterday
        from datetime import timedelta
        session_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        # After 15:00, belongs to today's night session
        session_date = now.strftime("%Y-%m-%d")
        
    return session_date

def get_current_tier(pct_change, last_tier=0.0):
    abs_pct = abs(pct_change)
    abs_last = abs(last_tier)
    direction = 1.0 if pct_change >= 0 else -1.0
    
    # Hysteresis buffer
    BUFFER = 0.3
    
    # If direction reversed, we start over from 0 (ignore last tier)
    if last_tier != 0.0 and (pct_change * last_tier < 0):
        abs_last = 0.0

    if abs_last == 0.0:
        # Standard threshold crossing from 0
        crossed = 0.0
        for t in THRESHOLDS:
            if abs_pct >= t:
                crossed = t
        return crossed * direction
    else:
        # We are moving in the same direction from a non-zero tier.
        # 1. Check if we scale UP to a higher tier
        higher_thresholds = [t for t in THRESHOLDS if t > abs_last]
        for t in higher_thresholds:
            if abs_pct >= t:
                return t * direction
                
        # 2. Check if we drop below the current tier.
        # To stay in the current tier, the price must remain >= abs_last - BUFFER
        if abs_pct >= (abs_last - BUFFER):
            return abs_last * (1.0 if last_tier >= 0 else -1.0)
            
        # 3. If we dropped below, find the highest lower tier we still satisfy with buffer
        lower_thresholds = [t for t in THRESHOLDS if t < abs_last]
        crossed = 0.0
        for t in sorted(lower_thresholds):
            if abs_pct >= (t - BUFFER):
                crossed = t
        return crossed * (1.0 if last_tier >= 0 else -1.0)

def main():
    if not check_gatekeeper():
        print("Night market is closed. Exiting.")
        return

    taipei_tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(taipei_tz)
    
    # Calculate current session start time in Taipei timezone
    if now.hour < 15:
        from datetime import timedelta
        session_start = now.replace(hour=15, minute=0, second=0, microsecond=0) - timedelta(days=1)
    else:
        session_start = now.replace(hour=15, minute=0, second=0, microsecond=0)
        
    session_start_timestamp = session_start.timestamp()
    session_key = session_start.strftime("%Y-%m-%d")

    state: Dict[str, Any] = load_state()
    
    # Reset state if it's a new session
    if state.get("session") != session_key:
        state = {"session": session_key, "alerts": {}}

    for symbol, name in SYMBOLS.items():
        try:
            data = fetch_yahoo_minute_data(symbol)
            if not data:
                continue
                
            last_timestamp = data["last_timestamp"]
            
            # Skip if the latest trade was before the current session started (stale data)
            if last_timestamp < session_start_timestamp:
                print(f"[{symbol}] Stale data (last trade: {datetime.fromtimestamp(last_timestamp, taipei_tz)}), session start: {session_start}. Skipping.")
                continue
                
            current_price = data["current_price"]
            
            # Use previousClose if available, otherwise fall back to first record's open
            ref_price = data["previous_close"]
            if ref_price is None or ref_price <= 0:
                ref_price = data["open_price"]
                ref_source = "open_price"
            else:
                ref_source = "previous_close"
                
            pct_change = ((current_price - ref_price) / ref_price) * 100
            
            # Load last tier from state alerts (default 0.0)
            last_tier = state["alerts"].get(symbol, 0.0)
            
            current_tier = get_current_tier(pct_change, last_tier)
            
            # Only trigger if crossed a NEW tier (and not 0.0)
            if current_tier != 0.0 and current_tier != last_tier:
                # Enforce cool-down rate limit of 15 minutes (900 seconds)
                last_alert_time_str = state["alerts"].get(f"{symbol}_last_time")
                if last_alert_time_str:
                    try:
                        last_alert_time = datetime.fromisoformat(last_alert_time_str)
                        if (now - last_alert_time).total_seconds() < 900:
                            print(f"[{symbol}] Cool-down active. Skipping alert to prevent spam.")
                            continue
                    except Exception as e:
                        print(f"[{symbol}] Error parsing last alert time: {e}")
                
                direction = "UP" if current_tier > 0 else "DOWN"
                direction_str = "暴跌" if direction == "DOWN" else "狂飆"
                
                # Check trend: escalation vs recovery
                is_escalation = abs(current_tier) > abs(last_tier)
                trend_str = "突破" if is_escalation else "自癒收斂至"
                
                # Severity emojis
                if direction == "DOWN":
                    emoji = "🚨" if is_escalation else "🟢"
                else:
                    emoji = "🚀" if is_escalation else "🔴"
                
                # Format tier display value
                tier_val = abs(current_tier)
                
                msg = (
                    f"{emoji} **夜盤緊急通報：{name} {direction_str}{trend_str} {tier_val}%！**\n\n"
                    f"📊 **目前點數/價格**：`{current_price:,.2f}`\n"
                    f"📈 **變動幅度**：`{current_price - ref_price:+.2f}` ({pct_change:+.2f}%) [基準: {ref_source}]\n"
                    f"⚠️ **警報層級**：`Tier {THRESHOLDS.index(tier_val) + 1}`"
                )
                
                print(msg)
                
                for cid in TARGET_CHATS:
                    send_telegram(msg, cid)
                    
                # Update the alert state with the new active tier and timestamp
                state["alerts"][symbol] = current_tier
                state["alerts"][f"{symbol}_last_time"] = now.isoformat()
                
        except Exception as e:
            print(f"Error checking {symbol}: {e}")

    # Always save state to persist the session key and prevent state-reset loop
    save_state(state)

if __name__ == "__main__":
    main()
