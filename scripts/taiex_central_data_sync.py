import subprocess
import json
import os
import time
from datetime import datetime
import requests
import pandas as pd
import urllib3
import yfinance as yf
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    })
    return session

# Configuration
NUMBERS_PATH = "/Users/bookid/Documents/StockTracking_Daily.numbers"
CACHE_FILE = "/Users/bookid/.hermes/data/central_stock_data.json"
HISTORY_LOG_FILE = "/Users/bookid/.hermes/data/intraday_data_log.csv"

def get_personal_tickers():
    """Fetches Ticker, Name, Qty, and Avg Cost from Numbers 'Portfolio' sheet."""
    portfolio = {}
    script = """
    set output to ""
    tell application "Numbers"
        set targetDoc to missing value
        set allDocs to name of every document
        repeat with d in allDocs
            if d starts with "StockTracking" then
                set targetDoc to d
                exit repeat
            end if
        end repeat
        
        if targetDoc is not missing value then
            tell document targetDoc to tell sheet "Portfolio" to tell table 1
                set rowCount to row count
                repeat with i from 2 to rowCount
                    set code to value of cell 1 of row i
                    if code is not missing value and code is not "" then
                        try
                            set nameVal to value of cell 2 of row i
                            set qtyVal to value of cell 3 of row i
                            set avgVal to value of cell 5 of row i
                            if nameVal is missing value then set nameVal to ""
                            if qtyVal is missing value then set qtyVal to 0
                            if avgVal is missing value then set avgVal to 0
                            set output to output & code & tab & nameVal & tab & qtyVal & tab & avgVal & linefeed
                        end try
                    end if
                end repeat
            end tell
        end if
    end tell
    return output
    """
    try:
        process_check = subprocess.run(['pgrep', 'Numbers'], capture_output=True)
        if process_check.returncode != 0:
            print("Numbers is not running. Attempting to open...")
            subprocess.run(['open', NUMBERS_PATH])
            time.sleep(5)

        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                parts = line.split('\t')
                if len(parts) >= 4:
                    c = parts[0].strip().strip("'")
                    if "." in c and c.split(".")[-1] == "0": c = c.split(".")[0]
                    portfolio[c] = {
                        "name": parts[1].strip(),
                        "qty": float(parts[2]) if parts[2] != "missing value" and parts[2].strip() else 0,
                        "avg": float(parts[3]) if parts[3] != "missing value" and parts[3].strip() else 0
                    }
    except Exception as e:
        print(f"Numbers Fetch Error: {e}")
    return portfolio

def log_to_csv(data, codes_mapping):
    """Logs intraday data to a persistent CSV for reference."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_exists = os.path.exists(HISTORY_LOG_FILE)
    os.makedirs(os.path.dirname(HISTORY_LOG_FILE), exist_ok=True)
    with open(HISTORY_LOG_FILE, 'a') as f:
        if not file_exists:
            f.write("timestamp,code,name,price,volume,pct_change\n")
        for code, info in data.items():
            name = codes_mapping.get(code, "Unknown")
            f.write(f"{now},{code},{name},{info['price']},{info['volume']},{info['pct']:.4f}\n")

def fetch_twse_data(codes):
    """Fetches real-time data from TWSE/OTC API."""
    results = {}
    session = get_session()
    ex_ch_list = []
    for code in codes:
        ex_ch_list.append(f"tse_{code}.tw")
        ex_ch_list.append(f"otc_{code}.tw")
    
    chunk_size = 50
    for i in range(0, len(ex_ch_list), chunk_size):
        chunk = ex_ch_list[i:i + chunk_size]
        query = "|".join(chunk)
        url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={query}&json=1&delay=0"
        try:
            resp = session.get(url, timeout=15, verify=False)
            data = resp.json()
            if 'msgArray' in data:
                for item in data['msgArray']:
                    code = item['c']
                    price_str = item.get('z', '-')
                    if price_str == '-': price_str = item.get('pz', '-')
                    if price_str == '-': price_str = item.get('o', '-')
                    try:
                        price = float(price_str)
                    except:
                        continue
                    yclose = float(item.get('y', price))
                    volume = int(item.get('v', 0))
                    res = {
                        "symbol": f"{code}.TW" if item['ex'] == 'tse' else f"{code}.TWO",
                        "price": price,
                        "volume": volume,
                        "prev_close": yclose,
                        "change": price - yclose,
                        "pct": (price - yclose) / yclose * 100 if yclose else 0,
                        "time": datetime.now().isoformat()
                    }
                    if code not in results:
                        results[code] = res
            time.sleep(2)
        except Exception as e:
            print(f"API Fetch Error: {e}")
    return results

def fetch_yfinance_fallback(codes):
    """Fetches data via yfinance for tickers that failed TWSE API."""
    results = {}
    if not codes: return results
    for c in codes:
        for suffix in [".TW", ".TWO"]:
            sym = f"{c}{suffix}"
            try:
                t = yf.Ticker(sym)
                info = t.info
                price = info.get('currentPrice') or info.get('regularMarketPrice')
                prev = info.get('previousClose')
                if price and prev:
                    results[c] = {
                        "symbol": sym,
                        "price": float(price),
                        "volume": int(info.get('volume', 0)),
                        "prev_close": float(prev),
                        "change": float(price - prev),
                        "pct": float((price - prev) / prev * 100),
                        "time": datetime.now().isoformat()
                    }
                    break
            except:
                continue
    return results

def sync():
    print("Starting Central Stock Data Sync (TWSE API + YF Fallback)...")
    personal_data = get_personal_tickers()
    william_defaults = {
        "8996": "高力", "5289": "宜鼎", "4966": "譜瑞", "3583": "辛耘", 
        "8210": "勤誠", "2327": "國巨", "5347": "世界", "2402": "毅嘉", 
        "6510": "精測", "3211": "順達", "6290": "良維", "6669": "緯穎", 
        "6147": "頎邦", "7828": "諾貝兒", "7815": "家登自動", "7769": "進能服", 
        "6877": "鏵友益", "6683": "雍智科技", "3709": "鑫聯大"
    }
    group_defaults = {
        "1513": "中興電", "2049": "上銀", "5347": "世界", "6147": "頎邦", "3709": "鑫聯大",
        "2408": "南亞科", "2382": "廣達", "2327": "國巨",
        "2313": "華通", "6285": "啟碁", "5289": "宜鼎",
        "4543": "萬在",
        "2330": "台積電", "2454": "聯發科", "3037": "欣興"
    }
    all_codes = set(personal_data.keys()) | set(william_defaults.keys()) | set(group_defaults.keys())
    mapping = {**william_defaults, **group_defaults}
    for code, info in personal_data.items():
        if code not in mapping: mapping[code] = info['name']

    print(f"Tracking {len(all_codes)} unique stocks.")
    market_data = fetch_twse_data(list(all_codes))
    
    failed_codes = [c for c in all_codes if c not in market_data]
    if failed_codes:
        print(f"Attempting YFinance fallback for: {failed_codes}")
        fallback_data = fetch_yfinance_fallback(failed_codes)
        market_data.update(fallback_data)

    for code in all_codes:
        if code in market_data:
            res = market_data[code]
            print(f"Done: {code} -> {res['price']} ({res['pct']:+.2f}%)")
        else:
            print(f"Failed: {code}")

    log_to_csv(market_data, mapping)
    healthy_count = len(market_data)
    status = "Healthy" if healthy_count > len(all_codes) * 0.8 else "Degraded"
    output = {
        "metadata": {
            "last_sync": datetime.now().isoformat(),
            "status": status,
            "total_requested": len(all_codes),
            "total_fetched": healthy_count
        },
        "personal_data": personal_data,
        "william_codes": list(william_defaults.keys()),
        "group_codes": list(group_defaults.keys()),
        "full_mapping": mapping,
        "data": market_data
    }
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Sync Complete: {healthy_count} stocks updated. Status: {status}")

if __name__ == "__main__":
    sync()
