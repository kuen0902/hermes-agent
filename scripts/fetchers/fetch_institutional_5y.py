#!/Users/bookid/.hermes/.venv/bin/python
import os
import json
import time
import argparse
import glob
import pandas as pd
import requests
from datetime import datetime, timedelta

# Configuration
SAVE_DIR = os.path.expanduser("~/Documents/StockData_History_5Y")
DATA_DIR = os.path.expanduser("~/.hermes/data")
ELIGIBLE_JSON_PATH = os.path.join(DATA_DIR, "eligible_5y_stocks.json")
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiYm9va2lkIiwiZW1haWwiOiJib29raWQyMDAwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjB9.MaUs7zQVYm5qKtlpIRdZ-s-I6WXCfcdtIowZiR7mXM4"

def get_already_processed_tickers():
    """Checks which price CSV files already have institutional columns."""
    processed = set()
    csv_files = glob.glob(os.path.join(SAVE_DIR, "*.csv"))
    for f in csv_files:
        try:
            # Just read header
            df = pd.read_csv(f, nrows=2)
            if 'Foreign_Net' in df.columns and 'Trust_Net' in df.columns:
                basename = os.path.basename(f)
                ticker = basename.split('_')[0]
                processed.add(ticker)
        except Exception:
            pass
    return processed

def fetch_institutional_data_for_ticker(ticker, start_date, end_date):
    """Fetches 5-year institutional buy/sell data for a single stock from FinMind."""
    url = "https://api.finmindtrade.com/api/v4/data"
    stock_id = ticker.split('.')[0]
    
    params = {
        'dataset': 'TaiwanStockInstitutionalInvestorsBuySell',
        'data_id': stock_id,
        'start_date': start_date,
        'end_date': end_date,
        'token': FINMIND_TOKEN
    }
    
    max_retries = 3
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                res_data = r.json()
                if res_data.get('status') == 200 or res_data.get('msg') == 'success':
                    return res_data.get('data', [])
                elif 'level is register' in res_data.get('msg', ''):
                    print("⚠️ FinMind API rate-limit message: register level limitations.")
                    time.sleep(5)
            elif r.status_code == 429:
                print(f"⚠️ Hit 429 Rate Limit. Sleeping for {retry_delay}s (Attempt {attempt+1}/{max_retries})...")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                print(f"⚠️ Non-200 Status {r.status_code} for {ticker}")
                time.sleep(2)
        except Exception as e:
            print(f"⚠️ Network error for {ticker}: {e}")
            time.sleep(3)
            
    return []

def process_institutional_records(records):
    """Pivots institutional records into daily Net Buys in '張' (thousand shares)."""
    if not records:
        return pd.DataFrame()
        
    df = pd.DataFrame(records)
    
    # Check fields
    if 'date' not in df.columns or 'buy' not in df.columns or 'sell' not in df.columns or 'name' not in df.columns:
        return pd.DataFrame()
        
    df['date'] = pd.to_datetime(df['date'])
    df['net_buy'] = (df['buy'] - df['sell']) / 1000.0  # Convert to thousand shares (張)
    
    # Group names:
    # Foreign Investors: Foreign_Investor, Foreign_Dealer_Self
    # Investment Trusts: Investment_Trust
    # Dealers: Dealer_self, Dealer_Hedging, Dealer
    
    # We will map each name to its simplified role
    def map_role(name):
        name_lower = name.lower()
        if 'foreign' in name_lower:
            return 'Foreign_Net'
        elif 'trust' in name_lower:
            return 'Trust_Net'
        elif 'dealer' in name_lower:
            return 'Dealer_Net'
        return None
        
    df['role'] = df['name'].apply(map_role)
    df = df.dropna(subset=['role'])
    
    if df.empty:
        return pd.DataFrame()
        
    # Pivot
    pivoted = df.pivot_table(index='date', columns='role', values='net_buy', aggfunc='sum').reset_index()
    
    # Ensure all columns exist
    for col in ['Foreign_Net', 'Trust_Net', 'Dealer_Net']:
        if col not in pivoted.columns:
            pivoted[col] = 0.0
            
    return pivoted

def main():
    parser = argparse.ArgumentParser(description="Fetch 5 years of daily institutional data and merge with price CSVs.")
    parser.add_argument("--top", type=int, default=500, help="Number of top high-liquidity stocks to fetch")
    parser.add_argument("--all", action="store_true", help="Fetch for all eligible stock survivors")
    parser.add_argument("--force", action="store_true", help="Force overwrite even if already processed")
    args = parser.parse_args()
    
    if not os.path.exists(ELIGIBLE_JSON_PATH):
        print(f"❌ Eligible stocks registry not found at {ELIGIBLE_JSON_PATH}. Run fetch_history_5y.py first.")
        return
        
    with open(ELIGIBLE_JSON_PATH, 'r', encoding='utf-8') as f:
        eligible_stocks = json.load(f)
        
    # Filter based on args
    if args.all:
        target_stocks = eligible_stocks
        print(f"Starting institutional data fetch for ALL {len(target_stocks)} survivors...")
    else:
        target_stocks = [s for s in eligible_stocks if s.get('is_top_500')]
        # If there are fewer than 500, get whatever is available
        target_stocks = target_stocks[:args.top]
        print(f"Starting institutional data fetch for TOP {len(target_stocks)} high-liquidity survivors...")
        
    processed_tickers = set() if args.force else get_already_processed_tickers()
    if processed_tickers:
        print(f"ℹ️ Found {len(processed_tickers)} stocks already processed. (Use --force to overwrite)")
        
    # Date range
    end_date_obj = datetime.now()
    start_date_obj = end_date_obj - timedelta(days=5*365 + 10)
    start_str = start_date_obj.strftime('%Y-%m-%d')
    end_str = end_date_obj.strftime('%Y-%m-%d')
    
    success_count = 0
    skipped_count = 0
    api_call_count = 0
    
    start_time = time.time()
    
    for idx, s in enumerate(target_stocks):
        ticker = s['ticker']
        name = s['name']
        
        # Check if already processed
        if ticker in processed_tickers:
            skipped_count += 1
            continue
            
        print(f"[{idx+1}/{len(target_stocks)}] Syncing {ticker} ({name})... ", end='', flush=True)
        
        # Check if price CSV exists
        file_path = os.path.join(SAVE_DIR, f"{ticker}_{name}.csv")
        if not os.path.exists(file_path):
            print("❌ Price CSV file not found. Skipping.")
            continue
            
        # Fetch records
        records = fetch_institutional_data_for_ticker(ticker, start_str, end_str)
        api_call_count += 1
        
        if not records:
            print("⚠️ No institutional data retrieved.")
            # Brief sleep to respect rate limits
            time.sleep(1.0)
            continue
            
        # Process and pivot
        inst_df = process_institutional_records(records)
        if inst_df.empty:
            print("⚠️ Failed to parse institutional records.")
            time.sleep(1.0)
            continue
            
        # Merge with prices
        try:
            price_df = pd.read_csv(file_path)
            price_df['Date'] = pd.to_datetime(price_df['Date'])
            
            # Merge
            merged = pd.merge(price_df, inst_df, left_on='Date', right_on='date', how='left')
            merged = merged.drop(columns=['date'], errors='ignore')
            
            # Fill NaNs with 0.0 for institutional buy/sells
            for col in ['Foreign_Net', 'Trust_Net', 'Dealer_Net']:
                merged[col] = merged[col].fillna(0.0)
                
            # Keep only original columns + institutional columns
            merged.to_csv(file_path, index=False)
            print(f"✓ Merged and saved ({len(merged)} records)", end='')
            
            # Sync to DuckDB
            try:
                import duckdb
                db_path = os.path.join(DATA_DIR, "potential_analysis.ddb")
                conn = duckdb.connect(db_path)
                
                df_temp = merged.copy()
                df_temp['Date'] = df_temp['Date'].dt.date
                df_temp['code'] = s['code']
                df_temp['ticker'] = ticker
                df_temp['name'] = name
                
                adj_col = 'Adj Close' if 'Adj Close' in df_temp.columns else df_temp.columns[5]
                df_temp = df_temp[['Date', 'code', 'ticker', 'name', 'Open', 'High', 'Low', 'Close', adj_col, 'Volume', 'Foreign_Net', 'Trust_Net', 'Dealer_Net']]
                df_temp.columns = ['date', 'code', 'ticker', 'name', 'open', 'high', 'low', 'close', 'adj_close', 'volume', 'foreign_net', 'trust_net', 'dealer_net']
                
                conn.execute("INSERT OR REPLACE INTO daily_stock_data SELECT * FROM df_temp")
                conn.close()
                print(" -> DuckDB synced.")
            except Exception as d_err:
                print(f" (DuckDB Sync Failed: {d_err})")
                
            success_count += 1
            
        except Exception as e:
            print(f"❌ Error merging: {e}")
            
        # Fine-tuned sleep: 600 requests per hour means 6.0 seconds per request.
        # We sleep 6.2 seconds to guarantee we never exceed the rate limit.
        time.sleep(6.2)
        
        # Periodic report
        if api_call_count > 0 and api_call_count % 50 == 0:
            elapsed = time.time() - start_time
            print(f"\n--- Periodic Progress: Synced {idx+1}/{len(target_stocks)} stocks. Calls: {api_call_count}. Elapsed: {elapsed:.1f}s ---")
            
    print(f"\n--- Institutional Sync Summary ---")
    print(f"Total target stocks: {len(target_stocks)}")
    print(f"Skipped (already merged): {skipped_count}")
    print(f"Successfully processed: {success_count}")
    print(f"Total FinMind API calls: {api_call_count}")
    print(f"Total time elapsed: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    import glob
    main()
