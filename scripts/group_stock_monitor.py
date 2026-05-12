import json
import urllib.request
import urllib.parse
import sys
import os
import time
from datetime import datetime
import ssl

# Configuration
GROUP_BOT_TOKEN = "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU"
GROUP_CHAT_ID = "-1003744330314" 
CENTRAL_DATA_FILE = "/Users/bookid/.hermes/data/central_stock_data.json"
CACHE_FILE = "/Users/bookid/.hermes/data/group_stock_last_prices.json"
OPEN_STATE_FILE = "/Users/bookid/.hermes/data/day_open_report_sent.json"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{GROUP_BOT_TOKEN}/sendMessage"
    ctx = ssl._create_unverified_context()
    payload = {
        "chat_id": GROUP_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, context=ctx)
        return True
    except Exception as e:
        print(f"Telegram Error: {e}")
        return False

def main():
    if not os.path.exists(CENTRAL_DATA_FILE):
        return

    with open(CENTRAL_DATA_FILE, 'r') as f:
        central_store = json.load(f)
    
    mapping = central_store.get("full_mapping", {})
    market_data = central_store.get("data", {})
    personal_data = central_store.get("personal_data", {})
    categories = {
        "我的核心持股": list(personal_data.keys()),
        "Kim哥推薦組": ["1513", "2049", "5347", "6147", "3709"],
        "正體鍾文字組": ["2408", "2382", "2327"],
        "順風老師組": ["2313", "6285", "5289"],
        "進莫組": ["4543", "6125", "7828"],
        "大盤積分組": ["2330", "2454", "3037"]
    }
    
    # Remove duplicates by moving to personal if they exist there
    personal_keys = set(personal_data.keys())
    for cat in ["Kim哥推薦組", "正體鍾文字組", "順風老師組", "進莫組", "大盤積分組"]:
        categories[cat] = [c for c in categories[cat] if c not in personal_keys]
    
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    
    # 09:00 - 09:10 Opening Report window
    is_opening = now.hour == 9 and 0 <= now.minute <= 10
    
    open_state = {}
    if os.path.exists(OPEN_STATE_FILE):
        with open(OPEN_STATE_FILE, 'r') as f: open_state = json.load(f)
    
    # Opening Report logic
    if is_opening and open_state.get("date") != today_str:
        print("Starting 09:00 Opening Report...")
        header = f"☀️ **09:00 開盤即時戰報**\n📅 日期：`{today_str}`\n"
        body = ""
        current_prices = {}
        for cat, codes in categories.items():
            body += f"\n📌 **{cat}**\n"
            for code in codes:
                data = market_data.get(code)
                if data:
                    sym = data['symbol']
                    price = data['price']
                    prev = data['prev_close']
                    open_p = data.get('open', price)
                    current_prices[sym] = price
                    diff = price - prev
                    pct = (diff / prev * 100) if prev > 0 else 0
                    emoji = "🔴" if diff > 0 else "🟢" if diff < 0 else "⚪"
                    name = mapping.get(code, data.get('name_en', code))
                    body += f"{emoji} **{name}**\n   ▸ 價：`{price:,.2f}` | 開：`{open_p:,.2f}` | 昨收：`{prev:,.2f}` | 差：`{pct:+.2f}%`\n"
        
        if send_telegram(header + body):
            with open(OPEN_STATE_FILE, 'w') as f: json.dump({"date": today_str}, f)
            with open(CACHE_FILE, 'w') as f: json.dump(current_prices, f)
        return

    # Normal monitoring with Filter (Gap > 3% from Prev or > 2% from Last)
    last_prices = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f: last_prices = json.load(f)
    
    report_lines = []
    current_prices = last_prices.copy()
    
    for code in [c for codes in categories.values() for c in codes]:
        data = market_data.get(code)
        if not data: continue
        sym = data['symbol']
        price = data['price']
        prev = data['prev_close']
        last_p = last_prices.get(sym, prev)
        
        # Filter Logic
        pct_from_prev = abs((price - prev) / prev * 100) if prev > 0 else 0
        pct_from_last = abs((price - last_p) / last_p * 100) if last_p > 0 else 0
        
        if pct_from_prev >= 3.0 or pct_from_last >= 2.0:
            emoji = "🔴" if price > prev else "🟢" if price < prev else "⚪"
            name = mapping.get(code, data.get('name_en', code))
            trend = "🚀" if price > last_p else "📉"
            line = f"{emoji}{trend} **{name}** (`{sym}`)\n   ▸ 現價：`{price:,.2f}` (昨收比: `{((price-prev)/prev*100):+.2f}%` | 20M比: `{((price-last_p)/last_p*100):+.2f}%`)\n"
            report_lines.append(line)
            current_prices[sym] = price

    if report_lines:
        print(f"Found {len(report_lines)} reportable changes.")
        ts = now.strftime("%H:%M")
        header = f"⚡ **盤中劇烈變動追蹤 ({ts})**\n💡 *條件：與昨收差>3% 或 與20分前差>2%*\n\n"
        send_telegram(header + "".join(report_lines))
        with open(CACHE_FILE, 'w') as f: json.dump(current_prices, f)

if __name__ == "__main__":
    main()
