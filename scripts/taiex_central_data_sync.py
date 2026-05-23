#!/Users/bookid/.hermes/.venv/bin/python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pandas",
#     "requests",
#     "urllib3",
#     "yfinance",
# ]
# ///
import subprocess
import json
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Any
import requests  # type: ignore
import pandas as pd  # type: ignore
import urllib3  # type: ignore
import yfinance as yf  # type: ignore

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_session() -> requests.Session:
    session = requests.Session()
    
    # User-Agent Rotator to prevent rate-limit bans
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
    ]
    session.headers.update({'User-Agent': random.choice(user_agents)})
    
    # Exponential Backoff Configuration
    retry_strategy = Retry(
        total=5,  # Maximum number of retries
        backoff_factor=1.5,  # 1.5, 3.0, 6.75 seconds...
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session

# Configuration
NUMBERS_PATH = Path("/Users/bookid/Documents/StockTracking_Daily.numbers")
CACHE_FILE = Path("/Users/bookid/.hermes/data/central_stock_data.json")
HISTORY_LOG_FILE = Path("/Users/bookid/.hermes/data/intraday_data_log.csv")

type PortfolioDict = dict[str, dict[str, Any]]

def get_personal_tickers() -> PortfolioDict:
    """Fetches Ticker, Name, Qty, and Avg Cost from Numbers 'Portfolio' sheet headlessly or via AppleScript fallback."""
    portfolio: PortfolioDict = {}
    
    # 1. 嘗試優先使用 numbers-parser 庫進行靜默無頭背景讀取
    try:
        from numbers_parser import Document
        if NUMBERS_PATH.exists():
            doc = Document(str(NUMBERS_PATH))
            sheets = doc.sheets
            portfolio_sheet = None
            for s in sheets:
                if s.name == "Portfolio":
                    portfolio_sheet = s
                    break
            
            if portfolio_sheet is not None:
                table = portfolio_sheet.tables[0]
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                # 遍歷所有列 (跳過第一列 Header)
                for row in table.rows()[1:]:
                    code_cell = getattr(row[0], "value", row[0])
                    if code_cell is not None:
                        code = str(code_cell).strip().strip("'")
                        if code.endswith(".0"):
                            code = code[:-2]  # 去除浮點數點零後綴 '2330.0' -> '2330'
                            
                        raw_name = str(getattr(row[1], "value", row[1]) or "")
                        clean_name = ansi_escape.sub('', raw_name)
                        
                        qty_val: Any = getattr(row[2], "value", row[2])
                        avg_val: Any = getattr(row[3], "value", row[3])  # Column D (0-indexed column 3) is Price (Average Buy Price)
                        
                        portfolio[code] = {
                            "name": clean_name,
                            "qty": float(qty_val) if qty_val is not None else 0.0,
                            "avg": float(avg_val) if avg_val is not None else 0.0
                        }
                print(f"✓ [Headless Numbers] 成功使用 numbers-parser 讀取 {len(portfolio)} 檔個人持股。")
                return portfolio
    except Exception as e:
        # 當未安裝此套件或有任何檔案存取異常時，安全進入下方的 AppleScript 降級備援
        pass

    # 2. Legacy AppleScript GUI 備援降級方案
    print("⚠️ 未安裝 numbers-parser 或無頭解析失敗，降級使用舊版 AppleScript GUI 引擎...")
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
                            set avgVal to value of cell 4 of row i
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
            subprocess.run(['open', str(NUMBERS_PATH)])
            time.sleep(5)

        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            for line in lines:
                parts = line.split('\t')
                if len(parts) >= 4:
                    c = parts[0].strip().strip("'")
                    if "." in c and c.split(".")[-1] == "0": c = c.split(".")[0]
                    raw_name = parts[1].strip()
                    clean_name = ansi_escape.sub('', raw_name)
                    portfolio[c] = {
                        "name": clean_name,
                        "qty": float(parts[2]) if parts[2] != "missing value" and parts[2].strip() else 0,
                        "avg": float(parts[3]) if parts[3] != "missing value" and parts[3].strip() else 0
                    }
    except Exception as e:
        print(f"Numbers Fetch Error: {e}")
    return portfolio

def log_to_csv(data: dict[str, dict[str, Any]], codes_mapping: dict[str, str]) -> None:
    """Logs intraday data to a persistent CSV for reference."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_exists = HISTORY_LOG_FILE.exists()
    HISTORY_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_LOG_FILE.open('a') as f:
        if not file_exists:
            f.write("timestamp,code,name,price,volume,pct_change\n")
        for code, info in data.items():
            name = codes_mapping.get(code, "Unknown")
            f.write(f"{now},{code},{name},{info['price']},{info['volume']},{info['pct']:.4f}\n")
            
    # ⚡ 盤中 Feather 高速暫存層實作 (Case 6 優化)
    FEATHER_PATH = HISTORY_LOG_FILE.parent / "intraday_today.feather"
    new_records = []
    for code, info in data.items():
        name = codes_mapping.get(code, "Unknown")
        new_records.append({
            "timestamp": now,
            "code": code,
            "name": name,
            "price": float(info['price']) if info['price'] is not None else 0.0,
            "volume": int(info['volume']) if info['volume'] is not None else 0,
            "pct_change": float(info['pct']) if info['pct'] is not None else 0.0
        })
    if new_records:
        try:
            new_df = pd.DataFrame(new_records)
            if FEATHER_PATH.exists():
                try:
                    old_df = pd.read_feather(FEATHER_PATH)
                    df = pd.concat([old_df, new_df], ignore_index=True)
                except Exception:
                    df = new_df
            else:
                df = new_df
            df.to_feather(FEATHER_PATH)
            print("⚡ [Feather Speed Layer] 盤中即時行情成功記錄。")
        except Exception as e:
            print(f"⚠️ Feather 寫入失敗: {e}")

def fetch_twse_data(codes: list[str]) -> dict[str, dict[str, Any]]:
    """Fetches real-time data from TWSE/OTC API."""
    results: dict[str, dict[str, Any]] = {}
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
                    except ValueError:
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

def fetch_yfinance_fallback(codes: list[str]) -> dict[str, dict[str, Any]]:
    """Fetches data via yfinance for tickers that failed TWSE API."""
    results: dict[str, dict[str, Any]] = {}
    if not codes: return results
    
    session = get_session()
    for c in codes:
        for suffix in [".TW", ".TWO"]:
            sym = f"{c}{suffix}"
            try:
                # Adding session for resilience in newer yfinance versions if supported, 
                # else wrapping with a short sleep to avoid hammering
                t = yf.Ticker(sym)
                hist = t.history(period="2d")
                if len(hist) >= 1:
                    price = float(hist['Close'].iloc[-1])
                    prev = float(hist['Close'].iloc[0]) if len(hist) > 1 else price
                    volume = int(hist['Volume'].iloc[-1])
                    results[c] = {
                        "symbol": sym,
                        "price": price,
                        "volume": volume,
                        "prev_close": prev,
                        "change": price - prev,
                        "pct": (price - prev) / prev * 100 if prev else 0,
                        "time": datetime.now().isoformat()
                    }
                    break
            except Exception as e:
                time.sleep(1) # Backoff for yfinance on error
                continue
        time.sleep(0.5) # Gentle rate limiting between symbols
    return results

def sync() -> None:
    print("Starting Central Stock Data Sync (TWSE API + YF Fallback)...")
    personal_data = get_personal_tickers()
    william_defaults = {
        "2376": "技嘉", "7828": "創新服務", "3709": "鑫聯大", "8299": "群聯", "4543": "萬在"
    }
    group_defaults = {
        "2317": "鴻海",
        "2409": "友達",
        "1513": "中興電", "2049": "上銀", "5347": "世界", "6147": "頎邦", "3709": "鑫聯大",
        "2408": "南亞科", "2382": "廣達", "2327": "國巨",
        "2313": "華通", "6285": "啟碁", "5289": "宜鼎", "2303": "聯電",
        "2376": "技嘉", "7828": "創新服務", "4925": "智微", "6125": "廣運",
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
    
    # Sanitize float values to ensure valid JSON (replace NaN/Inf with None)
    for code, info in list(market_data.items()):
        for key, val in list(info.items()):
            if isinstance(val, float) and (val != val or val == float('inf') or val == float('-inf')):
                info[key] = None

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
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Sync Complete: {healthy_count} stocks updated. Status: {status}")

if __name__ == "__main__":
    import time
    start_time = time.time()
    sync()
    end_time = time.time()
    print(f"Process Time: {end_time - start_time:.2f}s")
