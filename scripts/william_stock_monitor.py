import json
import urllib.request
import urllib.parse
import sys
import os
import time
from datetime import datetime
import ssl

# Configuration
WILLIAM_BOT_TOKEN = "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU"
WILLIAM_CHAT_ID = "8695583357" 
CENTRAL_DATA_FILE = "/Users/bookid/.hermes/data/central_stock_data.json"
CACHE_FILE = "/Users/bookid/.hermes/data/william_stock_last_prices.json"
OPEN_STATE_FILE = "/Users/bookid/.hermes/data/william_day_open_report_sent.json"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{WILLIAM_BOT_TOKEN}/sendMessage"
    ctx = ssl._create_unverified_context()
    payload = {"chat_id": WILLIAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    data = urllib.parse.urlencode(payload).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, context=ctx)
        return True
    except: return False

def main():
    if not os.path.exists(CENTRAL_DATA_FILE): return
    with open(CENTRAL_DATA_FILE, 'r') as f: central_store = json.load(f)
    mapping = central_store.get("full_mapping", {})
    market_data = central_store.get("data", {})
    william_codes = ["8996", "5289", "4966", "3583", "8210", "2327", "5347", "2402", "6510", "3211", "6290", "6669", "6147", "7828", "7815", "7769", "6877", "6683", "3709"]

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    is_opening = now.hour == 9 and 0 <= now.minute <= 10
    
    open_state = {}
    if os.path.exists(OPEN_STATE_FILE):
        with open(OPEN_STATE_FILE, 'r') as f: open_state = json.load(f)

    if is_opening and open_state.get("date") != today_str:
        header = f"🔷 **小智 (William) - 09:00 開盤快報**\n📅 日期：`{today_str}`\n"
        body = ""
        current_prices = {}
        for code in william_codes:
            data = market_data.get(code)
            if data:
                price = data['price']
                prev = data['prev_close']
                open_p = data.get('open', price)
                current_prices[data['symbol']] = price
                pct = ((price - prev) / prev * 100) if prev > 0 else 0
                emoji = "🔴" if price > prev else "🟢"
                name = mapping.get(code, code)
                body += f"{emoji} **{name}**\n   ▸ 價：`{price:,.2f}` | 開：`{open_p:,.2f}` | 昨收：`{prev:,.2f}` | 差：`{pct:+.2f}%`\n"
        if send_telegram(header + body):
            with open(OPEN_STATE_FILE, 'w') as f: json.dump({"date": today_str}, f)
            with open(CACHE_FILE, 'w') as f: json.dump(current_prices, f)
        return

    last_prices = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f: last_prices = json.load(f)
    
    report_lines = []
    current_prices = last_prices.copy()
    for code in william_codes:
        data = market_data.get(code)
        if not data: continue
        sym, price, prev = data['symbol'], data['price'], data['prev_close']
        last_p = last_prices.get(sym, prev)
        
        # Absolute Value Logic: Prev Diff > 3% or Last 20M Diff > 2%
        if abs((price - prev) / prev * 100) >= 3.0 or abs((price - last_p) / last_p * 100) >= 2.0:
            emoji = "🔴" if price > prev else "🟢"
            name = mapping.get(code, code)
            report_lines.append(f"{emoji} **{name}** (`{sym}`) 劇烈變動！\n   ▸ 現價：`{price:,.2f}` (昨收比：`{((price-prev)/prev*100):+.2f}%` | 20M：`{((price-last_p)/last_p*100):+.2f}%`)\n")
            current_prices[sym] = price

    if report_lines:
        send_telegram(f"🔷 **小智 (William) - 波動注意**\n\n" + "".join(report_lines))
        with open(CACHE_FILE, 'w') as f: json.dump(current_prices, f)

if __name__ == "__main__":
    main()
