import json
import urllib.request
import urllib.parse
import sys
import os
import time
from datetime import datetime
import ssl

# Profile Configurations
PROFILES = {
    "personal": {
        "token": "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU", # Star Platinum
        "chat_id": "6326497055",
        "cache_file": "/Users/bookid/.hermes/data/user_stock_last_prices.json",
        "open_file": "/Users/bookid/.hermes/data/user_day_open_report_sent.json",
        "header_open": "🎖️ **黃金體驗 - 09:00 開盤決報**",
        "header_alert": "⚖️ **白金之星 - 精密階梯波動警戒**",
    },
    "william": {
        "token": "8678817340:AAHLd6ObYqUUTfygY-fPf57Rw6SfOO2WEGQ", # William Bot
        "chat_id": "8695583357",
        "cache_file": "/Users/bookid/.hermes/data/william_stock_last_prices.json",
        "open_file": "/Users/bookid/.hermes/data/william_day_open_report_sent.json",
        "header_open": "🔷 **小智 (William) - 09:00 開盤快報**",
        "header_alert": "🔷 **小智 (William) - 階梯波動注意**",
    },
    "group": {
        "token": "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU", # Star Platinum
        "chat_id": "-1003744330314",
        "cache_file": "/Users/bookid/.hermes/data/group_stock_last_prices.json",
        "open_file": "/Users/bookid/.hermes/data/day_open_report_sent.json",
        "header_open": "☀️ **09:00 開盤即時戰報**",
        "header_alert": "⚡ **盤中階梯變動追蹤**",
    }
}

CENTRAL_DATA_FILE = "/Users/bookid/.hermes/data/central_stock_data.json"
TIERS = [3.0, 5.0, 7.0, 9.0]

def get_current_tier(pct: float) -> int:
    """Returns the highest tier the pct has crossed."""
    abs_pct = abs(pct)
    crossed = 0
    for t in TIERS:
        if abs_pct >= t:
            crossed = int(t)
    return crossed * (1 if pct >= 0 else -1)

def send_telegram(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    ctx = ssl._create_unverified_context()
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    data = urllib.parse.urlencode(payload).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            return response.status == 200
    except Exception as e:
        print(f"Telegram Error: {e}")
        return False

def get_target_stocks(profile_name, central_store):
    personal_data = central_store.get("personal_data", {})
    if profile_name == "personal":
        keys = list(personal_data.keys())
        return {"核心持股": keys} if keys else {"核心持股": ["2454", "3037", "2330"]}
    elif profile_name == "william":
        return {"William觀察名單": ["8996", "5289", "4966", "3583", "8210", "2327", "5347", "2402", "6510", "3211", "6290", "6669", "6147", "7828", "7815", "7769", "6877", "6683", "3709"]}
    elif profile_name == "group":
        categories = {
            "我的核心持股": list(personal_data.keys()),
            "Kim哥推薦組": ["1513", "2049", "5347", "6147", "3709"],
            "正體鍾文字組": ["2408", "2382", "2327"],
            "順風老師組": ["2313", "6285", "5289"],
            "進莫組": ["4543", "6125", "7828"],
            "大盤積分組": ["2330", "2454", "3037"]
        }
        personal_keys = set(personal_data.keys())
        for cat in ["Kim哥推薦組", "正體鍾文字組", "順風老師組", "進莫組", "大盤積分組"]:
            categories[cat] = [c for c in categories[cat] if c not in personal_keys]
        return categories
    return {}

def run(profile_name: str, capture_only=False):
    if profile_name not in PROFILES:
        print(f"Invalid profile: {profile_name}")
        return
        
    cfg = PROFILES[profile_name]
    if not os.path.exists(CENTRAL_DATA_FILE): return
    with open(CENTRAL_DATA_FILE, 'r') as f: central_store = json.load(f)
    
    mapping = central_store.get("full_mapping", {})
    market_data = central_store.get("data", {})
    target_categories = get_target_stocks(profile_name, central_store)
    
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    is_opening = now.hour == 9 and 0 <= now.minute <= 10
    
    # 1. OPENING REPORT LOGIC
    open_state = {}
    if os.path.exists(cfg["open_file"]):
        with open(cfg["open_file"], 'r') as f: open_state = json.load(f)
        
    if is_opening and open_state.get("date") != today_str:
        header = f"{cfg['header_open']}\n📅 日期：`{today_str}`\n"
        body = ""
        current_cache = {}
        for cat, codes in target_categories.items():
            if profile_name == "group": body += f"\n📌 **{cat}**\n"
            for code in codes:
                data = market_data.get(code)
                if not data: continue
                price, prev = data['price'], data['prev_close']
                open_p = data.get('open', price)
                pct = ((price - prev) / prev * 100) if prev > 0 else 0
                
                # Initialize tier in cache
                current_cache[data['symbol']] = {"price": price, "tier": get_current_tier(pct)}
                
                emoji = "🔴" if price > prev else "🟢" if price < prev else "⚪"
                name = mapping.get(code, data.get('name_en', code))
                body += f"{emoji} **{name}**\n   ▸ 價：`{price:,.2f}` | 開：`{open_p:,.2f}` | 昨收：`{prev:,.2f}` | 差：`{pct:+.2f}%`\n"
                
        if not capture_only:
            if send_telegram(cfg["token"], cfg["chat_id"], header + body):
                with open(cfg["open_file"], 'w') as f: json.dump({"date": today_str}, f)
                with open(cfg["cache_file"], 'w') as f: json.dump(current_cache, f)
        else:
            print(header + body)
        return

    # 2. TIERED MILESTONE MONITORING
    last_cache = {}
    if os.path.exists(cfg["cache_file"]):
        with open(cfg["cache_file"], 'r') as f: last_cache = json.load(f)
        
    # Migrate legacy float dictionary to new dict with {"price", "tier"}
    for k, v in last_cache.items():
        if isinstance(v, float) or isinstance(v, int):
            last_cache[k] = {"price": v, "tier": 0}
            
    report_lines = []
    current_cache = last_cache.copy()
    
    for codes in target_categories.values():
        for code in codes:
            data = market_data.get(code)
            if not data: continue
            sym, price, prev = data['symbol'], data['price'], data['prev_close']
            
            cached = last_cache.get(sym, {"price": prev, "tier": 0})
            last_tier = cached.get("tier", 0)
            
            pct = ((price - prev) / prev * 100) if prev > 0 else 0
            current_tier = get_current_tier(pct)
            
            # If the stock has crossed into a NEW tier (e.g. from 0 -> 3, or 3 -> 5)
            if current_tier != 0 and current_tier != last_tier:
                emoji = "🔴" if pct > 0 else "🟢"
                trend = "🚀" if abs(current_tier) > abs(last_tier) else "📉"
                name = mapping.get(code, data.get('name_en', code))
                
                line = f"{emoji}{trend} **{name}** (`{sym}`)\n   ▸ 現價：`{price:,.2f}` | 昨收比：`{pct:+.2f}%` (突破 `{current_tier}%` 門檻)\n"
                report_lines.append(line)
                
            # Update cache ALWAYS with current price and current evaluated tier
            current_cache[sym] = {"price": price, "tier": current_tier}

    if report_lines:
        ts = now.strftime("%H:%M")
        header = f"{cfg['header_alert']} ({ts})\n💡 *條件：跨越 ±3%, ±5%, ±7%, ±9% 絕對里程碑*\n\n"
        report_content = header + "".join(report_lines)
        if not capture_only:
            send_telegram(cfg["token"], cfg["chat_id"], report_content)
            with open(cfg["cache_file"], 'w') as f: json.dump(current_cache, f)
        else:
            print(report_content)
    else:
        if capture_only:
            print("[SILENT]")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, choices=PROFILES.keys())
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    run(args.profile, args.report_only)
