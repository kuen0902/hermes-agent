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


def get_previous_trading_day():
    """Returns the ISO string YYYY-MM-DD of the previous trading day (Mon-Fri) excluding holidays."""
    try:
        import yfinance as yf
        ticker = yf.Ticker("0050.TW")
        hist = ticker.history(period="5d")
        if not hist.empty:
            latest_trading_day = hist.index[-1].strftime('%Y-%m-%d')
            return latest_trading_day
    except Exception as e:
        print(f"Error querying yfinance 0050.TW for latest trading day: {e}")
        
    # Fallback to local weekday math if network check fails
    today = datetime.now()
    offset = 1
    wd = today.weekday()
    if wd == 0:    # Monday
        offset = 3
    elif wd == 6:  # Sunday
        offset = 2
    elif wd == 5:  # Saturday
        offset = 1
    prev = today - timedelta(days=offset)
    return prev.strftime('%Y-%m-%d')

def get_history_from_duckdb(ticker):
    """Attempts to fetch historical daily data for a ticker from DuckDB potential_analysis.ddb"""
    db_path = os.path.expanduser("~/.hermes/data/potential_analysis.ddb")
    if not os.path.exists(db_path):
        return None
    try:
        import duckdb
        conn = duckdb.connect(db_path)
        
        # Try full_daily_prices table first (15-year history)
        query = "SELECT date, open, high, low, close, adj_close, volume FROM full_daily_prices WHERE ticker = ? ORDER BY date"
        df = conn.execute(query, (ticker,)).fetchdf()
        
        # If empty, try daily_stock_data table (5-year history)
        if df.empty:
            query = "SELECT date, open, high, low, close, adj_close, volume FROM daily_stock_data WHERE ticker = ? ORDER BY date"
            df = conn.execute(query, (ticker,)).fetchdf()
            
        conn.close()
        if not df.empty:
            df.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.set_index('Date')
            return df
    except Exception as e:
        print(f"Error fetching from DuckDB for {ticker}: {e}")
    return None

def fill_institutional_data_and_sync_to_duckdb(ticker, df, symbols_map):
    """Fills missing institutional net buys in the DataFrame and writes/updates to DuckDB potential_analysis.ddb"""
    inst_ddb_path = os.path.expanduser("~/.hermes/data/portfolio.ddb")
    potential_ddb_path = os.path.expanduser("~/.hermes/data/potential_analysis.ddb")
    
    code = ticker.split('.')[0]
    
    # 1. Fill institutional columns if missing
    for col in ['Foreign_Net', 'Trust_Net', 'Dealer_Net']:
        if col not in df.columns:
            df[col] = 0.0
            
    # If there are NaN values in institutional columns, try to fill them from institutional_data table in portfolio.ddb
    nan_mask = df['Foreign_Net'].isna() | df['Trust_Net'].isna() | df['Dealer_Net'].isna()
    if nan_mask.any() and os.path.exists(inst_ddb_path):
        try:
            import duckdb
            inst_conn = duckdb.connect(inst_ddb_path)
            inst_df = inst_conn.execute(
                "SELECT date, foreign_buy, trust_buy, dealer_buy FROM institutional_data WHERE code = ?", (code,)
            ).fetchdf()
            inst_conn.close()
            
            if not inst_df.empty:
                inst_df['date'] = pd.to_datetime(inst_df['date']).dt.strftime('%Y-%m-%d')
                inst_df = inst_df.set_index('date')
                
                # Fill NaNs
                for idx, row in df[nan_mask].iterrows():
                    date_str = str(row['Date'])
                    if date_str in inst_df.index:
                        inst_row = inst_df.loc[date_str]
                        if isinstance(inst_row, pd.DataFrame):
                            inst_row = inst_row.iloc[0]
                        if pd.isna(df.loc[idx, 'Foreign_Net']):
                            df.loc[idx, 'Foreign_Net'] = float(inst_row['foreign_buy'])
                        if pd.isna(df.loc[idx, 'Trust_Net']):
                            df.loc[idx, 'Trust_Net'] = float(inst_row['trust_buy'])
                        if pd.isna(df.loc[idx, 'Dealer_Net']):
                            df.loc[idx, 'Dealer_Net'] = float(inst_row['dealer_buy'])
        except Exception as e:
            print(f"Error filling institutional data for {ticker}: {e}")
            
    # Fill remaining NaNs with 0.0
    for col in ['Foreign_Net', 'Trust_Net', 'Dealer_Net']:
        df[col] = df[col].fillna(0.0)
        
    # 2. Sync the updated DataFrame rows of the last 15 days to DuckDB potential_analysis.ddb table `daily_stock_data`
    if os.path.exists(potential_ddb_path):
        try:
            import duckdb
            name = symbols_map.get(ticker, "Unknown").replace("/", "_")
            
            df_sync = df.copy()
            df_sync['code'] = code
            df_sync['ticker'] = ticker
            df_sync['name'] = name
            
            adj_col = 'Adj Close' if 'Adj Close' in df_sync.columns else df_sync.columns[5]
            
            df_temp = df_sync[['Date', 'code', 'ticker', 'name', 'Open', 'High', 'Low', 'Close', adj_col, 'Volume', 'Foreign_Net', 'Trust_Net', 'Dealer_Net']].copy()
            df_temp.columns = ['date', 'code', 'ticker', 'name', 'open', 'high', 'low', 'close', 'adj_close', 'volume', 'foreign_net', 'trust_net', 'dealer_net']
            
            for col in ['open', 'high', 'low', 'close', 'adj_close', 'volume', 'foreign_net', 'trust_net', 'dealer_net']:
                df_temp[col] = pd.to_numeric(df_temp[col], errors='coerce').fillna(0.0)
            df_temp['volume'] = df_temp['volume'].astype('int64')
            df_temp['date'] = pd.to_datetime(df_temp['date']).dt.date
            
            df_temp = df_temp.tail(15)
            
            potential_conn = duckdb.connect(potential_ddb_path)
            potential_conn.execute("INSERT OR REPLACE INTO daily_stock_data SELECT * FROM df_temp")
            potential_conn.close()
        except Exception as e:
            print(f"Error syncing {ticker} to DuckDB daily_stock_data: {e}")
            
    return df

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

def sync_all(fast_mode=False, force=False):
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
    
    # Check if data sync for the previous trading day is already complete in DuckDB
    prev_trading_day = get_previous_trading_day()
    print(f"Target previous trading day for sync check: {prev_trading_day}")
    
    db_path = os.path.expanduser("~/.hermes/data/potential_analysis.ddb")
    if os.path.exists(db_path) and not force:
        try:
            import duckdb
            conn = duckdb.connect(db_path)
            # Query if standard benchmark stock '2330' has data for target date
            res = conn.execute("SELECT count(*) FROM daily_stock_data WHERE date = ? AND code = '2330'", (prev_trading_day,)).fetchone()
            conn.close()
            if res and res[0] > 0:
                print(f"🎉 [已完成] 前一個開盤日 ({prev_trading_day}) 的 Data Sync 已經完成！本次執行略過下載。")
                print(f"--- Sync Complete ---")
                return
        except Exception as e:
            print(f"Error checking sync completion status: {e}")

    # 2. Identify missing vs existing
    existing_files = {f.split('_')[0]: f for f in os.listdir(DATA_DIR) if f.endswith('.csv')}
    
    # 3. Process to update
    to_update_raw = [s for s in all_symbols if s in existing_files]
    
    # 智慧健康度篩選：如果已存在五年以上完整數據且已到前一交易日，則從 --force 補全名單中智慧排除，僅交給平日增量即可。
    to_update = []
    if not fast_mode:
        print("🔍 啟動全市場『智慧健康篩選』，自動排除已完美補全之個股...")
        skipped_count = 0
        for s in to_update_raw:
            file_path = os.path.join(DATA_DIR, existing_files[s])
            try:
                df = pd.read_csv(file_path)
                if len(df) >= 1000 and 'Date' in df.columns:
                    last_date = str(df['Date'].iloc[-1]).strip()
                    nan_count = df['Close'].isna().sum()
                    if last_date == prev_trading_day and nan_count == 0:
                        skipped_count += 1
                        continue # 完美補全，智慧排除！
            except:
                pass
            to_update.append(s)
        print(f"✓ 篩選完畢！全市場共有 {skipped_count} 檔個股已完美補全並成功『智慧排除』，本次僅需補全 {len(to_update)} 檔缺失個股。")
    else:
        to_update = to_update_raw
        print(f"Fast Sync: Updating {len(to_update)} core monitoring stocks...")
    
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
                    
                    # Fill institutional flows and update DuckDB
                    combined = fill_institutional_data_and_sync_to_duckdb(ticker, combined, symbols_map)
                    
                    # Save
                    combined.to_csv(file_path, index=False)
                except Exception as e:
                    print(f"Failed to sync details for {ticker}: {e}")
                    continue
            print(f"Synced {min(i+chunk_size, len(to_update))}/{len(to_update)} existing stocks.")
        except Exception as e:
            print(f"Error in batch update: {e}")

    # 4. Handle new listings
    new_tickers = [s for s in all_symbols if s not in existing_files]
    if new_tickers:
        print(f"Detected {len(new_tickers)} new listings. Creating initial history...")
        for ticker in new_tickers:
            try:
                # 1. Try DuckDB cache first
                t_data = get_history_from_duckdb(ticker)
                if t_data is not None and not t_data.empty:
                    name = symbols_map.get(ticker, "Unknown").replace("/", "_")
                    file_path = os.path.join(DATA_DIR, f"{ticker}_{name}.csv")
                    t_data.to_csv(file_path)
                    print(f"Created record for {ticker} from DuckDB cache")
                    continue
                
                # 2. Fallback to yfinance
                print(f"Ticker {ticker} not found in DuckDB. Downloading from yfinance...")
                t_data = yf.download(ticker, period="max", interval="1d", progress=False)
                if t_data is not None and not t_data.empty:
                    t_data = t_data.dropna()
                    if 'Adj Close' not in t_data.columns and 'adj_close' in t_data.columns:
                        t_data.rename(columns={'adj_close': 'Adj Close'}, inplace=True)
                    name = symbols_map.get(ticker, "Unknown").replace("/", "_")
                    file_path = os.path.join(DATA_DIR, f"{ticker}_{name}.csv")
                    t_data.to_csv(file_path)
                    print(f"Created record for {ticker} from yfinance")
            except Exception as e:
                print(f"Failed to create record for {ticker}: {e}")
                continue

    print(f"--- Sync Complete ---")

if __name__ == "__main__":
    import sys
    fast = "--fast" in sys.argv
    force = "--force" in sys.argv
    sync_all(fast_mode=fast, force=force)
