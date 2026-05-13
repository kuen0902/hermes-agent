import json
import urllib.request
import urllib.parse
import sys
import os
import time
from datetime import datetime
import ssl

# Configuration
BOT_TOKEN = "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU" # MONITOR BOT (STAR PLATINUM)
CHAT_ID = "6326497055"
CENTRAL_DATA_FILE = "/Users/bookid/.hermes/data/central_stock_data.json"
CACHE_FILE = "/Users/bookid/.hermes/data/user_stock_last_prices.json"
OPEN_STATE_FILE = "/Users/bookid/.hermes/data/user_day_open_report_sent.json"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    ctx = ssl._create_unverified_context()
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    data = urllib.parse.urlencode(payload).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data)
        # 增加 timeout=10 防止因網路抖動造成的無限期卡死
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            return response.status == 200
    except Exception as e:
        print(f"Telegram Sending Error: {e}")
        return False

def main():
    if not os.path.exists(CENTRAL_DATA_FILE): return
    with open(CENTRAL_DATA_FILE, 'r') as f: central_store = json.load(f)
    
    mapping = central_store.get("full_mapping", {})
    market_data = central_store.get("data", {})
    personal_data = central_store.get("personal_data", {})
    # Core Holdings from central data (Numbers sync)
    user_portfolio = list(personal_data.keys())
    
    if not user_portfolio:
        # Fallback to legacy if central sync is empty
        user_portfolio = ["2454", "3037", "2330"] 

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    is_opening = now.hour == 9 and 0 <= now.minute <= 10
    
    open_state = {}
    if os.path.exists(OPEN_STATE_FILE):
        with open(OPEN_STATE_FILE, 'r') as f: open_state = json.load(f)

    # Opening Report logic
    if is_opening and open_state.get("date") != today_str:
        header = f"🎖️ **黃金體驗 - 09:00 開盤決報**\n📅 日期：`{today_str}`\n"
        body = ""
        current_prices = {}
        for code in user_portfolio:
            data = market_data.get(code)
            if data:
                price = data['price']
                prev = data['prev_close']
                open_p = data.get('open', price)
                current_prices[data['symbol']] = price
                pct = ((price - prev) / prev * 100) if prev > 0 else 0
                emoji = "🔴" if price > prev else "🟢"
                name = mapping.get(code, code)
                body += f"{emoji} **{name}** (`{data['symbol']}`)\n   ▸ 價：`{price:,.2f}` | 開：`{open_p:,.2f}` | 昨收：`{prev:,.2f}` | 差：`{pct:+.2f}%`\n"
        if send_telegram(header + body):
            with open(OPEN_STATE_FILE, 'w') as f: json.dump({"date": today_str}, f)
            with open(CACHE_FILE, 'w') as f: json.dump(current_prices, f)
        return

    last_prices = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f: last_prices = json.load(f)
    
    report_lines = []
    current_prices = last_prices.copy()
    print(f"Checking {len(user_portfolio)} core stocks for Star Platinum...")
    for code in user_portfolio:
        data = market_data.get(code)
        if not data: continue
        sym, price, prev = data['symbol'], data['price'], data['prev_close']
        last_p = last_prices.get(sym, prev)
        
        # Filter Logic: >3% from Prev or >2% from Last 20M
        pct_from_prev = abs((price - prev) / prev * 100) if prev > 0 else 0
        pct_from_last = abs((price - last_p) / last_p * 100) if last_p > 0 else 0
        
        if pct_from_prev >= 3.0 or pct_from_last >= 2.0:
            # 只有當價格跟前次紀錄不同時，才顯示「較前次」變動幅度
            change_str = f" (較前次：`{((price-last_p)/last_p*100):+.2f}%`)" if price != last_p else ""
            emoji = "🔴" if price > prev else "🟢"
            name = mapping.get(code, code)
            report_lines.append(f"{emoji} **{name}** (`{code}`)\n   ▸ 現價：`{price:,.2f}` | 昨收比：`{((price-prev)/prev*100):+.2f}%`{change_str}\n")
            current_prices[sym] = price

    if report_lines:
        print(f"Found {len(report_lines)} reportable changes for Star Platinum.")
        # 精簡專業格式：[時間] 標題
        ts = now.strftime("%H:%M")
        header = f"⚖️ **白金之星 - 精密波動警戒 ({ts})**\n\n"
        send_telegram(header + "".join(report_lines))
        with open(CACHE_FILE, 'w') as f: json.dump(current_prices, f)

if __name__ == "__main__":
    main()
