#!/Users/bookid/.hermes/.venv/bin/python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pandas",
#     "yfinance",
#     "duckdb",
#     "requests",
# ]
# ///
import os
import sys
import glob
import sqlite3
import json
import time
import datetime
import duckdb
import pandas as pd
import yfinance as yf

# Configuration
DATA_DIR = os.path.expanduser("~/.hermes/data")
DB_PATH = os.path.join(DATA_DIR, "portfolio.db")
REGISTRY_PATH = os.path.join(DATA_DIR, "master_stock_registry.json")
POTENTIAL_DDB = os.path.join(DATA_DIR, "potential_analysis.ddb")

def load_all_ticker_suffixes():
    """Offline lookup for all ticker suffixes from potential_analysis.ddb daily table."""
    suffixes = {}
    if os.path.exists(POTENTIAL_DDB):
        try:
            conn = duckdb.connect(POTENTIAL_DDB)
            rows = conn.execute("SELECT DISTINCT code, ticker FROM daily_stock_data").fetchall()
            conn.close()
            for r in rows:
                code, ticker = r[0], r[1]
                if ticker.endswith(".TWO"):
                    suffixes[code] = ".TWO"
                elif ticker.endswith(".TW"):
                    suffixes[code] = ".TW"
        except Exception as e:
            print(f"⚠️ DuckDB suffix lookup failed: {e}")
            
    # Hardcoded fallbacks for popular OTC stocks
    otc_set = {"3105", "3211", "3260", "3709", "4543", "4925", "5289", "5347", "6125", "6147", "6290", "6510", "6877", "7815", "7843", "7828", "8299"}
    for code in otc_set:
        if code not in suffixes:
            suffixes[code] = ".TWO"
            
    return suffixes

def load_monitored_codes():
    """Compiles actively monitored codes (which are already updated at 15:35)."""
    codes = set()
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT code FROM watchlist")
            for r in cursor.fetchall():
                codes.add(str(r[0]).strip())
            cursor.execute("SELECT code FROM current_holdings")
            for r in cursor.fetchall():
                codes.add(str(r[0]).strip())
            conn.close()
        except:
            pass
            
    if os.path.exists(REGISTRY_PATH):
        try:
            with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            for code in registry.get("william_codes", []):
                codes.add(str(code).strip())
            group_categories = registry.get("group_categories", {})
            for grp, grp_codes in group_categories.items():
                for code in grp_codes:
                    codes.add(str(code).strip())
        except:
            pass
            
    return {c for c in codes if c.isdigit()}

def load_remaining_online_codes():
    """Loads all stock codes in registry except those already monitored."""
    monitored = load_monitored_codes()
    all_codes = set()
    official_names = {}
    
    if os.path.exists(REGISTRY_PATH):
        try:
            with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            official_names = registry.get("official_names", {})
            for code in official_names.keys():
                if code.isdigit():
                    all_codes.add(code)
        except Exception as e:
            print(f"⚠️ Failed to read registry: {e}")
            
    remaining = sorted([c for c in all_codes if c not in monitored])
    return remaining, official_names

def sync_all_online_5m():
    start_time = time.time()
    print("=========================================================================")
    print(f" 🚀 啟動「其餘在線個股」5分鐘高頻價量 DuckDB 每日增量更新 [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}]")
    print("=========================================================================")
    
    remaining_codes, official_names = load_remaining_online_codes()
    suffixes = load_all_ticker_suffixes()
    
    print(f"  偵測到監控個股外之「在線其餘個股」共 {len(remaining_codes)} 檔。")
    print("  正在啟動高效能批次下載 (每批 50 檔)...")
    
    success_dfs = []
    success_count = 0
    fail_count = 0
    
    # Split remaining_codes into chunks of 50
    chunk_size = 50
    chunks = [remaining_codes[i:i + chunk_size] for i in range(0, len(remaining_codes), chunk_size)]
    total_chunks = len(chunks)
    
    for chunk_idx, chunk_codes in enumerate(chunks, 1):
        chunk_tickers = []
        ticker_to_info = {}
        for code in chunk_codes:
            suffix = suffixes.get(code, ".TW")
            ticker = f"{code}{suffix}"
            name = official_names.get(code, code)
            chunk_tickers.append(ticker)
            ticker_to_info[ticker] = {"code": code, "name": name}
            
        tickers_str = " ".join(chunk_tickers)
        print(f"   ▸ [{chunk_idx}/{total_chunks}] 正在下載 {len(chunk_tickers)} 檔個股的 5m 數據...")
        
        try:
            df = yf.download(tickers_str, period="2d", interval="5m", group_by="ticker", progress=False)
            if df.empty:
                print(f"     ⚠️ 此批次下載返回空數據")
                fail_count += len(chunk_tickers)
                continue
                
            for ticker in chunk_tickers:
                code = ticker_to_info[ticker]["code"]
                name = ticker_to_info[ticker]["name"]
                
                # Extract ticker data
                if isinstance(df.columns, pd.MultiIndex):
                    if ticker in df.columns.levels[0]:
                        df_ticker = df[ticker]
                    else:
                        df_ticker = pd.DataFrame()
                else:
                    df_ticker = df if len(chunk_tickers) == 1 else pd.DataFrame()
                    
                if df_ticker.empty:
                    fail_count += 1
                    continue
                    
                # Clean and parse
                df_ticker = df_ticker[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
                if df_ticker.empty:
                    fail_count += 1
                    continue
                    
                df_ticker = df_ticker.reset_index()
                # The index column is always the first column in the reset DataFrame
                df_ticker.rename(columns={df_ticker.columns[0]: 'timestamp'}, inplace=True)
                df_ticker['timestamp'] = pd.to_datetime(df_ticker['timestamp']).dt.tz_convert('UTC').dt.strftime('%Y-%m-%d %H:%M:%S+00:00')
                
                # Add required columns
                df_ticker['code'] = code
                df_ticker['ticker'] = ticker
                df_ticker['name'] = name
                
                # Rename columns to match DuckDB schema
                df_ticker.rename(columns={
                    'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'
                }, inplace=True)
                
                df_final = df_ticker[['timestamp', 'code', 'ticker', 'name', 'open', 'high', 'low', 'close', 'volume']]
                success_dfs.append(df_final)
                success_count += 1
                
        except Exception as e:
            print(f"     ❌ 批次下載出錯: {e}")
            fail_count += len(chunk_tickers)
            
        # Respectful delay between requests
        time.sleep(0.5)
        
    # 📌 批次將當日 K 線增量寫入 DuckDB
    if success_dfs:
        print(f"\n  ⏳ 正在將 {success_count} 檔個股當日 5分增量數據批次寫入 DuckDB...")
        try:
            df_all = pd.concat(success_dfs, ignore_index=True)
            df_all['timestamp'] = pd.to_datetime(df_all['timestamp'])
            
            conn = duckdb.connect(POTENTIAL_DDB)
            conn.execute("INSERT OR REPLACE INTO kbars_5m SELECT * FROM df_all")
            conn.commit()
            conn.close()
            print(f"  ✓ [DuckDB] 當日 5m 行情批量寫入/覆蓋成功！共寫入 {len(df_all)} 條 5m K 線。")
        except Exception as e:
            print(f"  ❌ 批次寫入 DuckDB 失敗: {e}")
            
    elapsed = time.time() - start_time
    print("=========================================================================")
    print(f"  🎉 其餘在線個股 5m 更新完成！ 成功：{success_count} 檔 | 失敗：{fail_count} 檔")
    print(f"  ⏱ 總計耗時: {elapsed:.2f} 秒。")
    print("=========================================================================")

if __name__ == "__main__":
    sync_all_online_5m()
