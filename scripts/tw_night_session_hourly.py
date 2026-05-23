import requests
import random
import time
from datetime import datetime, timedelta
import pytz
import os
import json

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


def get_bridge_data(key):
    try:
        bridge_path = "/Users/bookid/.hermes/data/market_prices_bridge.json"
        if os.path.exists(bridge_path):
            with open(bridge_path, 'r') as f:
                data = json.load(f)
                return data.get(key)
    except:
        return None

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
                timestamps = result.get("timestamp", [])
                closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
                opens = result.get("indicators", {}).get("quote", [{}])[0].get("open", [])
                
                records = []
                for t, c, o in zip(timestamps, closes, opens):
                    if c is not None and o is not None:
                        records.append({"timestamp": t, "close": float(c), "open": float(o)})
                if records:
                    return records
            elif r.status_code == 429:
                pass
        except Exception as e:
            pass
            
        if attempt < max_retries - 1:
            time.sleep(base_delay * (2 ** attempt) + random.uniform(0.1, 0.5))
            
    return None

def get_night_session_status():
    ticker_symbol = "NQ=F"
    taipei_tz = pytz.timezone('Asia/Taipei')
    report_time = datetime.now(taipei_tz).strftime("%Y-%m-%d %H:%M")
    
    records = fetch_yahoo_minute_data(ticker_symbol)

    CACHE_FILE = "/Users/bookid/.hermes/data/night_session_nq_cache.json"
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
        except:
            pass

    if records is None or not records:
        # --- BRIDGE FALLBACK ---
        current_price = get_bridge_data("NQ")
        if current_price:
            open_price = cache.get("open_price")
            prev_hour_price = cache.get("last_price")
            
            def get_color_emoji(val):
                if val > 0.05: return "🔴"
                if val < -0.05: return "🟢"
                return "⚪️"
                
            if open_price and prev_hour_price:
                session_change = current_price - open_price
                session_pct = (session_change / open_price) * 100
                hour_change = current_price - prev_hour_price
                hour_pct = (hour_change / prev_hour_price) * 100
                
                msg = [
                    f"🌌 **台股夜盤指標 (Nasdaq Futures)**",
                    f"⏰ 檢測時間：`{report_time}`",
                    f"----------------------------",
                    f"💰 **目前點數 (NQ)**：`{current_price:,.1f}`",
                    f"",
                    f"📊 **近期走勢 (Hourly)** [Cache]",
                    f"{get_color_emoji(hour_change)} 漲跌：`{hour_change:+.1f}` ({hour_pct:+.2f}%)",
                    f"",
                    f"📈 **全日變動 (vs NY Open)** [Cache]",
                    f"{get_color_emoji(session_change)} 漲跌：`{session_change:+.1f}` ({session_pct:+.2f}%)",
                    f"----------------------------",
                    f"📊 **狀態**：`PROXIED (Resilient Bridge)`"
                ]
                
                cache["last_price"] = current_price
                with open(CACHE_FILE, 'w') as f:
                    json.dump(cache, f)
                    
                return "\n".join(msg)
            else:
                msg = [
                    f"🌌 **台股夜盤指標 (Nasdaq Futures)**",
                    f"⏰ 檢測時間：`{report_time}`",
                    f"----------------------------",
                    f"💰 **目前點數 (NQ)**：`{current_price:,.1f}`",
                    f"📊 **狀態**：`PROXIED (Resilient Bridge)`",
                    f"----------------------------"
                ]
                return "\n".join(msg)
        return "❌ [Health Check ERROR]: 無法獲取 NQ=F 數據。"

    # Normal Flow
    current_price = records[-1]["close"]
    open_price = records[0]["open"]
    last_timestamp = records[-1]["timestamp"]
    
    prev_hour_records = [r for r in records if r["timestamp"] <= last_timestamp - 3600]
    prev_hour_price = prev_hour_records[-1]["close"] if prev_hour_records else open_price
    
    session_change = current_price - open_price
    session_pct = (session_change / open_price) * 100
    hour_change = current_price - prev_hour_price
    hour_pct = (hour_change / prev_hour_price) * 100

    def get_color_emoji(val):
        if val > 0.05: return "🔴"
        if val < -0.05: return "🟢"
        return "⚪️"

    msg = [
        f"🌌 **台股夜盤指標 (Nasdaq Futures)**",
        f"⏰ 檢測時間：`{report_time}`",
        f"----------------------------",
        f"💰 **目前點數 (NQ)**：`{current_price:,.1f}`",
        f"",
        f"📊 **近期走勢 (Hourly)**",
        f"{get_color_emoji(hour_change)} 漲跌：`{hour_change:+.1f}` ({hour_pct:+.2f}%)",
        f"",
        f"📈 **全日變動 (vs NY Open)**",
        f"{get_color_emoji(session_change)} 漲跌：`{session_change:+.1f}` ({session_pct:+.2f}%)",
        f"----------------------------"
    ]
    
    cache["open_price"] = float(open_price)
    cache["last_price"] = float(current_price)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

    return "\n".join(msg)


if __name__ == "__main__":
    print(get_night_session_status())
