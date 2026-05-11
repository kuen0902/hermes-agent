import subprocess
import json
import urllib.request
import sys
import os
from datetime import datetime

# CONFIGURATION
TELEGRAM_BOT_TOKEN = "7953681404:AAEqC90d79ZPlYfE09f7aRbeD1fVd-7Iu7o"
TELEGRAM_CHAT_ID = "1537241249"
CACHE_FILE = os.path.expanduser("~/.hermes/data/stock_last_prices.json")
PORTFOLIO_PATH = os.path.expanduser("~/Documents/StockTracking_Daily.numbers")

def send_telegram_message(message):
    token = TELEGRAM_BOT_TOKEN
    chat_id = TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Simple retry and ignore failures to keep script robust
    for _ in range(2):
        try:
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    return True
        except:
            pass
    return False

def get_holdings():
    # Use AppleScript to read from Numbers.app
    script = f"""
    tell application "Numbers"
        try
            open POSIX file "{PORTFOLIO_PATH}"
            delay 1
            tell document 1 to tell sheet "Portfolio" to tell table 1
                set stockCodes to value of every cell of column 1
                set stockNames to value of every cell of column 2
                return {{stockCodes, stockNames}}
            end tell
        on error
            return ""
        end try
    end tell
    """
    try:
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        if result.returncode == 0:
            raw = result.stdout.strip()
            if not raw: return {}
            # Parsing complex AppleScript list output
            parts = raw.split(", ")
            mid = len(parts) // 2
            codes = [c.strip("'\" ") for c in parts[:mid]]
            names = [n.strip("'\" ") for n in parts[mid:]]
            mapping = {}
            for i in range(len(codes)):
                c = codes[i]
                if not c or c in ["ID", "missing value", "代號"]: continue
                if c.startswith("'"): c = c[1:]
                mapping[c] = names[i] if i < len(names) else ""
            return mapping
        return {}
    except:
        return {}

def fetch_yahoo(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            res_list = data.get('chart', {}).get('result')
            if not res_list: return None
            res = res_list[0]
            meta = res.get('meta', {})
            return {
                'symbol': meta.get('symbol'),
                'shortName': meta.get('shortName', symbol),
                'price': meta.get('regularMarketPrice'),
                'prev_close': meta.get('chartPreviousClose')
            }
    except: return None

def get_stock_data(symbol):
    if "." in symbol: return fetch_yahoo(symbol)
    # Autocompletion for TW stocks
    for suffix in [".TW", ".TWO"]:
        data = fetch_yahoo(symbol + suffix)
        if data and data['price'] is not None: return data
    return fetch_yahoo(symbol)

def load_last_prices():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except: return {}
    return {}

def save_current_prices(prices):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(prices, f)

def main():
    holdings_map = get_holdings()
    codes = list(holdings_map.keys())
    # Fallback list if Numbers is closed or empty
    if not codes: codes = ["2330.TW", "2454.TW", "0050.TW", "0056.TW"]
    codes.sort()

    last_prices = load_last_prices()
    current_prices = {}
    results = []

    for code in codes:
        data = get_stock_data(code)
        if data and data['price'] is not None:
            symbol = data['symbol']
            price = data['price']
            current_prices[symbol] = price
            baseline = data['prev_close']
            
            if baseline is not None:
                diff_prev = price - baseline
                pct_prev = (diff_prev / baseline * 100) if baseline > 0 else 0
                # TAIWAN COLORS: RED UP (🔴), GREEN DOWN (🟢)
                trend_prev = "🔴 ▲" if diff_prev > 0 else "🟢 ▼" if diff_prev < 0 else "⚪ ➡️"

                last_p = last_prices.get(symbol)
                m10_str = ""
                if last_p is not None:
                    diff_10m = price - last_p
                    pct_10m = (diff_10m / last_p * 100) if last_p > 0 else 0
                    trend_10m = "🔺" if diff_10m > 0 else "🔻" if diff_10m < 0 else "➡️"
                    m10_str = f" | 10M: {trend_10m}{diff_10m:+.2f} ({pct_10m:+.2f}%)"

                zh_name = holdings_map.get(code, "")
                en_name = data['short_name'] if 'short_name' in data else data.get('shortName', "")
                display_name = zh_name if zh_name else en_name
                results.append(f"{trend_prev} *{display_name}* (`{symbol}`)\n   現價: *{price}* | 漲跌: *{diff_prev:+.2f}* ({pct_prev:+.2f}%){m10_str}")

    save_current_prices(current_prices)
    curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if results:
        header = f"📊 **持股即時報價**\n🕒 **更新時間**: `{curr_time}`\n*(🔴漲/🟢跌 | 10M: 相較上次)*\n\n"
        full_message = header + "\n\n".join(results)
        
        # SEND TO TELEGRAM (Dedicated Bot: Star Platinum)
        send_telegram_message(full_message)
        
        # OUTPUT HANDLING
        # Silent for main chat during automated runs (unless --verbose is passed)
        if "--verbose" in sys.argv:
            print(full_message)
        # No output in main chat to keep "Golden Experience" clean
    else:
        if "--verbose" in sys.argv:
            print("⚠️ 未能獲取任何持股數據。")

if __name__ == "__main__":
    main()
