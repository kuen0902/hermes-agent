import os
import json
import urllib.request
import urllib.parse
import ssl
import subprocess
import sys
from datetime import datetime
import pytz
import yfinance as yf

# Configuration
DATA_DIR = os.path.expanduser("~/.hermes/data")
STATE_FILE = os.path.join(DATA_DIR, "night_threshold_state.json")
BOT_TOKEN = "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU"
# TARGET_CHATS: [Jojo, Group]
TARGET_CHATS = ["6326497055", "-1003744330314"] 

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
        urllib.request.urlopen(req, context=ctx, timeout=10)
        return True
    except Exception as e:
        print(f"Telegram Error: {e}")
        return False

def load_state():
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

def get_tier(pct_change):
    abs_pct = abs(pct_change)
    crossed_tiers = [t for t in THRESHOLDS if abs_pct >= t]
    if not crossed_tiers:
        return None
    return max(crossed_tiers)

def main():
    if not check_gatekeeper():
        print("Night market is closed. Exiting.")
        return

    session_key = get_current_session_key()
    state = load_state()
    
    # Reset state if it's a new session
    if state.get("session") != session_key:
        state = {"session": session_key, "alerts": {}}

    alerts_triggered = False

    for symbol, name in SYMBOLS.items():
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d", interval="1m")
            if data.empty:
                continue
                
            current_price = data['Close'].iloc[-1]
            open_price = data['Open'].iloc[0]
            
            pct_change = ((current_price - open_price) / open_price) * 100
            tier = get_tier(pct_change)
            
            if tier is not None:
                # Check if this tier has already been alerted for this symbol in this direction
                direction = "UP" if pct_change > 0 else "DOWN"
                alert_key = f"{symbol}_{tier}_{direction}"
                
                if alert_key not in state["alerts"]:
                    # New threshold crossed!
                    emoji = "🚨" if direction == "DOWN" else "🚀"
                    direction_str = "暴跌" if direction == "DOWN" else "狂飆"
                    
                    msg = (
                        f"{emoji} **夜盤緊急通報：{name} {direction_str}突破 {tier}%！**\n\n"
                        f"📊 **目前點數/價格**：`{current_price:,.2f}`\n"
                        f"📈 **開盤至今變動**：`{current_price - open_price:+.2f}` ({pct_change:+.2f}%)\n"
                        f"⚠️ **警報層級**：`Tier {THRESHOLDS.index(tier) + 1}`"
                    )
                    
                    print(msg)
                    
                    for cid in TARGET_CHATS:
                        send_telegram(msg, cid)
                        
                    # Record the alert
                    state["alerts"][alert_key] = datetime.now().isoformat()
                    alerts_triggered = True
                    
        except Exception as e:
            print(f"Error checking {symbol}: {e}")

    if alerts_triggered:
        save_state(state)

if __name__ == "__main__":
    main()
