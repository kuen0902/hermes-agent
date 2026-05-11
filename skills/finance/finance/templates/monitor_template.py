import json
import urllib.request
import urllib.parse
import sys
import os
import time
from datetime import datetime

# --- CONFIGURATION (Change these) ---
BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID" # Get this via getUpdates
CACHE_FILE = os.path.expanduser("~/.hermes/data/stock_cache.json")
LOCK_FILE = os.path.expanduser("~/.hermes/data/stock.lock")
# STOCK_MAPPING = {"2330": "台積電", "AAPL": "Apple"}
STOCK_MAPPING = {} 
STOCK_LIST = list(STOCK_MAPPING.keys())

def check_lock(timeout=120):
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'r') as f:
                last_run = float(f.read().strip())
                if time.time() - last_run < timeout:
                    return False
        except: pass
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    with open(LOCK_FILE, 'w') as f:
        f.write(str(time.time()))
    return True

def send_telegram(message):
    if not CHAT_ID or CHAT_ID == "PENDING":
        print("CHAT_ID not set.")
        return
    if not check_lock(): return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"Error: {e}")

def fetch_yahoo(symbol):
    # Auto-append .TW/.TWO if missing
    if "." not in symbol:
        for suffix in [".TW", ".TWO"]:
            d = fetch_yahoo_raw(symbol + suffix)
            if d and d['price'] is not None: return d
    return fetch_yahoo_raw(symbol)

def fetch_yahoo_raw(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            res = data.get('chart', {}).get('result')[0]
            meta = res.get('meta', {})
            return {
                'symbol': meta.get('symbol'),
                'shortName': meta.get('shortName', symbol),
                'price': meta.get('regularMarketPrice'),
                'prev_close': meta.get('chartPreviousClose')
            }
    except: return None

def main():
    last_prices = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f: last_prices = json.load(f)

    current_prices = {}
    results = []
    
    for code in STOCK_LIST:
        data = fetch_yahoo(code)
        if data and data['price'] is not None:
            sym = data['symbol']
            price = data['price']
            prev = data['prev_close']
            current_prices[sym] = price
            
            diff = price - (prev or price)
            pct = (diff / prev * 100) if prev and prev > 0 else 0
            # Taiwan Style: Red Up, Green Down
            trend = "🔴" if diff > 0 else "🟢" if diff < 0 else "⚪"
            
            last_p = last_prices.get(sym)
            m10_str = ""
            if last_p is not None:
                d10 = price - last_p
                p10 = (d10 / last_p * 100) if last_p > 0 else 0
                t10 = "🔴 ▲" if d10 > 0 else "🟢 ▼" if d10 < 0 else "⚪ ➡️"
                m10_str = f" | 10M: {t10} {d10:+.2f} ({p10:+.2f}%)"
            
            zh_name = STOCK_MAPPING.get(code, "")
            display_name = f"{zh_name} {data['shortName']}" if zh_name else data['shortName']
            results.append(f"{trend} *{display_name}* (`{sym}`)\n   現價: *{price}* | 漲跌: *{diff:+.2f}* ({pct:+.2f}%){m10_str}")

    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w') as f: json.dump(current_prices, f)

    if results:
        curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"📊 **Stock Update**\n🕒 **Time**: `{curr_time}`\n\n"
        send_telegram(header + "\n\n".join(results))

if __name__ == "__main__":
    main()
