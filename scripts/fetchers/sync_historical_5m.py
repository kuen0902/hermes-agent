#!/Users/bookid/.hermes/.venv/bin/python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pandas",
#     "yfinance",
#     "requests",
# ]
# ///
import os
import sys
import glob
import sqlite3
import json
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime

# Configuration
DATA_DIR = os.path.expanduser("~/.hermes/data")
DB_PATH = os.path.join(DATA_DIR, "portfolio.db")
REGISTRY_PATH = os.path.join(DATA_DIR, "master_stock_registry.json")

def get_stock_suffix(code):
    """Offline method using local files and DuckDB to determine the suffix reliably and instantly."""
    # 1. Check existing CSV files in 5Y history directory
    save_5y_dir = os.path.expanduser("~/Documents/StockData_History_5Y")
    if os.path.exists(save_5y_dir):
        files = glob.glob(os.path.join(save_5y_dir, f"{code}.TW_*.csv"))
        if files:
            return ".TW"
        files_two = glob.glob(os.path.join(save_5y_dir, f"{code}.TWO_*.csv"))
        if files_two:
            return ".TWO"
            
    # 2. Query DuckDB potential_analysis.ddb for the ticker
    potential_ddb = os.path.join(DATA_DIR, "potential_analysis.ddb")
    if os.path.exists(potential_ddb):
        try:
            import duckdb
            conn = duckdb.connect(potential_ddb)
            row = conn.execute("SELECT DISTINCT ticker FROM daily_stock_data WHERE code = ?", (code,)).fetchone()
            conn.close()
            if row and row[0]:
                ticker = str(row[0])
                if ticker.endswith(".TWO"):
                    return ".TWO"
                elif ticker.endswith(".TW"):
                    return ".TW"
        except:
            pass
            
    # 3. Registry fallback or standard OTC list check
    otc_set = {"3105", "3211", "3260", "3709", "4543", "4925", "5289", "5347", "6125", "6147", "6290", "6510", "6877", "7815", "7843", "7828", "8299"}
    if code in otc_set:
        return ".TWO"
        
    return ".TW"

def load_historically_active_codes():
    """Compiles all historically active stock codes in the system."""
    codes = set()
    
    # 1. Scan for existing {code}_intraday_5m.csv files
    files = glob.glob(os.path.join(DATA_DIR, "*_intraday_5m.csv"))
    for f in files:
        basename = os.path.basename(f)
        code = basename.split('_')[0]
        if code.isdigit():
            codes.add(code)
            
    # 2. Read SQLite current holdings and watchlist
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Watchlist
            cursor.execute("SELECT code FROM watchlist")
            for r in cursor.fetchall():
                codes.add(str(r[0]).strip())
                
            # Holdings
            cursor.execute("SELECT code FROM current_holdings")
            for r in cursor.fetchall():
                codes.add(str(r[0]).strip())
                
            conn.close()
        except Exception as e:
            print(f"⚠️ 無法讀取 SQLite 歷史股號: {e}")
            
    # 3. Read registry official names
    if os.path.exists(REGISTRY_PATH):
        try:
            with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            for code in registry.get("official_names", {}).keys():
                if code.isdigit():
                    codes.add(code)
        except:
            pass
            
    return sorted(list(codes))

def sync_5m_data():
    print("=========================================================================")
    print(f" ⏳ 啟動「歷史股票」5分鐘高頻價量數據每日同步常式 [{datetime.now().strftime('%Y-%m-%d %H:%M')}]")
    print("=========================================================================")
    
    active_codes = load_historically_active_codes()
    print(f"  偵測到系統歷史累積股票共 {len(active_codes)} 檔。正在逐一更新 5m K 線檔案...")
    
    success_count = 0
    fail_count = 0
    
    for idx, code in enumerate(active_codes, 1):
        suffix = get_stock_suffix(code)
        ticker = f"{code}{suffix}"
        output_path = os.path.join(DATA_DIR, f"{code}_intraday_5m.csv")
        
        print(f"  [{idx}/{len(active_codes)}] 正在同步 {ticker} 過去 60 天的 5m 價量...")
        try:
            df = yf.download(ticker, period="60d", interval="5m", progress=False)
            if df.empty:
                print(f"    ❌ {ticker} yfinance 返回空資料。")
                fail_count += 1
                continue
                
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
            df = df.reset_index()
            df.rename(columns={'Datetime': 'timestamp'}, inplace=True)
            
            # Save
            df.to_csv(output_path, index=False)
            print(f"    ✓ 成功更新 5m 高頻資料檔案: {output_path} ({len(df)} 筆)")
            success_count += 1
        except Exception as e:
            print(f"    ❌ 更新 {ticker} 失敗: {e}")
            fail_count += 1
            
    print("=========================================================================")
    print(f"  🎉 歷史股票 5m 同步完成！ 成功：{success_count} 檔 | 失敗：{fail_count} 檔")
    print("=========================================================================")

if __name__ == "__main__":
    sync_5m_data()
