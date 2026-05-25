#!/Users/bookid/.hermes/.venv/bin/python
import os
import json
import time
import argparse
import glob
import pandas as pd
import requests
import urllib3
from datetime import datetime

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration - Redirected to central ~/.hermes/data directory to bypass TCC permission blocks
SAVE_DIR = os.path.expanduser("~/.hermes/data/StockData_History_5Y")
DATA_DIR = os.path.expanduser("~/.hermes/data")
ELIGIBLE_JSON_PATH = os.path.join(DATA_DIR, "eligible_5y_stocks.json")
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiYm9va2lkIiwiZW1haWwiOiJib29raWQyMDAwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjB9.MaUs7zQVYm5qKtlpIRdZ-s-I6WXCfcdtIowZiR7mXM4"

CANDIDATE_DIRS = [
    os.path.expanduser("~/.hermes/data/StockData_History_5Y"),
    os.path.expanduser("~/.hermes/data/StockData_History_Full"),
    os.path.expanduser("~/.hermes/data/StockData_History_Final")
]

os.makedirs(SAVE_DIR, exist_ok=True)

def get_already_processed_tickers():
    """Checks which price CSV files already have full 14-year (since 2012) expanded institutional & shareholding data."""
    processed = set()
    for c_dir in CANDIDATE_DIRS:
        if not os.path.exists(c_dir):
            continue
        csv_files = glob.glob(os.path.join(c_dir, "*.csv"))
        for f in csv_files:
            try:
                df = pd.read_csv(f)
                if 'Large_Holder_Rate' not in df.columns:
                    continue
                df['Date'] = pd.to_datetime(df['Date'])
                df_valid = df[df['Date'] >= pd.to_datetime('2012-05-02')]
                if df_valid.empty:
                    basename = os.path.basename(f)
                    ticker = basename.split('_')[0]
                    processed.add(ticker)
                    continue
                
                # Check first 50 rows after 2012-05-02 to verify shareholding data exists and is populated
                first_rows = df_valid.head(50)
                if (first_rows['Large_Holder_Rate'] > 0.0).any():
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
            r = requests.get(url, params=params, timeout=15, verify=False)
            if r.status_code == 200:
                res_data = r.json()
                if res_data.get('status') == 200 or res_data.get('msg') == 'success':
                    return res_data.get('data', [])
                elif 'level is register' in res_data.get('msg', ''):
                    print("⚠️ FinMind API rate-limit message: register level limitations.")
                    time.sleep(5)
            elif r.status_code == 429:
                print(f"⚠️ Hit 429 Rate Limit for Institutional. Sleeping for {retry_delay}s (Attempt {attempt+1}/{max_retries})...")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                print(f"⚠️ Non-200 Status {r.status_code} for {ticker}")
                time.sleep(2)
        except Exception as e:
            print(f"⚠️ Network error for {ticker} (Inst): {e}")
            time.sleep(3)
            
    return []

def fetch_margin_data_for_ticker(ticker, start_date, end_date):
    """Fetches 5-year margin purchase and short sale data for a single stock from FinMind."""
    url = "https://api.finmindtrade.com/api/v4/data"
    stock_id = ticker.split('.')[0]
    
    params = {
        'dataset': 'TaiwanStockMarginPurchaseShortSale',
        'data_id': stock_id,
        'start_date': start_date,
        'end_date': end_date,
        'token': FINMIND_TOKEN
    }
    
    max_retries = 3
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            r = requests.get(url, params=params, timeout=15, verify=False)
            if r.status_code == 200:
                res_data = r.json()
                if res_data.get('status') == 200 or res_data.get('msg') == 'success':
                    return res_data.get('data', [])
            elif r.status_code == 429:
                print(f"⚠️ Hit 429 Rate Limit for Margin. Sleeping for {retry_delay}s (Attempt {attempt+1}/{max_retries})...")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                time.sleep(2)
        except Exception as e:
            print(f"⚠️ Network error for {ticker} (Margin): {e}")
            time.sleep(3)
            
    return []

def fetch_shareholding_data_for_ticker(ticker, start_date, end_date):
    """Fetches weekly shareholder levels data for a single stock from FinMind."""
    url = "https://api.finmindtrade.com/api/v4/data"
    stock_id = ticker.split('.')[0]
    
    params = {
        'dataset': 'TaiwanStockHoldingSharesPer',
        'data_id': stock_id,
        'start_date': start_date,
        'end_date': end_date,
        'token': FINMIND_TOKEN
    }
    
    max_retries = 3
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            r = requests.get(url, params=params, timeout=15, verify=False)
            if r.status_code == 200:
                res_data = r.json()
                if res_data.get('status') == 200 or res_data.get('msg') == 'success':
                    return res_data.get('data', [])
            elif r.status_code == 429:
                print(f"⚠️ Hit 429 Rate Limit for Shareholding. Sleeping for {retry_delay}s (Attempt {attempt+1}/{max_retries})...")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                time.sleep(2)
        except Exception as e:
            print(f"⚠️ Network error for {ticker} (Shareholding): {e}")
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

def process_margin_records(records):
    """Processes margin records into daily net buys, balances, and short-to-margin ratio in '張'."""
    if not records:
        return pd.DataFrame()
        
    df = pd.DataFrame(records)
    
    required_cols = ['date', 'MarginPurchaseBuy', 'MarginPurchaseSell', 
                     'ShortSaleSell', 'ShortSaleBuy', 'ShortSaleTodayBalance', 'MarginPurchaseTodayBalance']
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0.0
            
    df['date'] = pd.to_datetime(df['date'])
    
    for col in ['MarginPurchaseBuy', 'MarginPurchaseSell', 'ShortSaleSell', 'ShortSaleBuy', 
                'ShortSaleTodayBalance', 'MarginPurchaseTodayBalance']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
    df['Margin_Net'] = df['MarginPurchaseBuy'] - df['MarginPurchaseSell']
    df['Short_Net'] = df['ShortSaleSell'] - df['ShortSaleBuy']
    df['Short_Balance'] = df['ShortSaleTodayBalance']
    df['Margin_Balance'] = df['MarginPurchaseTodayBalance']
    
    # Calculate Short_Margin_Ratio in %
    df['Short_Margin_Ratio'] = 0.0
    valid_margin_mask = df['Margin_Balance'] != 0.0
    df.loc[valid_margin_mask, 'Short_Margin_Ratio'] = (df.loc[valid_margin_mask, 'Short_Balance'] / df.loc[valid_margin_mask, 'Margin_Balance']) * 100.0
    
    return df[['date', 'Margin_Net', 'Short_Net', 'Short_Balance', 'Margin_Balance', 'Short_Margin_Ratio']]

def process_shareholding_records(records):
    """Processes weekly shareholding records into aggregated large/retail holder rates and total shareholders."""
    if not records:
        return pd.DataFrame()
        
    df = pd.DataFrame(records)
    
    if 'date' not in df.columns or 'HoldingSharesLevel' not in df.columns or 'percent' not in df.columns or 'people' not in df.columns:
        return pd.DataFrame()
        
    df['date'] = pd.to_datetime(df['date'])
    df['percent'] = pd.to_numeric(df['percent'], errors='coerce').fillna(0.0)
    df['people'] = pd.to_numeric(df['people'], errors='coerce').fillna(0.0)
    
    # Pivot or filter and aggregate
    # 1. Large Holder Rate
    large_df = df[df['HoldingSharesLevel'] == 'more than 1,000,001'][['date', 'percent']].copy()
    large_df.columns = ['date', 'Large_Holder_Rate']
    
    # 2. Retail Holder Rate (10張以下散戶: 1-999, 1,000-5,000, 5,001-10,000)
    retail_levels = ['1-999', '1,000-5,000', '5,001-10,000']
    retail_sub = df[df['HoldingSharesLevel'].isin(retail_levels)]
    retail_df = retail_sub.groupby('date')['percent'].sum().reset_index()
    retail_df.columns = ['date', 'Retail_Holder_Rate']
    
    # 3. Total Holders
    total_df = df[df['HoldingSharesLevel'] == 'total'][['date', 'people']].copy()
    total_df.columns = ['date', 'Total_Holders']
    
    # Merge them together
    merged_sh = pd.merge(large_df, retail_df, on='date', how='outer')
    merged_sh = pd.merge(merged_sh, total_df, on='date', how='outer')
    
    return merged_sh

def main():
    parser = argparse.ArgumentParser(description="Fetch 14 years of daily institutional, margin and weekly shareholding data and merge with price CSVs.")
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
        print(f"Starting expanded data fetch for ALL {len(target_stocks)} survivors...")
    else:
        target_stocks = [s for s in eligible_stocks if s.get('is_top_500')]
        target_stocks = target_stocks[:args.top]
        print(f"Starting expanded data fetch for TOP {len(target_stocks)} high-liquidity survivors...")
        
    processed_tickers = set() if args.force else get_already_processed_tickers()
    if processed_tickers:
        print(f"ℹ️ Found {len(processed_tickers)} stocks already processed. (Use --force to overwrite)")
        
    # Date range - set to FinMind's institutional start date (2012-05-02) for full 14-year backfill
    end_date_obj = datetime.now()
    start_date_obj = datetime.strptime("2012-05-02", "%Y-%m-%d")
    start_str = start_date_obj.strftime('%Y-%m-%d')
    end_str = end_date_obj.strftime('%Y-%m-%d')
    
    success_count = 0
    skipped_count = 0
    api_call_count = 0
    
    start_time = time.time()
    
    for idx, s in enumerate(target_stocks):
        ticker = s['ticker']
        name = s['name']
        clean_name = name.replace('\ufffd', '').replace('*', '').strip()
        
        # Check if already processed
        if ticker in processed_tickers:
            skipped_count += 1
            continue
            
        print(f"[{idx+1}/{len(target_stocks)}] Syncing {ticker} ({name})... ", end='', flush=True)
        
        # Check if price CSV exists in any candidate directory
        file_path = None
        for c_dir in CANDIDATE_DIRS:
            p = os.path.join(c_dir, f"{ticker}_{clean_name}.csv")
            if os.path.exists(p):
                file_path = p
                break
                
        if not file_path:
            print("❌ Price CSV file not found in any candidate directory. Skipping.")
            continue
            
        # 1. Fetch institutional records
        inst_records = fetch_institutional_data_for_ticker(ticker, start_str, end_str)
        api_call_count += 1
        time.sleep(0.05)
        
        # 2. Fetch margin records
        margin_records = fetch_margin_data_for_ticker(ticker, start_str, end_str)
        api_call_count += 1
        time.sleep(0.05)
        
        # 3. Fetch shareholding records
        sh_records = fetch_shareholding_data_for_ticker(ticker, start_str, end_str)
        api_call_count += 1
        
        if not inst_records and not margin_records and not sh_records:
            print("⚠️ No data retrieved from FinMind.")
            time.sleep(5.0)
            continue
            
        inst_df = process_institutional_records(inst_records)
        margin_df = process_margin_records(margin_records)
        sh_df = process_shareholding_records(sh_records)
        
        # Merge with prices
        try:
            price_df = pd.read_csv(file_path)
            price_df['Date'] = pd.to_datetime(price_df['Date'])
            
            # Clean existing columns from price_df to prevent merge duplication
            cols_to_drop = ['Foreign_Net', 'Trust_Net', 'Dealer_Net', 'Margin_Net', 'Major_Net',
                            'Short_Net', 'Short_Balance', 'Margin_Balance', 'Short_Margin_Ratio',
                            'Large_Holder_Rate', 'Retail_Holder_Rate', 'Total_Holders']
            for col in cols_to_drop:
                if col in price_df.columns:
                    price_df = price_df.drop(columns=[col])
            
            # Merge institutional
            if not inst_df.empty:
                merged = pd.merge(price_df, inst_df, left_on='Date', right_on='date', how='left')
                merged = merged.drop(columns=['date'], errors='ignore')
            else:
                merged = price_df.copy()
                for col in ['Foreign_Net', 'Trust_Net', 'Dealer_Net']:
                    merged[col] = 0.0
                    
            # Merge margin
            if not margin_df.empty:
                merged = pd.merge(merged, margin_df, left_on='Date', right_on='date', how='left')
                merged = merged.drop(columns=['date'], errors='ignore')
            else:
                for col in ['Margin_Net', 'Short_Net', 'Short_Balance', 'Margin_Balance', 'Short_Margin_Ratio']:
                    merged[col] = 0.0
                    
            # Merge shareholding
            if not sh_df.empty:
                merged = pd.merge(merged, sh_df, left_on='Date', right_on='date', how='left')
                merged = merged.drop(columns=['date'], errors='ignore')
            else:
                for col in ['Large_Holder_Rate', 'Retail_Holder_Rate', 'Total_Holders']:
                    merged[col] = 0.0
                    
            # Fill NaNs for daily columns with 0.0
            for col in ['Foreign_Net', 'Trust_Net', 'Dealer_Net', 'Margin_Net', 
                        'Short_Net', 'Short_Balance', 'Margin_Balance', 'Short_Margin_Ratio']:
                merged[col] = merged[col].fillna(0.0)
                
            # Forward-fill and backward-fill weekly shareholding data
            for col in ['Large_Holder_Rate', 'Retail_Holder_Rate', 'Total_Holders']:
                merged[col] = merged[col].ffill().bfill().fillna(0.0)
                
            # Calculate Major_Net
            merged['Major_Net'] = merged['Foreign_Net'] + merged['Trust_Net'] + merged['Dealer_Net'] + merged['Margin_Net']
            
            # Save merged back to CSV cache
            merged.to_csv(file_path, index=False)
            print(f"✓ Merged ({len(merged)} records)", end='')
            
            # Sync directly to DuckDB daily_stock_data table
            try:
                import duckdb
                db_path = os.path.join(DATA_DIR, "potential_analysis.ddb")
                conn = duckdb.connect(db_path)
                
                df_temp = merged.copy()
                df_temp['Date'] = df_temp['Date'].dt.date
                df_temp['code'] = s['code']
                df_temp['ticker'] = ticker
                df_temp['name'] = clean_name
                
                adj_col = 'Adj Close' if 'Adj Close' in df_temp.columns else df_temp.columns[5]
                df_temp = df_temp[['Date', 'code', 'ticker', 'name', 'Open', 'High', 'Low', 'Close', adj_col, 'Volume', 
                                   'Foreign_Net', 'Trust_Net', 'Dealer_Net', 'Margin_Net', 'Major_Net',
                                   'Short_Net', 'Short_Balance', 'Margin_Balance', 'Short_Margin_Ratio',
                                   'Large_Holder_Rate', 'Retail_Holder_Rate', 'Total_Holders']]
                df_temp.columns = ['date', 'code', 'ticker', 'name', 'open', 'high', 'low', 'close', 'adj_close', 'volume', 
                                   'foreign_net', 'trust_net', 'dealer_net', 'margin_net', 'major_net',
                                   'short_net', 'short_balance', 'margin_balance', 'short_margin_ratio',
                                   'large_holder_rate', 'retail_holder_rate', 'total_holders']
                
                conn.execute("INSERT OR REPLACE INTO daily_stock_data SELECT * FROM df_temp")
                conn.close()
                print(" -> DuckDB synced.")
            except Exception as d_err:
                print(f" (DuckDB Sync Failed: {d_err})")
                
            success_count += 1
            
        except Exception as e:
            print(f"❌ Error merging: {e}")
            
        # Respect FinMind's API rate limits
        time.sleep(0.05)
        
        # Periodic report
        if api_call_count > 0 and api_call_count % 50 == 0:
            elapsed = time.time() - start_time
            print(f"\n--- Periodic Progress: Synced {idx+1}/{len(target_stocks)} stocks. Calls: {api_call_count}. Elapsed: {elapsed:.1f}s ---")
            
    print(f"\n--- Institutional, Margin & Shareholding Sync Summary ---")
    print(f"Total target stocks: {len(target_stocks)}")
    print(f"Skipped (already merged): {skipped_count}")
    print(f"Successfully processed: {success_count}")
    print(f"Total FinMind API calls: {api_call_count}")
    print(f"Total time elapsed: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
