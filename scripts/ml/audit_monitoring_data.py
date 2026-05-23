#!/Users/bookid/.hermes/.venv/bin/python
import os
import json
import glob
import pandas as pd
import duckdb
import yfinance as yf
import argparse
from datetime import datetime

# Configuration
DATA_DIR = os.path.expanduser("~/.hermes/data")
SAVE_DIR = os.path.expanduser("~/Documents/StockData_History_5Y")
DB_PATH = os.path.join(DATA_DIR, "potential_analysis.ddb")
CENTRAL_JSON = os.path.join(DATA_DIR, "central_stock_data.json")

def get_monitoring_codes():
    if not os.path.exists(CENTRAL_JSON):
        print(f"❌ 找不到核心設定檔: {CENTRAL_JSON}")
        return []
        
    try:
        with open(CENTRAL_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ 讀取核心設定檔失敗: {e}")
        return []
        
    personal = list(data.get('personal_data', {}).keys())
    group = data.get('group_codes', [])
    william = data.get('william_codes', [])
    
    # Combined unique tickers (exclude ETFs and indexes that might not have institutional flow if necessary, but we can check all)
    all_codes = sorted(list(set(personal + group + william)))
    
    # Filter out obvious non-stock indices
    all_codes = [c for c in all_codes if not c.startswith('^')]
    return all_codes

def audit_stock_data(auto_fix=False):
    codes = get_monitoring_codes()
    print("=========================================================================")
    print("  🔍 啟動「個人持股與監控個股」數據完整性審計 (EOD Audit)")
    print(f"  目標個股總量：{len(codes)} 檔")
    print("=========================================================================")
    
    results = []
    
    # Connect to DuckDB
    try:
        conn = duckdb.connect(DB_PATH)
    except Exception as e:
        print(f"⚠️ 無法連接到 DuckDB potential_analysis.ddb: {e}")
        conn = None
        
    # Get mapping for proper names
    code_to_name = {}
    mapping_path = os.path.join(DATA_DIR, "stock_mapping.json")
    if os.path.exists(mapping_path):
        try:
            with open(mapping_path, 'r', encoding='utf-8') as f:
                code_to_name = {v: k for k, v in json.load(f).items()}
        except:
            pass
            
    missing_5m_count = 0
    missing_inst_count = 0
    
    for code in codes:
        # Find matching CSV in StockData_History_5Y
        csv_pattern = os.path.join(SAVE_DIR, f"{code}.TW_*.csv")
        csv_pattern_otc = os.path.join(SAVE_DIR, f"{code}.TWO_*.csv")
        csv_files = glob.glob(csv_pattern) + glob.glob(csv_pattern_otc)
        
        has_csv = len(csv_files) > 0
        has_institutional = False
        latest_date = "N/A"
        csv_rows = 0
        
        # 1. Audit Daily & Institutional flow
        if has_csv:
            try:
                df_daily = pd.read_csv(csv_files[0])
                csv_rows = len(df_daily)
                if 'Date' in df_daily.columns:
                    latest_date = str(df_daily['Date'].max())
                if 'Foreign_Net' in df_daily.columns and 'Trust_Net' in df_daily.columns:
                    # Check if last row has non-null net buys
                    last_row = df_daily.iloc[-1]
                    if not pd.isna(last_row['Foreign_Net']) and not pd.isna(last_row['Trust_Net']):
                        has_institutional = True
            except:
                pass
                
        # Check DuckDB status
        in_duckdb = False
        duckdb_rows = 0
        if conn and has_csv:
            try:
                res = conn.execute("SELECT count(*) FROM daily_stock_data WHERE code=?", (code,)).fetchone()
                if res and res[0] > 0:
                    in_duckdb = True
                    duckdb_rows = res[0]
            except:
                pass
                
        # 2. Audit 5m intraday data file
        path_5m = os.path.join(DATA_DIR, f"{code}_intraday_5m.csv")
        has_5m = os.path.exists(path_5m)
        m_rows_5m = 0
        
        if has_5m:
            try:
                df_5m = pd.read_csv(path_5m)
                m_rows_5m = len(df_5m)
            except:
                pass
                
        name = code_to_name.get(code, "未知名稱")
        
        # Increment missing counts
        if not has_5m:
            missing_5m_count += 1
        if not has_institutional:
            missing_inst_count += 1
            
        results.append({
            "code": code,
            "name": name,
            "has_csv": has_csv,
            "has_inst": has_institutional,
            "in_db": in_duckdb,
            "db_rows": duckdb_rows,
            "latest_date": latest_date,
            "has_5m": has_5m,
            "rows_5m": m_rows_5m,
            "path_5m": path_5m
        })
        
    if conn:
        conn.close()
        
    # Render Report Table
    print("\n📋 審計詳細報告表：")
    print(f"{'股號':<6} | {'股名':<10} | {'歷史CSV':<7} | {'三大法人':<7} | {'DuckDB':<6} | {'最新交易日':<10} | {'5分K線 (60D)':<12} | {'5m記錄數':<8}")
    print("-" * 96)
    
    for r in results:
        csv_status = "OK" if r['has_csv'] else "無"
        inst_status = "OK" if r['has_inst'] else "缺失"
        db_status = f"OK({r['db_rows']})" if r['in_db'] else "無"
        m5_status = "OK" if r['has_5m'] else "缺失"
        print(f"{r['code']:<8} | {r['name']:<10} | {csv_status:<9} | {inst_status:<11} | {db_status:<8} | {r['latest_date']:<10} | {m5_status:<16} | {r['rows_5m']:<8}")
        
    print("-" * 96)
    print(f"📊 審計摘要：")
    print(f"  - 三大法人資訊缺失：{missing_inst_count} / {len(codes)} 檔")
    print(f"  - 五分高頻資料缺失：{missing_5m_count} / {len(codes)} 檔")
    print("=========================================================================")
    
    # 3. Auto Fix logic for missing 5m data (Download 60 days of 5m data headlessly)
    if auto_fix and missing_5m_count > 0:
        print("\n🚀 啟動自動修復機制 (Auto-Fix) 補全缺失的 5 分鐘高頻資料...")
        fixed_count = 0
        for r in results:
            if not r['has_5m']:
                code = r['code']
                # Determine suffix
                # We can try .TW and fallback to .TWO
                suffixes = [".TW", ".TWO"]
                success = False
                for suffix in suffixes:
                    ticker = f"{code}{suffix}"
                    print(f"  [下載] 正在獲取 {r['name']} ({ticker}) 60 天 5m K 線資料...")
                    try:
                        df_dl = yf.download(ticker, period="60d", interval="5m", progress=False)
                        if not df_dl.empty:
                            if isinstance(df_dl.columns, pd.MultiIndex):
                                df_dl.columns = df_dl.columns.get_level_values(0)
                            df_dl = df_dl[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
                            df_dl = df_dl.reset_index()
                            df_dl.rename(columns={'Datetime': 'timestamp'}, inplace=True)
                            
                            df_dl.to_csv(r['path_5m'], index=False)
                            print(f"  ✓ 成功儲存 {len(df_dl)} 筆高頻資料至 {r['path_5m']}")
                            success = True
                            fixed_count += 1
                            break
                    except Exception as e:
                        pass
                if not success:
                    print(f"  ❌ 無法為 {r['name']} ({code}) 下載 5m 資料。")
        print(f"\n✓ 自動修復完畢：成功補齊 {fixed_count} 檔個股的 5m 歷史高頻資料！")
        
    print("=========================================================================")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit stock dataset.")
    parser.add_argument("--fix", action="store_true", help="Auto-fix missing 5-minute datasets.")
    args = parser.parse_args()
    
    audit_stock_data(auto_fix=args.fix)
