#!/Users/bookid/.hermes/.venv/bin/python
# -*- coding: utf-8 -*-
import os
import json
import time
import datetime
import requests
import sqlite3
import duckdb
import urllib3

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATA_DIR = os.path.expanduser("~/.hermes/data")
DB_PATH = os.path.join(DATA_DIR, "portfolio.db")
DUCK_PATH = os.path.join(DATA_DIR, "potential_analysis.ddb")
CENTRAL_JSON = os.path.join(DATA_DIR, "central_stock_data.json")
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiYm9va2lkIiwiZW1haWwiOiJib29raWQyMDAwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjB9.MaUs7zQVYm5qKtlpIRdZ-s-I6WXCfcdtIowZiR7mXM4"

CORE_SYMBOLS = [
    "2330.TW", "2454.TW", "3037.TW", "2382.TW", "2327.TW",
    "8996.TW", "5289.TWO", "4966.TWO", "3583.TW", "8210.TW",
    "5347.TWO", "6510.TWO", "3211.TWO", "6290.TWO", "6669.TW",
    "1513.TW", "2049.TW", "2408.TW", "2313.TW", "6285.TW"
]

def load_target_codes():
    target_codes = set()
    for s in CORE_SYMBOLS:
        target_codes.add(s.replace(".TWO", "").replace(".TW", "").strip())
    
    # 1. 讀取 SQLite 真實持股商品
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT code FROM current_holdings")
            for row in cursor.fetchall():
                code = str(row[0]).replace(".TWO", "").replace(".TW", "").strip()
                target_codes.add(code)
            conn.close()
        except Exception as e:
            print(f"⚠️ 無法讀取持股清單: {e}")
            
    # 2. 讀取 central_stock_data.json 的監控名單
    if os.path.exists(CENTRAL_JSON):
        try:
            with open(CENTRAL_JSON, 'r', encoding='utf-8') as f:
                central_data = json.load(f)
                group_codes = central_data.get("group_codes", [])
                william_codes = central_data.get("william_codes", [])
                
                def norm_c(c_str):
                    return str(c_str).replace(".TWO", "").replace(".TW", "").strip()
                
                if isinstance(group_codes, dict):
                    for c in group_codes.keys(): target_codes.add(norm_c(c))
                elif isinstance(group_codes, list):
                    for c in group_codes: target_codes.add(norm_c(c))
                    
                if isinstance(william_codes, dict):
                    for c in william_codes.keys(): target_codes.add(norm_c(c))
                elif isinstance(william_codes, list):
                    for c in william_codes: target_codes.add(norm_c(c))
        except Exception as e:
            print(f"⚠️ 無法讀取監控清單: {e}")
            
    return sorted(list(target_codes))

def init_duck_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        # 連接 DuckDB 寫入主庫
        conn = duckdb.connect(DUCK_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monthly_revenue (
                date VARCHAR,
                code VARCHAR,
                revenue BIGINT,
                revenue_month INT,
                revenue_year INT,
                out_revenue BIGINT,
                in_revenue BIGINT,
                yoy DOUBLE,
                mom DOUBLE,
                PRIMARY KEY (date, code)
            )
        ''')
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rev_code ON monthly_revenue(code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rev_date ON monthly_revenue(date)")
        conn.commit()
        return conn
    except Exception as e:
        print(f"❌ 無法建立 DuckDB 寫入連線: {e}")
        return None

def fetch_finmind_monthly_revenue(code, start_date="2012-01-01"):
    url = "https://api.finmindtrade.com/api/v4/data"
    parameter = {
        'dataset': 'TaiwanStockMonthRevenue',
        'data_id': code,
        'start_date': start_date,
        'token': FINMIND_TOKEN
    }
    try:
        r = requests.get(url, params=parameter, timeout=15, verify=False)
        if r.status_code == 200:
            res_data = r.json()
            if res_data.get('status') == 200 or res_data.get('msg') == 'success':
                return res_data.get('data', [])
            else:
                print(f"    ❌ FinMind API 回傳錯誤: {res_data.get('msg')}")
        else:
            print(f"    ❌ HTTP 請求失敗 ({r.status_code})")
    except Exception as e:
        print(f"    ❌ 網路請求錯誤: {e}")
    return []

def main():
    print("=========================================================================")
    print(" 🚀 啟動 14 年月營收歷史數據 (2012-01-01 至今) 批次補全程式")
    print("=========================================================================")
    
    target_codes = load_target_codes()
    print(f"  過濾彙整出核心監控商品共 {len(target_codes)} 檔：{target_codes}")
    
    conn = init_duck_db()
    if conn is None:
        print("❌ 無法取得 DuckDB 寫入權限，結束程式。")
        return
        
    success_count = 0
    total_records = 0
    start_time = time.time()
    
    for idx, code in enumerate(target_codes, 1):
        print(f"  [{idx}/{len(target_codes)}] 正在從 FinMind 獲取 {code} 14 年月營收...")
        data = fetch_finmind_monthly_revenue(code)
        
        if not data:
            print(f"    ⚠️ 未取得 {code} 月營收歷史資料，跳過。")
            time.sleep(0.5)
            continue
            
        print(f"    ✓ 成功下載 {len(data)} 筆月營收歷史紀錄。正在寫入 DuckDB...")
        
        cursor = conn.cursor()
        batch_data = []
        for row in data:
            date = str(row.get("date", ""))
            rev = int(row.get("revenue", 0))
            month = int(row.get("revenue_month", 0))
            year = int(row.get("revenue_year", 0))
            out_val = int(row.get("out", 0))
            in_val = int(row.get("in", 0))
            yoy = float(row.get("during_manifest_yoy", 0.0))
            mom = float(row.get("during_manifest_mom", 0.0))
            
            batch_data.append((date, code, rev, month, year, out_val, in_val, yoy, mom))
            
        try:
            cursor.executemany('''
                INSERT INTO monthly_revenue (date, code, revenue, revenue_month, revenue_year, out_revenue, in_revenue, yoy, mom)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date, code) DO UPDATE SET
                    revenue = excluded.revenue,
                    revenue_month = excluded.revenue_month,
                    revenue_year = excluded.revenue_year,
                    out_revenue = excluded.out_revenue,
                    in_revenue = excluded.in_revenue,
                    yoy = excluded.yoy,
                    mom = excluded.mom
            ''', batch_data)
            conn.commit()
            print(f"    ✓ {code} 歷史數據同步至 DuckDB 成功！")
            success_count += 1
            total_records += len(batch_data)
        except Exception as e:
            print(f"    ❌ {code} 寫入 DuckDB 失敗: {e}")
            
        # 友善冷卻防止觸發 WAF 封鎖
        time.sleep(0.2)
        
    conn.close()
    
    elapsed = time.time() - start_time
    print("=========================================================================")
    print(f" 🎉 月營收歷史補全圓滿成功！")
    print(f"  - 成功補全商品：{success_count} / {len(target_codes)} 檔")
    print(f"  - 累計同步月數：{total_records} 個月份")
    print(f"  - 總計花費時間：{elapsed:.2f} 秒")
    print("=========================================================================")

if __name__ == "__main__":
    main()
