import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import json
import requests
from bs4 import BeautifulSoup
import urllib3
import time

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
DATA_DIR = os.path.expanduser("~/Documents/StockData_History_Final")
os.makedirs(DATA_DIR, exist_ok=True)

def get_tw_stock_list():
    """Fetches all TWSE/TPEx stock symbols from ISIN page."""
    print("Fetching latest stock list from ISIN...")
    stocks = {}
    for mode in [2, 4]: # 2: Listed, 4: OTC
        url = f"https://isin.twse.com.tw/isin/C_public.jsp?strMode={mode}"
        try:
            response = requests.get(url, timeout=15, verify=False)
            response.encoding = 'big5'
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'class': 'h4'})
            if not table: continue
            for row in table.find_all('tr')[1:]:
                tds = row.find_all('td')
                if len(tds) < 1: continue
                text = tds[0].text.strip()
                parts = text.split('\u3000') # Wide space
                if len(parts) == 2:
                    code, name = parts
                    if len(code) == 4 and code.isdigit():
                        suffix = ".TW" if mode == 2 else ".TWO"
                        stocks[code + suffix] = name
        except Exception as e:
            print(f"Error fetching list for mode {mode}: {e}")
    return stocks

def verify_health(file_path):
    """Mandatory Health Check Protocol (v2.0)"""
    try:
        if not os.path.exists(file_path): return False
        size_kb = os.path.getsize(file_path) / 1024
        if size_kb < 1: return False
        df = pd.read_csv(file_path)
        if df.empty: return False
        if 'Date' not in df.columns: return False
        nan_count = df['Close'].isna().sum()
        if nan_count > len(df) * 0.05: return False
        return True
    except:
        return False

def sync_all(fast_mode=False):
    print(f"--- Starting Daily Historical Sync [{'Fast' if fast_mode else 'Full'}] [{datetime.now().strftime('%Y-%m-%d %H:%M')}] ---")
    
    # 1. Get symbols to sync
    symbols_map = {}
    if fast_mode:
        try:
            with open(os.path.expanduser("~/.hermes/data/central_stock_data.json"), 'r') as f:
                c_data = json.load(f)
                symbols_map = {k + (".TW" if "." not in k else ""): v for k, v in c_data.get("full_mapping", {}).items()}
        except:
            print("Fast mode requested but central_stock_data.json missing. Falling back to full.")
            symbols_map = get_tw_stock_list()
    else:
        symbols_map = get_tw_stock_list()
    
    all_symbols = list(symbols_map.keys())
    
    # 2. Identify missing vs existing
    existing_files = {f.split('_')[0]: f for f in os.listdir(DATA_DIR) if f.endswith('.csv')}
    
    # 3. Process to update (Prioritize fast_mode symbols)
    to_update = [s for s in all_symbols if s in existing_files]
    if fast_mode:
        print(f"Fast Sync: Updating {len(to_update)} core monitoring stocks...")
    else:
        print(f"Full Sync: Updating {len(to_update)} existing records...")
    
    # We download last 7 days to cover weekends/holidays/late settlements
    end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
    
    chunk_size = 100
    for i in range(0, len(to_update), chunk_size):
        chunk = to_update[i:i+chunk_size]
        try:
            # Disable threads to prevent SQLite lock errors
            data = yf.download(chunk, start=start_date, end=end_date, group_by='ticker', threads=False, progress=False)
            if data is None or data.empty:
                print(f"Batch {i//chunk_size + 1} returned no data.")
                continue
                
            for ticker in chunk:
                try:
                    new_data = data[ticker].dropna() if len(chunk) > 1 else data.dropna()
                    if new_data.empty: continue
                    
                    file_path = os.path.join(DATA_DIR, existing_files[ticker])
                    old_df = pd.read_csv(file_path)
                    
                    # Merge and deduplicate
                    combined = pd.concat([old_df, new_data.reset_index()])
                    # Normalize Date string to avoid dups from different formats
                    combined['Date'] = pd.to_datetime(combined['Date']).dt.strftime('%Y-%m-%d')
                    combined = combined.drop_duplicates(subset=['Date']).sort_values('Date')
                    
                    # Save
                    combined.to_csv(file_path, index=False)
                except: continue
            print(f"Synced {min(i+chunk_size, len(to_update))}/{len(to_update)} existing stocks.")
        except Exception as e:
            print(f"Error in batch update: {e}")

    # 4. Handle new listings
    new_tickers = [s for s in all_symbols if s not in existing_files]
    if new_tickers:
        print(f"Detected {len(new_tickers)} new listings. Creating initial history...")
        for ticker in new_tickers:
            try:
                # Try to get 15 years for new listings
                t_data = yf.download(ticker, period="max", interval="1d", progress=False)
                if t_data is not None and not t_data.empty:
                    t_data = t_data.dropna()
                    name = symbols_map.get(ticker, "Unknown").replace("/", "_")
                    file_path = os.path.join(DATA_DIR, f"{ticker}_{name}.csv")
                    t_data.to_csv(file_path)
                    print(f"Created record for {ticker}")
            except: continue

    print(f"--- Sync Complete ---")

if __name__ == "__main__":
    import sys
    fast = "--fast" in sys.argv
    sync_all(fast_mode=fast)
