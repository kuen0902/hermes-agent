#!/Users/bookid/.hermes/.venv/bin/python
import os
import json
import time
import argparse
import glob
import pandas as pd
import requests
import urllib3
from requests.adapters import HTTPAdapter
from datetime import datetime, timedelta

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create a robust, high-performance requests Session with optimized connection pool
session = requests.Session()
adapter = HTTPAdapter(
    pool_connections=35,
    pool_maxsize=35,
    max_retries=3
)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Configuration
SAVE_DIR = os.path.expanduser("~/.hermes/data/StockData_KBar_5M")
DATA_DIR = os.path.expanduser("~/.hermes/data")
ELIGIBLE_JSON_PATH = os.path.join(DATA_DIR, "eligible_5y_stocks.json")
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiYm9va2lkIiwiZW1haWwiOiJib29raWQyMDAwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjB9.MaUs7zQVYm5qKtlpIRdZ-s-I6WXCfcdtIowZiR7mXM4"

CANDIDATE_DIRS = [
    os.path.expanduser("~/.hermes/data/StockData_History_5Y"),
    os.path.expanduser("~/.hermes/data/StockData_History_Full"),
    os.path.expanduser("~/.hermes/data/StockData_History_Final")
]

os.makedirs(SAVE_DIR, exist_ok=True)

def fetch_single_day(ticker, date):
    """Helper to fetch a single day's K-bars."""
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        'dataset': 'TaiwanStockKBar',
        'data_id': ticker.split('.')[0],
        'start_date': date,
        'token': FINMIND_TOKEN
    }
    max_retries = 5
    attempt = 0
    while attempt < max_retries:
        try:
            # Using requests.get directly inside thread, which is completely thread-safe and avoids session-sharing deadlocks
            r = requests.get(url, params=params, timeout=(5, 10), verify=False)
            if r.status_code == 200:
                res_data = r.json()
                if res_data.get('status') == 200 or res_data.get('msg') == 'success':
                    return res_data.get('data', [])
                elif 'ip banned' in str(res_data.get('msg', '')).lower() or res_data.get('status') == 403:
                    retry_after = int(res_data.get('retry_after', 600))
                    print(f"\n🚨 IP Banned (200)! WAF throttling active. Sleeping for {retry_after + 10} seconds...")
                    time.sleep(retry_after + 10)
                    continue
            elif r.status_code == 403 or (r.status_code == 200 and 'ip banned' in r.text.lower()):
                try:
                    res_json = r.json()
                    retry_after = int(res_json.get('retry_after', 600))
                except Exception:
                    retry_after = 600
                print(f"\n🚨 IP Banned (403)! WAF throttling active. Sleeping for {retry_after + 10} seconds...")
                time.sleep(retry_after + 10)
                continue
            elif r.status_code == 429:
                time.sleep(5)
            time.sleep(0.1)
        except Exception:
            time.sleep(1)
        attempt += 1
    return []

def fetch_kbar_for_ticker_150d(ticker, clean_name):
    """Fetches K-bar data for the past 150 days by querying day by day in parallel with smart concurrency."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    # Find price CSV to extract exact trading dates
    file_path = None
    for c_dir in CANDIDATE_DIRS:
        p = os.path.join(c_dir, f"{ticker}_{clean_name}.csv")
        if os.path.exists(p):
            file_path = p
            break
            
    cutoff_date = datetime.now() - timedelta(days=150)
    
    # Extract trading dates
    trading_dates = []
    if file_path:
        try:
            price_df = pd.read_csv(file_path)
            price_df['Date'] = pd.to_datetime(price_df['Date'])
            recent_df = price_df[price_df['Date'] >= cutoff_date]
            trading_dates = recent_df['Date'].dt.strftime('%Y-%m-%d').tolist()
        except Exception:
            pass
            
    if not trading_dates:
        # Fallback to weekday calendar dates
        start_dt = cutoff_date
        end_dt = datetime.now()
        curr = start_dt
        while curr <= end_dt:
            # 0 is Monday, 5 is Saturday, 6 is Sunday
            if curr.weekday() < 5:
                trading_dates.append(curr.strftime("%Y-%m-%d"))
            curr += timedelta(days=1)
            
    records = []
    print(f"({len(trading_dates)} trading days)... ", end='', flush=True)
    
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(fetch_single_day, ticker, d): d for d in trading_dates}
        for future in as_completed(futures):
            res = future.result()
            if res:
                records.extend(res)
                
    return records

def resample_to_5m(records):
    """Resamples raw 1-minute K-bars into standard 5-minute OHLCV bars."""
    if not records:
        return pd.DataFrame()
        
    df = pd.DataFrame(records)
    required = ['date', 'minute', 'open', 'high', 'low', 'close', 'volume']
    for col in required:
        if col not in df.columns:
            return pd.DataFrame()
            
    # Combine date and minute to timestamp
    df['timestamp'] = pd.to_datetime(df['date'] + ' ' + df['minute'])
    df = df.set_index('timestamp').sort_index()
    
    # Convert numeric fields
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
    # Resample to 5 minutes
    resampled = df.resample('5Min', closed='right', label='right').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    # Discard non-trading empty rows
    resampled = resampled[resampled['volume'] > 0.0]
    
    return resampled.reset_index()

def init_duckdb_kbar_table(db_path):
    """Initializes the kbars_5m table in DuckDB."""
    import duckdb
    try:
        conn = duckdb.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kbars_5m (
                timestamp TIMESTAMP,
                code VARCHAR,
                ticker VARCHAR,
                name VARCHAR,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume BIGINT,
                PRIMARY KEY (timestamp, code)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kbars_code ON kbars_5m(code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kbars_time ON kbars_5m(timestamp)")
        conn.close()
    except Exception as e:
        # Graceful handling if database is locked
        print(f"⚠️ DuckDB Table Init Warning (Lock Conflict): {e}")

def main():
    parser = argparse.ArgumentParser(description="Fetch 150 days of 1-minute KBar data, resample to 5-minute bars and cache to CSV/DuckDB.")
    parser.add_argument("--top", type=int, default=100, help="Number of top high-liquidity stocks to fetch (default: 100)")
    parser.add_argument("--all", action="store_true", help="Fetch K-bars for ALL survivors")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing K-bar CSVs")
    args = parser.parse_args()
    
    if not os.path.exists(ELIGIBLE_JSON_PATH):
        print(f"❌ Eligible stocks registry not found at {ELIGIBLE_JSON_PATH}.")
        return
        
    with open(ELIGIBLE_JSON_PATH, 'r', encoding='utf-8') as f:
        eligible_stocks = json.load(f)
        
    if args.all:
        target_stocks = eligible_stocks
        print(f"Starting 5-minute K-bar expansion (past 150 days) for ALL {len(target_stocks)} survivors...")
    else:
        target_stocks = [s for s in eligible_stocks if s.get('is_top_500')]
        target_stocks = target_stocks[:args.top]
        print(f"Starting 5-minute K-bar expansion (past 150 days) for TOP {len(target_stocks)} high-liquidity survivors...")
        
    db_path = os.path.join(DATA_DIR, "potential_analysis.ddb")
    init_duckdb_kbar_table(db_path)
    
    success_count = 0
    skipped_count = 0
    start_time = time.time()
    
    for idx, s in enumerate(target_stocks):
        ticker = s['ticker']
        name = s['name']
        code = s['code']
        clean_name = name.replace('\ufffd', '').replace('*', '').strip()
        
        csv_path = os.path.join(SAVE_DIR, f"{ticker}_{clean_name}.csv")
        
        # Self-healing cache check: verify file has at least 1,000 lines (20+ days of bars)
        is_complete = False
        if os.path.exists(csv_path):
            try:
                with open(csv_path, 'r') as tmp_f:
                    lines = sum(1 for line in tmp_f)
                if lines >= 1000:
                    is_complete = True
            except Exception:
                pass
                
        if is_complete and not args.force:
            print(f"[{idx+1}/{len(target_stocks)}] {ticker} ({name}) already cached. (Use --force to overwrite)")
            skipped_count += 1
            continue
            
        print(f"[{idx+1}/{len(target_stocks)}] Expanding {ticker} ({name}) ", end='', flush=True)
        
        # 1. Fetch raw 1-minute bars day by day
        records = fetch_kbar_for_ticker_150d(ticker, clean_name)
        if not records:
            print("⚠️ No K-bar data returned.")
            continue
            
        # 2. Resample to 5-minute bars
        df_5m = resample_to_5m(records)
        if df_5m.empty:
            print("⚠️ No valid trading bars after resampling.")
            continue
            
        # 3. Save to CSV
        df_5m.to_csv(csv_path, index=False)
        print(f"✓ Cached ({len(df_5m)} 5M-bars)", end='')
        
        # 4. Sync to DuckDB
        try:
            import duckdb
            df_temp = df_5m.copy()
            df_temp['code'] = code
            df_temp['ticker'] = ticker
            df_temp['name'] = clean_name
            
            # Explicit column ordering
            df_temp = df_temp[['timestamp', 'code', 'ticker', 'name', 'open', 'high', 'low', 'close', 'volume']]
            
            conn = duckdb.connect(db_path)
            conn.execute("INSERT OR REPLACE INTO kbars_5m SELECT * FROM df_temp")
            conn.close()
            print(" -> DB synced.")
        except Exception as d_err:
            print(" (DB Lock conflict, cached to CSV only)")
            
        success_count += 1
        
        # Safe cooldown between stocks to avoid hitting WAF blocks
        time.sleep(2.5)
        
    print(f"\n--- 5-Minute K-Bar Expansion Summary ---")
    print(f"Total target stocks: {len(target_stocks)}")
    print(f"Skipped (already cached): {skipped_count}")
    print(f"Successfully processed: {success_count}")
    print(f"Total time elapsed: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
