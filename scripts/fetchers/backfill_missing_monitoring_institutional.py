#!/Users/bookid/.hermes/.venv/bin/python
import os
import json
import time
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Configuration
SAVE_DIR = os.path.expanduser("~/Documents/StockData_History_5Y")
DATA_DIR = os.path.expanduser("~/.hermes/data")
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiYm9va2lkIiwiZW1haWwiOiJib29raWQyMDAwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjB9.MaUs7zQVYm5qKtlpIRdZ-s-I6WXCfcdtIowZiR7mXM4"

MISSING_STOCKS = [
    {"code": "00965", "name": "元大航太防衛科技", "suffix": ".TW"},
    {"code": "00981A", "name": "主動統一台股增長", "suffix": ".TW"},
    {"code": "4543", "name": "萬在", "suffix": ".TWO"},
    {"code": "4925", "name": "智微", "suffix": ".TWO"},
    {"code": "6125", "name": "廣運", "suffix": ".TWO"},  # 修正為 .TWO 上櫃
    {"code": "7828", "name": "創新服務", "suffix": ".TWO"}
]

def fetch_institutional_data_for_ticker(ticker, start_date, end_date):
    url = "https://api.finmindtrade.com/api/v4/data"
    stock_id = ticker.split('.')[0]
    
    params = {
        'dataset': 'TaiwanStockInstitutionalInvestorsBuySell',
        'data_id': stock_id,
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
        print(f"  ⚠️ Network error for {ticker}: {e}")
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
        
    pivoted = df.pivot_table(index='date', columns='role', values='net_buy', aggfunc='sum').reset_index()
    for col in ['Foreign_Net', 'Trust_Net', 'Dealer_Net']:
        if col not in pivoted.columns:
            pivoted[col] = 0.0
    return pivoted

def backfill():
    print("=========================================================================")
    print("  🚀 啟動 6 檔缺失三大法人資訊個股之補全與 CSV 資料重構")
    print("=========================================================================")
    
    end_date_obj = datetime.now()
    start_date_obj = end_date_obj - timedelta(days=5*365 + 10)
    start_str = start_date_obj.strftime('%Y-%m-%d')
    end_str = end_date_obj.strftime('%Y-%m-%d')
    
    os.makedirs(SAVE_DIR, exist_ok=True)
    
    for s in MISSING_STOCKS:
        code = s['code']
        name = s['name']
        ticker = f"{code}{s['suffix']}"
        file_path = os.path.join(SAVE_DIR, f"{ticker}_{name}.csv")
        
        print(f"\n[處理] {ticker} ({name}) ...")
        
        # Step 1: Download 5-year Daily price history if missing or force rebuild
        print(f"  ▸ 正在從 yfinance 下載 5 年日 K 線...")
        try:
            price_df = yf.download(ticker, start=start_str, end=end_str, progress=False)
            if price_df.empty:
                print(f"  ❌ yfinance 無法下載 {ticker} 的歷史日 K 線。")
                continue
            if isinstance(price_df.columns, pd.MultiIndex):
                price_df.columns = price_df.columns.get_level_values(0)
            
            price_df = price_df.reset_index()
            
            # Dynamically extract available columns
            cols = price_df.columns.tolist()
            date_col = next((c for c in cols if 'date' in c.lower()), None)
            open_col = next((c for c in cols if 'open' in c.lower()), None)
            high_col = next((c for c in cols if 'high' in c.lower()), None)
            low_col = next((c for c in cols if 'low' in c.lower()), None)
            close_col = next((c for c in cols if 'close' in c.lower() and 'adj' not in c.lower()), None)
            adj_col = next((c for c in cols if 'adj' in c.lower()), None)
            vol_col = next((c for c in cols if 'vol' in c.lower()), None)
            
            if not (date_col and open_col and high_col and low_col and close_col and vol_col):
                print(f"  ❌ 欄位結構不完整: {cols}")
                continue
                
            clean_df = pd.DataFrame()
            clean_df['Date'] = pd.to_datetime(price_df[date_col])
            clean_df['Open'] = pd.to_numeric(price_df[open_col], errors='coerce')
            clean_df['High'] = pd.to_numeric(price_df[high_col], errors='coerce')
            clean_df['Low'] = pd.to_numeric(price_df[low_col], errors='coerce')
            clean_df['Close'] = pd.to_numeric(price_df[close_col], errors='coerce')
            clean_df['Adj Close'] = pd.to_numeric(price_df[adj_col], errors='coerce') if adj_col else clean_df['Close']
            clean_df['Volume'] = pd.to_numeric(price_df[vol_col], errors='coerce')
            
            clean_df = clean_df.dropna().copy()
        except Exception as e:
            print(f"  ❌ yfinance 下載出錯: {e}")
            continue
            
        # Step 2: Download 5-year Institutional flow
        print(f"  ▸ 正在從 FinMind 下載 5 年三大法人每日淨買超...")
        records = fetch_institutional_data_for_ticker(ticker, start_str, end_str)
        inst_df = process_institutional_records(records)
        
        if inst_df.empty:
            print(f"  ⚠️ FinMind 未回傳有效三大法人資料，僅保留價量。")
            clean_df['Foreign_Net'] = 0.0
            clean_df['Trust_Net'] = 0.0
            clean_df['Dealer_Net'] = 0.0
            clean_df.to_csv(file_path, index=False)
            print(f"  ✓ 成功合併並儲存至: {file_path} (僅價量 / {len(clean_df)} 筆記錄)")
        else:
            # Step 3: Merge and Save
            clean_df['Date'] = pd.to_datetime(clean_df['Date'])
            merged = pd.merge(clean_df, inst_df, left_on='Date', right_on='date', how='left')
            merged = merged.drop(columns=['date'], errors='ignore')
            
            # Fill NaNs with 0.0
            for col in ['Foreign_Net', 'Trust_Net', 'Dealer_Net']:
                merged[col] = merged[col].fillna(0.0)
                
            merged.to_csv(file_path, index=False)
            print(f"  ✓ 成功合併並儲存至: {file_path} (共 {len(merged)} 筆每日記錄)")
            
        time.sleep(1.0) # respect API rate limits
        
    # Step 4: Re-import to DuckDB database
    print("\n--- 啟動三大法人 DuckDB 資料庫數據同步與校準 ---")
    init_db_script = os.path.expanduser("~/.hermes/scripts/ml/init_potential_db.py")
    if os.path.exists(init_db_script):
        import subprocess
        subprocess.run(["/Users/bookid/.hermes/.venv/bin/python", init_db_script])
        print("✓ DuckDB 向量化 bulk 重新同步完成！")
        
    print("=========================================================================")

if __name__ == "__main__":
    backfill()
