#!/Users/bookid/.hermes/.venv/bin/python
# -*- coding: utf-8 -*-
import os
import time
import datetime
import requests
import duckdb
import urllib3

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATA_DIR = os.path.expanduser("~/.hermes/data")
DUCK_PATH = os.path.join(DATA_DIR, "potential_analysis.ddb")
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2Vy_idIjoiYm9va2lkIiwiZW1haWwiOiJib29raWQyMDAwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjB9.MaUs7zQVYm5qKtlpIRdZ-s-I6WXCfcdtIowZiR7mXM4"
# Actually, the token in original file has user_id but the model truncated/masked? 
# Let's use the exact token from the original file:
# eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiYm9va2lkIiwiZW1haWwiOiJib29raWQyMDAwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjB9.MaUs7zQVYm5qKtlpIRdZ-s-I6WXCfcdtIowZiR7mXM4

def load_db_codes():
    """從 daily_stock_data 載入所有存在的 stock codes，避免寫入無效商品"""
    if not os.path.exists(DUCK_PATH):
        return set()
    try:
        conn = duckdb.connect(DUCK_PATH)
        df = conn.execute("SELECT DISTINCT code FROM daily_stock_data").fetchdf()
        conn.close()
        codes = set(df['code'].astype(str).str.strip().tolist())
        return codes
    except Exception as e:
        print(f"⚠️ 無法載入資料庫商品代碼: {e}")
        return set()

def get_report_date(date_str):
    """計算季度財報的法定發布日期 (防止未來函數/Look-ahead Bias)"""
    parts = date_str.split('-')
    year = int(parts[0])
    month = int(parts[1])
    
    if month == 3:     # Q1
        return f"{year}-05-15"
    elif month == 6:   # Q2
        return f"{year}-08-15"
    elif month == 9:   # Q3
        return f"{year}-11-15"
    elif month == 12:  # Q4 / 年報
        return f"{year+1}-04-01"
    else:
        return date_str

def init_duck_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        conn = duckdb.connect(DUCK_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS financial_statements (
                date VARCHAR,
                code VARCHAR,
                report_date VARCHAR,
                eps DOUBLE,
                gross_profit_margin DOUBLE,
                operating_profit_margin DOUBLE,
                net_profit_margin DOUBLE,
                PRIMARY KEY (date, code)
            )
        ''')
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fin_code ON financial_statements(code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fin_date ON financial_statements(date)")
        conn.commit()
        return conn
    except Exception as e:
        print(f"❌ 無法建立 DuckDB 寫入連線: {e}")
        return None

def fetch_finmind_bulk_date(q_date):
    """批次獲取整個市場在特定季度截止日的財務損益表數據"""
    url = "https://api.finmindtrade.com/api/v4/data"
    parameter = {
        'dataset': 'TaiwanStockFinancialStatements',
        'start_date': q_date,
        'token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiYm9va2lkIiwiZW1haWwiOiJib29raWQyMDAwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjB9.MaUs7zQVYm5qKtlpIRdZ-s-I6WXCfcdtIowZiR7mXM4'
    }
    try:
        r = requests.get(url, params=parameter, timeout=30, verify=False)
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
    print(" 🚀 啟動全市場 14 年季度財務報表 (2012 至今) 全自動高速批次補全程式")
    print("=========================================================================")
    
    db_codes = load_db_codes()
    print(f"  資料庫中現有股票商品共計: {len(db_codes)} 檔")
    if not db_codes:
        print("❌ 資料庫中沒有任何股票，無法進行補全。")
        return
        
    conn = init_duck_db()
    if conn is None:
        print("❌ 無法取得 DuckDB 寫入權限，結束程式。")
        return
        
    # 生成 2012 至今的所有季度截止日
    start_year = 2012
    current_year = datetime.datetime.now().year
    quarter_ends = []
    
    for y in range(start_year, current_year + 1):
        for m in ["03-31", "06-30", "09-30", "12-31"]:
            q_date = f"{y}-{m}"
            if q_date <= datetime.datetime.now().strftime("%Y-%m-%d"):
                quarter_ends.append(q_date)
                
    print(f"  總計需要補全 {len(quarter_ends)} 個季度截止日的數據：{quarter_ends}")
    
    total_records = 0
    start_time = time.time()
    
    for idx, q_date in enumerate(quarter_ends, 1):
        print(f"  [{idx}/{len(quarter_ends)}] 正在獲取 {q_date} 全市場財務季報...")
        data = fetch_finmind_bulk_date(q_date)
        
        if not data:
            print(f"    ⚠️ {q_date} 未取得任何財務資料，跳過。")
            time.sleep(0.5)
            continue
            
        # 按 stock_id 分組
        stock_quarters = {}
        for row in data:
            stock_id = str(row.get("stock_id", "")).strip()
            if stock_id not in db_codes:
                continue
                
            t = str(row.get("type", ""))
            try:
                v = float(row.get("value", 0.0))
            except:
                v = 0.0
                
            if stock_id not in stock_quarters:
                stock_quarters[stock_id] = {}
            stock_quarters[stock_id][t] = v
            
        print(f"    ✓ 成功解析 {len(stock_quarters)} 檔資料庫內商品的季度指標。正在寫入 DuckDB...")
        
        cursor = conn.cursor()
        batch_data = []
        
        for stock_id, q_data in stock_quarters.items():
            rev = q_data.get('Revenue', 0.0)
            gp = q_data.get('GrossProfit', 0.0)
            op = q_data.get('OperatingIncome', 0.0)
            net = q_data.get('IncomeAfterTaxes', 0.0)
            eps = q_data.get('EPS', 0.0)
            
            gp_margin = gp / rev if rev > 0 else 0.0
            op_margin = op / rev if rev > 0 else 0.0
            net_margin = net / rev if rev > 0 else 0.0
            
            # 計算法定發佈日期
            report_date = get_report_date(q_date)
            
            batch_data.append((q_date, stock_id, report_date, eps, gp_margin, op_margin, net_margin))
            
        if batch_data:
            try:
                cursor.executemany('''
                    INSERT INTO financial_statements (date, code, report_date, eps, gross_profit_margin, operating_profit_margin, net_profit_margin)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(date, code) DO UPDATE SET
                        report_date = excluded.report_date,
                        eps = excluded.eps,
                        gross_profit_margin = excluded.gross_profit_margin,
                        operating_profit_margin = excluded.operating_profit_margin,
                        net_profit_margin = excluded.net_profit_margin
                ''', batch_data)
                conn.commit()
                print(f"    ✓ 成功批次同步 {len(batch_data)} 筆紀錄到 DuckDB！")
                total_records += len(batch_data)
            except Exception as e:
                print(f"    ❌ 批次寫入 DuckDB 失敗: {e}")
                
        # 爬蟲冷卻
        time.sleep(0.5)
        
    conn.close()
    
    elapsed = time.time() - start_time
    print("=========================================================================")
    print(f" 🎉 全市場財務季報指標高效率批次同步圓滿成功！")
    print(f"  - 累計同步季度紀錄：{total_records} 筆")
    print(f"  - 總計花費時間：{elapsed:.2f} 秒")
    print("=========================================================================")

if __name__ == "__main__":
    main()
