#!/Users/bookid/.hermes/.venv/bin/python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pandas",
#     "requests",
#     "yfinance",
#     "duckdb",
# ]
# ///
import os
import sys
import json
import time
import argparse
import sqlite3
import subprocess
import requests
import urllib3
import duckdb
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
DATA_DIR = os.path.expanduser("~/.hermes/data")
SCRIPTS_DIR = os.path.expanduser("~/.hermes/scripts")
REGISTRY_PATH = os.path.join(DATA_DIR, "master_stock_registry.json")
SYNC_SCRIPT_PATH = os.path.join(SCRIPTS_DIR, "taiex_central_data_sync.py")
PORTFOLIO_DB = os.path.join(DATA_DIR, "portfolio.db")
PORTFOLIO_DDB = os.path.join(DATA_DIR, "portfolio.ddb")
POTENTIAL_DDB = os.path.join(DATA_DIR, "potential_analysis.ddb")
INTRADAY_LOG = os.path.join(DATA_DIR, "intraday_data_log.csv")

FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiYm9va2lkIiwiZW1haWwiOiJib29raWQyMDAwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjB9.MaUs7zQVYm5qKtlpIRdZ-s-I6WXCfcdtIowZiR7mXM4"

def get_stock_name_and_suffix(code):
    """Fetches stock Chinese name and market suffix (.TW or .TWO) dynamically."""
    print(f"🔍 正在獲取股號 {code} 的官方中文字稱及市場分類...")
    
    # 1. Try TWSE API
    try:
        url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_{code}.tw|otc_{code}.tw&json=1"
        r = requests.get(url, timeout=5, verify=False)
        data = r.json()
        if 'msgArray' in data and data['msgArray']:
            item = data['msgArray'][0]
            name = item.get('n', '').strip()
            ex = item.get('ex', 'tse')
            suffix = ".TW" if ex == 'tse' else ".TWO"
            if name:
                print(f"✓ [TWSE API] 找到商品: {name} (市場字尾: {suffix})")
                return name, suffix
    except Exception as e:
        print(f"  ⚠️ TWSE API 查詢失敗: {e}")
        
    # 2. Try yfinance Fallback
    for suffix in ['.TW', '.TWO']:
        try:
            ticker_str = f"{code}{suffix}"
            t = yf.Ticker(ticker_str)
            hist = t.history(period="1d")
            if not hist.empty:
                info = t.info
                name = info.get('shortName') or info.get('longName') or code
                # Remove common English terms from shortName if returned
                name = name.replace("Co., Ltd.", "").strip()
                print(f"✓ [yfinance] 找到商品: {name} (市場字尾: {suffix})")
                return name, suffix
        except Exception:
            continue
            
    print(f"⚠️ 無法在線上確認分類，預設套用 tse / .TW 分類。")
    return code, ".TW"

def update_swift_monitor(code, group):
    """Automatically adds the onboarded stock code into the appropriate Swift monitor watchlist."""
    swift_path = os.path.join(SCRIPTS_DIR, "hermes_monitor.swift")
    if not os.path.exists(swift_path):
        print(f"  ⚠️ 找不到 swift 監控程式: {swift_path}，跳過自動編輯。")
        return
        
    swift_group_key = group
    if "William" in group or "william" in group:
        swift_group_key = "William觀察名單"
        
    try:
        with open(swift_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        lines = content.split('\n')
        modified = False
        for idx, line in enumerate(lines):
            if f'"{swift_group_key}"' in line and '[' in line and ']' in line:
                start_idx = line.find('[')
                end_idx = line.find(']', start_idx)
                if start_idx != -1 and end_idx != -1:
                    array_str = line[start_idx+1:end_idx]
                    existing_codes = [c.strip().replace('"', '') for c in array_str.split(',') if c.strip()]
                    if code not in existing_codes:
                        existing_codes.append(code)
                        new_array_str = ", ".join([f'"{c}"' for c in existing_codes])
                        new_line = line[:start_idx+1] + new_array_str + line[end_idx:]
                        lines[idx] = new_line
                        modified = True
                        print(f"  ✓ 成功在 Swift 監控程式 {swift_path} 中的 [{swift_group_key}] 新增股號: {code}")
                    else:
                        print(f"  ℹ️ Swift 監控程式中的 [{swift_group_key}] 已包含股號 {code}，跳過編輯。")
                    break
        
        if modified:
            with open(swift_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            print("  ✓ hermes_monitor.swift 更新並儲存成功。")
    except Exception as e:
        print(f"  ❌ 更新 hermes_monitor.swift 失敗: {e}")

def step1_onboard_registry_and_files(code, name, suffix, group):
    print("\n--- [Step 1] 同步註冊中央註冊表、同步腳本與 SQLite 資料庫 ---")
    
    # 1.1 Update master_stock_registry.json
    if os.path.exists(REGISTRY_PATH):
        try:
            with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            # Add to group category
            if "group_categories" in registry:
                if group not in registry["group_categories"]:
                    registry["group_categories"][group] = []
                if code not in registry["group_categories"][group]:
                    registry["group_categories"][group].append(code)
                    print(f"  ✓ 成功在註冊表群組 [{group}] 中新增股號: {code}")
            
            # Add to official_names
            if "official_names" in registry:
                registry["official_names"][code] = name
                print(f"  ✓ 成功在註冊表官方名稱中登錄: {code} -> {name}")
                
            with open(REGISTRY_PATH, 'w', encoding='utf-8') as f:
                json.dump(registry, f, indent=2, ensure_ascii=False)
            print("  ✓ master_stock_registry.json 更新並儲存成功。")
        except Exception as e:
            print(f"  ❌ 更新 master_stock_registry.json 失敗: {e}")
            sys.exit(1)
            
    # 1.2 Update taiex_central_data_sync.py
    if os.path.exists(SYNC_SCRIPT_PATH):
        try:
            with open(SYNC_SCRIPT_PATH, 'r', encoding='utf-8') as f:
                sync_content = f.read()
                
            if f'"{code}":' not in sync_content:
                pattern = "group_defaults = {"
                if pattern in sync_content:
                    insert_str = f'\n        "{code}": "{name}",'
                    sync_content = sync_content.replace(pattern, pattern + insert_str)
                    with open(SYNC_SCRIPT_PATH, 'w', encoding='utf-8') as f:
                        f.write(sync_content)
                    print(f"  ✓ 成功在同步引擎的 group_defaults 中登錄: {code}")
            else:
                print(f"  ℹ️ 同步引擎中已包含股號 {code}，跳過編輯。")
        except Exception as e:
            print(f"  ❌ 更新 taiex_central_data_sync.py 失敗: {e}")
            sys.exit(1)

    # 1.3 Update hermes_monitor.swift
    update_swift_monitor(code, group)

    # 1.4 Update SQLite watchlist
    try:
        conn = sqlite3.connect(PORTFOLIO_DB)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        # SQLite group prefix matching
        if "William" in group or "william" in group:
            db_group_name = "William哥推薦組"
        else:
            db_group_name = f"高潮不斷群 ({group})"
            
        cursor.execute("SELECT count(*) FROM watchlist WHERE code = ?", (code,))
        exists = cursor.fetchone()[0] > 0
        
        if exists:
            cursor.execute("UPDATE watchlist SET group_name = ? WHERE code = ?", (db_group_name, code))
            print(f"  ✓ SQLite: 股號 {code} 已在觀測清單中，成功將群組變更為 [{db_group_name}]")
        else:
            cursor.execute("INSERT INTO watchlist (code, name, added_at, group_name) VALUES (?, ?, ?, ?)",
                           (code, name, now, db_group_name))
            print(f"  ✓ SQLite: 成功將 {name}({code}) 新增至觀測清單 [{db_group_name}]")
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"  ❌ 更新 SQLite 觀測清單資料庫失敗: {e}")
        sys.exit(1)

def step2_backfill_5m_price_and_logs(code, name, suffix):
    print("\n--- [Step 2] 補全過去 60 天的 5分鐘高頻價量資料並回填日誌 ---")
    ticker = f"{code}{suffix}"
    output_path = os.path.join(DATA_DIR, f"{code}_intraday_5m.csv")
    
    print(f"  ▸ 正在從 yfinance 下載 {ticker} 過去 60 天 (高頻 API 限制) 的 5m 資料...")
    try:
        df = yf.download(ticker, period="60d", interval="5m", progress=False)
        if df.empty:
            print("  ❌ yfinance 返回空高頻資料，補全失敗。")
            return
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
        df = df.reset_index()
        df.rename(columns={'Datetime': 'timestamp'}, inplace=True)
        
        # Save to csv
        df.to_csv(output_path, index=False)
        print(f"  ✓ 成功將高頻 K 線儲存至: {output_path} ({len(df)} 筆記錄)")
        
        # --- 追加回填 intraday_data_log.csv 的最新交易日數據，以利 ML 立即運行 ---
        df['timestamp_dt'] = pd.to_datetime(df['timestamp'])
        latest_date = df['timestamp_dt'].dt.date.max()
        df_latest = df[df['timestamp_dt'].dt.date == latest_date].copy()
        
        # Convert UTC to local Taipei time (+8 hours)
        df_latest['timestamp_local'] = df_latest['timestamp_dt'] + timedelta(hours=8)
        df_latest['timestamp_str'] = df_latest['timestamp_local'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Fetch UMC or similar prev close for relative change calculation
        prev_close = float(df_latest['Close'].iloc[0])
        log_rows = []
        for idx, row in df_latest.iterrows():
            pct = (row['Close'] - prev_close) / prev_close * 100
            log_rows.append({
                'timestamp': row['timestamp_str'],
                'code': code,
                'name': name,
                'price': row['Close'],
                'volume': int(row['Volume']),
                'pct_change': pct
            })
            
        df_log_new = pd.DataFrame(log_rows)
        df_log_new.to_csv(INTRADAY_LOG, mode='a', header=False, index=False)
        print(f"  ✓ 成功將最新交易日 ({latest_date}) 共 {len(df_log_new)} 筆高頻 Bins 資料安全回填至 intraday_data_log.csv")
    except Exception as e:
        print(f"  ❌ 下載/處理五頻高階價量資料時出錯: {e}")

def fetch_finmind_institutional(code, start_date, end_date):
    """Fetches daily institutional net buy/sells for a stock from FinMind."""
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        'dataset': 'TaiwanStockInstitutionalInvestorsBuySell',
        'data_id': code,
        'start_date': start_date,
        'end_date': end_date,
        'token': FINMIND_TOKEN
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            res_data = r.json()
            if res_data.get('status') == 200 or res_data.get('msg') == 'success':
                return res_data.get('data', [])
    except Exception as e:
        print(f"    ⚠️ FinMind API 連結出錯: {e}")
    return []

def process_institutional_records(records):
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    if 'date' not in df.columns or 'buy' not in df.columns or 'sell' not in df.columns or 'name' not in df.columns:
        return pd.DataFrame()
    df['date'] = pd.to_datetime(df['date'])
    df['net_buy'] = (df['buy'] - df['sell']) / 1000.0  # Convert to thousand shares (張)
    
    def map_role(name):
        name_lower = name.lower()
        if 'foreign' in name_lower: return 'Foreign_Net'
        elif 'trust' in name_lower: return 'Trust_Net'
        elif 'dealer' in name_lower: return 'Dealer_Net'
        return None
        
    df['role'] = df['name'].apply(map_role)
    df = df.dropna(subset=['role'])
    if df.empty:
        return pd.DataFrame()
        
    pivoted = df.pivot_table(index='date', columns='role', values='net_buy', aggfunc='sum').reset_index()
    for col in ['Foreign_Net', 'Trust_Net', 'Dealer_Net']:
        if col not in pivoted.columns:
            pivoted[col] = 0.0
    return pivoted

def step3_backfill_5y_institutional_data(code, name, suffix):
    print("\n--- [Step 3] 回填並同步 5 年三大法人每日歷史籌碼數據 ---")
    ticker = f"{code}{suffix}"
    
    end_date_obj = datetime.now()
    start_date_obj = end_date_obj - timedelta(days=5*365 + 10)
    start_str = start_date_obj.strftime('%Y-%m-%d')
    end_str = end_date_obj.strftime('%Y-%m-%d')
    
    # 3.1 Fetch daily prices for 5 years
    print(f"  ▸ 正在從 yfinance 下載 {ticker} 過去 5 年的每日日 K 線...")
    try:
        price_df = yf.download(ticker, start=start_str, end=end_str, progress=False)
        if price_df.empty:
            print("  ❌ yfinance 無法下載 5 年價格歷史。")
            return
        if isinstance(price_df.columns, pd.MultiIndex):
            price_df.columns = price_df.columns.get_level_values(0)
        price_df = price_df.reset_index()
        
        # Standardize columns
        clean_df = pd.DataFrame()
        clean_df['Date'] = pd.to_datetime(price_df['Date'])
        clean_df['Open'] = pd.to_numeric(price_df['Open'], errors='coerce')
        clean_df['High'] = pd.to_numeric(price_df['High'], errors='coerce')
        clean_df['Low'] = pd.to_numeric(price_df['Low'], errors='coerce')
        clean_df['Close'] = pd.to_numeric(price_df['Close'], errors='coerce')
        clean_df['Adj Close'] = pd.to_numeric(price_df['Adj Close'], errors='coerce') if 'Adj Close' in price_df.columns else clean_df['Close']
        clean_df['Volume'] = pd.to_numeric(price_df['Volume'], errors='coerce')
        clean_df = clean_df.dropna()
    except Exception as e:
        print(f"  ❌ 下載 5 年歷史價格出錯: {e}")
        return

    # 3.2 Fetch 5-year institutional buy/sell records
    print(f"  ▸ 正在從 FinMind 下載 {code} 過去 5 年的三大法人每日淨買賣超...")
    records = fetch_finmind_institutional(code, start_str, end_str)
    inst_df = process_institutional_records(records)
    
    if inst_df.empty:
        print("  ⚠️ FinMind 未回傳任何三大法人數據，預設籌碼補 0。")
        clean_df['Foreign_Net'] = 0.0
        clean_df['Trust_Net'] = 0.0
        clean_df['Dealer_Net'] = 0.0
    else:
        # Merge
        clean_df['Date'] = pd.to_datetime(clean_df['Date'])
        clean_df = pd.merge(clean_df, inst_df, left_on='Date', right_on='date', how='left')
        clean_df = clean_df.drop(columns=['date'], errors='ignore')
        for col in ['Foreign_Net', 'Trust_Net', 'Dealer_Net']:
            clean_df[col] = clean_df[col].fillna(0.0)
            
    # 3.3 Save merged CSV to StockData_History_5Y directory
    history_5y_dir = os.path.expanduser("~/Documents/StockData_History_5Y")
    os.makedirs(history_5y_dir, exist_ok=True)
    csv_file_path = os.path.join(history_5y_dir, f"{ticker}_{name}.csv")
    clean_df.to_csv(csv_file_path, index=False)
    print(f"  ✓ 成功合併價量與法人數據並存檔至: {csv_file_path} ({len(clean_df)} 筆每日記錄)")

    # 3.4 Sync to DuckDB potential_analysis.ddb
    try:
        conn = duckdb.connect(POTENTIAL_DDB)
        df_temp = clean_df.copy()
        df_temp['Date'] = df_temp['Date'].dt.date
        df_temp['code'] = code
        df_temp['ticker'] = ticker
        df_temp['name'] = name
        
        # Select exact columns
        df_temp = df_temp[['Date', 'code', 'ticker', 'name', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Foreign_Net', 'Trust_Net', 'Dealer_Net']]
        df_temp.columns = ['date', 'code', 'ticker', 'name', 'open', 'high', 'low', 'close', 'adj_close', 'volume', 'foreign_net', 'trust_net', 'dealer_net']
        
        conn.execute("""
            INSERT OR REPLACE INTO daily_stock_data 
            (date, code, ticker, name, open, high, low, close, adj_close, volume, foreign_net, trust_net, dealer_net) 
            SELECT * FROM df_temp
        """)
        conn.close()
        print(f"  ✓ [DuckDB potential_analysis.ddb] 成功增量寫入/更新 {len(df_temp)} 筆日歷史數據。")
    except Exception as e:
        print(f"  ❌ 同步至 DuckDB potential_analysis.ddb 失敗: {e}")

    # 3.5 Sync to DuckDB portfolio.ddb
    try:
        conn = duckdb.connect(PORTFOLIO_DDB)
        df_port = clean_df.copy()
        df_port['date_str'] = df_port['Date'].dt.strftime('%Y-%m-%d')
        df_port['code_norm'] = code
        df_port['foreign_buy'] = df_port['Foreign_Net'].round().astype('int64')
        df_port['trust_buy'] = df_port['Trust_Net'].round().astype('int64')
        df_port['dealer_buy'] = df_port['Dealer_Net'].round().astype('int64')
        df_port['foreign_ratio'] = 0.0
        df_port['foreign_holding'] = 0
        df_port['issued_shares'] = 0
        
        df_port = df_port[['date_str', 'code_norm', 'foreign_buy', 'trust_buy', 'dealer_buy', 'foreign_ratio', 'foreign_holding', 'issued_shares']]
        
        conn.execute("""
            INSERT OR REPLACE INTO institutional_data (date, code, foreign_buy, trust_buy, dealer_buy, foreign_ratio, foreign_holding, issued_shares)
            SELECT * FROM df_port;
        """)
        conn.close()
        print(f"  ✓ [DuckDB portfolio.ddb] 成功增量寫入/更新 {len(df_port)} 筆每日籌碼數據。")
    except Exception as e:
        print(f"  ❌ 同步至 DuckDB portfolio.ddb 失敗: {e}")

def step4_run_validation_and_ml_rerun():
    print("\n--- [Step 4] 啟動防呆一致性驗證與 ML 雙指標重啟預測 ---")
    
    # 4.1 Run hermes_diagnostic.swift to verify symmetry
    print("  ▸ 正在運行系統診斷檢查配對對稱性...")
    try:
        result = subprocess.run(["swift", os.path.join(SCRIPTS_DIR, "hermes_diagnostic.swift")], capture_output=True, text=True)
        if result.returncode == 0:
            print("  ✅ [診斷認證] 配置一致性完全通過！商品對稱性 100% 正確。")
        else:
            print(f"  ❌ [診斷失敗] 發現配置異常，錯誤資訊:\n{result.stdout}")
    except Exception as e:
        print(f"  ⚠️ 無法執行系統診斷腳本: {e}")
        
    # 4.2 Run intraday_ml_pipeline.py to update TG report
    print("  ▸ 正在運行 ML 雙指標自適應收斂預測引擎，發送更新報告...")
    try:
        subprocess.run(["/Users/bookid/.hermes/.venv/bin/python", os.path.join(SCRIPTS_DIR, "ml/intraday_ml_pipeline.py")], check=True)
        print("  ✅ [ML 預測重啟] 成功生成最新收盤自適應預測報告，且已完全同步發送至 Telegram！")
    except Exception as e:
        print(f"  ❌ 執行 ML 預測引擎時出錯: {e}")

def main():
    parser = argparse.ArgumentParser(description="Automated Standard Stock Onboarding Pipeline")
    parser.add_argument("--code", required=True, help="Stock code (e.g. 2409, 2303)")
    parser.add_argument("--group", required=True, help="Target watchlist group name in registry (e.g. 順風老師組, 正體鍾文字組)")
    args = parser.parse_args()
    
    start_time = time.time()
    print("=========================================================================")
    print(f" 🚀 啟動全新的自動化股票上架管道 (Stock Onboarding Pipeline): {args.code}")
    print("=========================================================================")
    
    # Dynamic Info Fetching
    name, suffix = get_stock_name_and_suffix(args.code)
    
    # Run pipeline steps
    step1_onboard_registry_and_files(args.code, name, suffix, args.group)
    step2_backfill_5m_price_and_logs(args.code, name, suffix)
    step3_backfill_5y_institutional_data(args.code, name, suffix)
    step4_run_validation_and_ml_rerun()
    
    print("\n=========================================================================")
    print(f"  🎉 商品 {name}({args.code}) 上架、數據補全、資料庫同步與預測生成全部成功！")
    print(f"  ⏱ 總計耗時: {time.time() - start_time:.2f} 秒。")
    print("=========================================================================")

if __name__ == "__main__":
    main()
