#!/Users/bookid/.hermes/.venv/bin/python
import os
import json
import glob
import pandas as pd
import duckdb
from datetime import datetime

# Configuration
DATA_DIR = os.path.expanduser("~/.hermes/data")
FINAL_DIR = os.path.expanduser("~/Documents/StockData_History_Final")
FULL_DIR = os.path.expanduser("~/Documents/StockData_History_Full")
DB_PATH = os.path.join(DATA_DIR, "potential_analysis.ddb")
TRASH_JSON_PATH = os.path.join(DATA_DIR, "removed_trash_stocks.json")
MAPPING_JSON_PATH = os.path.join(DATA_DIR, "stock_mapping.json")

def get_db_connection():
    return duckdb.connect(DB_PATH)

def init_table(conn):
    cursor = conn.cursor()
    # Create the full_daily_prices table for 15-year history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS full_daily_prices (
            date DATE,
            code VARCHAR,
            ticker VARCHAR,
            name VARCHAR,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            adj_close DOUBLE,
            volume BIGINT,
            PRIMARY KEY (date, code)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_full_code ON full_daily_prices(code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_full_date ON full_daily_prices(date)")
    conn.commit()
    print("✓ [DuckDB] Table 'full_daily_prices' initialized successfully.")

def identify_and_load():
    print("=========================================================================")
    print("  🦆 DUCKDB BULK LOAD: 15-YEAR STOCK HISTORY & TRASH STOCK FILTERING")
    print("=========================================================================")
    
    conn = get_db_connection()
    init_table(conn)
    
    # Load CJK name mapping
    code_to_name = {}
    if os.path.exists(MAPPING_JSON_PATH):
        try:
            with open(MAPPING_JSON_PATH, 'r', encoding='utf-8') as f:
                m = json.load(f)
                code_to_name = {v: k for k, v in m.items()}
        except Exception:
            pass
            
    # Locate all CSV files in both FINAL_DIR and FULL_DIR to be fully comprehensive
    files_final = glob.glob(os.path.join(FINAL_DIR, "*.csv"))
    files_full = glob.glob(os.path.join(FULL_DIR, "*.csv"))
    
    # We will identify unique files by ticker to avoid double processing
    unique_tickers = {}
    
    # Combine lists, preferring FINAL_DIR since it has merged data
    for f in files_final:
        ticker = os.path.basename(f).split('_')[0]
        unique_tickers[ticker] = f
        
    for f in files_full:
        ticker = os.path.basename(f).split('_')[0]
        if ticker not in unique_tickers:
            unique_tickers[ticker] = f
            
    total_files = len(unique_tickers)
    print(f"Total unique historical stock files identified: {total_files}")
    
    cutoff_active = pd.to_datetime('2026-05-01')
    
    trash_stocks = []
    non_trash_files = []
    
    # First Pass: Identify trash stocks
    print("Running Pass 1: Screening for delisted/inactive 'trash stocks' (<2 years history)...")
    for ticker, filepath in unique_tickers.items():
        try:
            # Read first and last row to quickly determine dates
            # We use pandas tail/head to be fast
            df_dates = pd.read_csv(filepath, usecols=['Date'])
            if df_dates.empty:
                continue
                
            df_dates['Date'] = pd.to_datetime(df_dates['Date'])
            min_date = df_dates['Date'].min()
            max_date = df_dates['Date'].max()
            
            is_active = max_date >= cutoff_active
            duration_days = (max_date - min_date).days
            duration_years = duration_days / 365.25
            
            basename = os.path.basename(filepath)
            code = ticker.split('.')[0]
            name = code_to_name.get(code, basename.split('_')[1].replace('.csv', '') if '_' in basename else '')
            name = name.replace('\ufffd', '').replace('*', '').strip()
            
            # Definition: (Currently Inactive) AND (History < 2 Years)
            if (not is_active) and (duration_years < 2.0):
                trash_stocks.append({
                    "ticker": ticker,
                    "code": code,
                    "name": name,
                    "start_date": min_date.strftime('%Y-%m-%d'),
                    "end_date": max_date.strftime('%Y-%m-%d'),
                    "duration_years": float(duration_years),
                    "days": len(df_dates)
                })
            else:
                non_trash_files.append((ticker, code, name, filepath))
        except Exception as e:
            # If reading header fails, treat it as empty/corrupted
            pass
            
    print(f"\n--- PASS 1 SCREENING RESULT ---")
    print(f"Total screened stocks : {total_files}")
    print(f"Removed trash stocks  : {len(trash_stocks)}")
    print(f"Eligible stocks to load: {len(non_trash_files)}")
    print(f"--------------------------------")
    
    # Save the list of removed trash stocks
    with open(TRASH_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(trash_stocks, f, indent=2, ensure_ascii=False)
    print(f"✓ Trash stocks list saved to {TRASH_JSON_PATH}")
    
    # Pass 2: Bulk load non-trash stocks into DuckDB
    print("\nRunning Pass 2: Bulk loading 15-year historical daily prices...")
    loaded_count = 0
    total_records = 0
    start_time = datetime.now()
    
    batch_dfs = []
    
    for idx, (ticker, code, name, filepath) in enumerate(non_trash_files):
        try:
            df = pd.read_csv(filepath)
            if df.empty:
                continue
                
            # Assign metadata columns
            df['code'] = code
            df['ticker'] = ticker
            df['name'] = name
            
            # Ensure proper columns and order
            # Handles 'Adj Close' with double quotes or spaces
            adj_col = 'Adj Close' if 'Adj Close' in df.columns else df.columns[5]
            
            df_temp = df[['Date', 'code', 'ticker', 'name', 'Open', 'High', 'Low', 'Close', adj_col, 'Volume']].copy()
            df_temp.columns = ['date', 'code', 'ticker', 'name', 'open', 'high', 'low', 'close', 'adj_close', 'volume']
            
            # Robust data cleaning: coerce numeric types and drop corrupted rows
            for col in ['open', 'high', 'low', 'close', 'adj_close', 'volume']:
                df_temp[col] = pd.to_numeric(df_temp[col], errors='coerce')
                
            # Drop rows with NaN in critical price columns
            df_temp = df_temp.dropna(subset=['open', 'high', 'low', 'close', 'volume'])
            df_temp['volume'] = df_temp['volume'].astype('int64')
            df_temp['date'] = pd.to_datetime(df_temp['date']).dt.date
            
            if not df_temp.empty:
                batch_dfs.append(df_temp)
                loaded_count += 1
                total_records += len(df_temp)
            
            # Vectorized bulk load in batches of 100 files
            if len(batch_dfs) >= 100:
                combined_df = pd.concat(batch_dfs)
                conn.execute("INSERT OR REPLACE INTO full_daily_prices SELECT * FROM combined_df")
                batch_dfs = []
                if loaded_count % 300 == 0:
                    print(f"  Processed {loaded_count}/{len(non_trash_files)} stocks...")
                    
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            
    # Load remaining
    if batch_dfs:
        combined_df = pd.concat(batch_dfs)
        conn.execute("INSERT OR REPLACE INTO full_daily_prices SELECT * FROM combined_df")
        
    duration = datetime.now() - start_time
    print(f"✓ [DuckDB] Bulk load finished: {loaded_count} files loaded successfully.")
    print(f"✓ [DuckDB] Total historical records added: {total_records:,d} rows.")
    print(f"✓ [DuckDB] Elapsed time: {duration.total_seconds():.2f} seconds.")
    
    conn.close()
    
    # Display Trash Stocks to the user
    print("\n=========================================================================")
    print("  🚨 REMOVED TRASH STOCKS (垃圾股明細)")
    print("=========================================================================")
    if trash_stocks:
        print(f"{'股號':<8} | {'股名':<10} | {'起始日期':<10} | {'結束日期':<10} | {'資料年限':<8} | {'交易天數':<8}")
        print("-" * 70)
        for t in trash_stocks:
            print(f"{t['code']:<8} | {t['name']:<10} | {t['start_date']:<10} | {t['end_date']:<10} | {t['duration_years']:<8.2f} | {t['days']:<8}")
    else:
        print("沒有符合條件的垃圾股。")
    print("=========================================================================")

if __name__ == "__main__":
    identify_and_load()
