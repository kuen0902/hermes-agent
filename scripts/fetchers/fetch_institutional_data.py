#!/Users/bookid/.hermes/.venv/bin/python
import os
import json
import time
import datetime
import requests
import sqlite3
import argparse
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATA_DIR = os.path.expanduser("~/.hermes/data")
INST_FILE = os.path.join(DATA_DIR, "institutional_data.json")
DB_PATH = os.path.join(DATA_DIR, "portfolio.db")

CORE_SYMBOLS = [
    "2330.TW", "2454.TW", "3037.TW", "2382.TW", "2327.TW",
    "8996.TW", "5289.TWO", "4966.TWO", "3583.TW", "8210.TW",
    "5347.TWO", "6510.TWO", "3211.TWO", "6290.TWO", "6669.TW",
    "1513.TW", "2049.TW", "2408.TW", "2313.TW", "6285.TW"
]

def init_sqlite_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS institutional_data (
            date TEXT,
            code TEXT,
            foreign_buy INTEGER,
            trust_buy INTEGER,
            dealer_buy INTEGER,
            foreign_ratio REAL,
            foreign_holding INTEGER,
            issued_shares INTEGER,
            PRIMARY KEY (date, code)
        )
    ''')
    # 動態增強向後相容
    cursor.execute("PRAGMA table_info(institutional_data)")
    cols = [col[1] for col in cursor.fetchall()]
    for col, c_type in [("foreign_ratio", "REAL"), ("foreign_holding", "INTEGER"), ("issued_shares", "INTEGER")]:
        if col not in cols:
            cursor.execute(f"ALTER TABLE institutional_data ADD COLUMN {col} {c_type}")
    conn.commit()
    return conn


def load_target_codes():
    """從 SQLite 與監控 JSON 讀取當前持股與所有監控代碼，用於限縮 FinMind 外資持股比的 API 查詢"""
    target_codes = set()
    for s in CORE_SYMBOLS:
        target_codes.add(s.replace(".TW", "").replace(".TWO", "").strip())
    
    # 1. 讀取 SQLite 真實持股
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT code FROM current_holdings")
        for row in cursor.fetchall():
            code = str(row[0]).replace(".TW", "").replace(".TWO", "").strip()
            target_codes.add(code)
        conn.close()
    except Exception as e:
        print(f"無法讀取當前持股代碼限制清單: {e}")
        
    # 2. 讀取 central_stock_data.json 的監控清單 (group_codes & william_codes)
    central_data_path = os.path.join(DATA_DIR, "central_stock_data.json")
    if os.path.exists(central_data_path):
        try:
            with open(central_data_path, 'r') as f:
                central_data = json.load(f)
                group_codes = central_data.get("group_codes", [])
                william_codes = central_data.get("william_codes", [])
                
                def norm_c(c_str):
                    return str(c_str).replace(".TW", "").replace(".TWO", "").strip()
                
                if isinstance(group_codes, dict):
                    for c in group_codes.keys(): target_codes.add(norm_c(c))
                elif isinstance(group_codes, list):
                    for c in group_codes: target_codes.add(norm_c(c))
                    
                if isinstance(william_codes, dict):
                    for c in william_codes.keys(): target_codes.add(norm_c(c))
                elif isinstance(william_codes, list):
                    for c in william_codes: target_codes.add(norm_c(c))
        except Exception as e:
            print(f"無法讀取監控清單以擴展三大法人同步目標: {e}")
            
    return target_codes


def load_inst_data():
    if os.path.exists(INST_FILE):
        try:
            with open(INST_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_inst_data(data):
    with open(INST_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def fetch_twse(date_str):
    url = f"https://www.twse.com.tw/fund/T86?response=json&date={date_str}&selectType=ALL"
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=10, verify=False)
        data = r.json()
        if data.get('stat') != 'OK': return {}
        
        result = {}
        fields = data['fields']
        try:
            code_idx = fields.index('證券代號')
            foreign_idx = fields.index('外陸資買賣超股數(不含外資自營商)')
            trust_idx = fields.index('投信買賣超股數')
            dealer_idx = fields.index('自營商買賣超股數')
        except:
            return {}
            
        for row in data['data']:
            code = row[code_idx].strip()
            result[code] = {
                "foreign": int(row[foreign_idx].replace(',', '')) // 1000 if row[foreign_idx] else 0,
                "trust": int(row[trust_idx].replace(',', '')) // 1000 if row[trust_idx] else 0,
                "dealer": int(row[dealer_idx].replace(',', '')) // 1000 if row[dealer_idx] else 0
            }
        return result
    except Exception as e:
        print(f" [TWSE Error: {e}] ", end='')
        return {}

def fetch_tpex(date_str):
    year = int(date_str[:4]) - 1911
    roc_date = f"{year}/{date_str[4:6]}/{date_str[6:]}"
    url = f"https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&se=EW&t=D&d={roc_date}"
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=10, verify=False)
        data = r.json()
        
        rows = []
        if 'tables' in data and len(data['tables']) > 0 and 'data' in data['tables'][0]:
            rows = data['tables'][0]['data']
            foreign_idx, trust_idx, dealer_idx = 4, 13, 22
        elif 'aaData' in data:
            rows = data['aaData']
            foreign_idx, trust_idx, dealer_idx = 4, 7, 10
        else:
            return {}
            
        result = {}
        for row in rows:
            code = row[0].strip()
            result[code] = {
                "foreign": int(row[foreign_idx].replace(',', '')) // 1000 if row[foreign_idx] else 0,
                "trust": int(row[trust_idx].replace(',', '')) // 1000 if row[trust_idx] else 0,
                "dealer": int(row[dealer_idx].replace(',', '')) // 1000 if row[dealer_idx] else 0
            }
        return result
    except Exception as e:
        print(f" [TPEx Error: {e}] ", end='')
        return {}

FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiYm9va2lkIiwiZW1haWwiOiJib29raWQyMDAwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjB9.MaUs7zQVYm5qKtlpIRdZ-s-I6WXCfcdtIowZiR7mXM4"

def fetch_finmind_single(date_str, code):
    """利用 FinMind API 抓取特定日期與代號的外資持股資料"""
    url = "https://api.finmindtrade.com/api/v4/data"
    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    parameter = {
        'dataset': 'TaiwanStockShareholding',
        'data_id': code,
        'start_date': formatted_date,
        'end_date': formatted_date,
        'token': FINMIND_TOKEN
    }
    try:
        time.sleep(0.1) # 稍作延遲防鎖 IP / 頻率限制
        r = requests.get(url, params=parameter, timeout=8, verify=False)
        if r.status_code == 200:
            data = r.json().get('data', [])
            if data:
                row = data[0]
                return (
                    float(row.get("ForeignInvestmentSharesRatio", 0.0)),
                    int(row.get("ForeignInvestmentShares", 0)) // 1000,
                    int(row.get("NumberOfSharesIssued", 0)) // 1000
                )
    except Exception as e:
        print(f" [FinMind Err {code}: {e}] ", end='')
    return 0.0, 0, 0

def save_to_sqlite(conn, date_str, twse_data, tpex_data):
    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    cursor = conn.cursor()
    
    target_codes = load_target_codes()
    print(f" (正在同步外資持股比率，目標限制商品數: {len(target_codes)})...", end='', flush=True)
    
    # Insert TWSE
    for code, val in twse_data.items():
        if code in target_codes:
            f_ratio, f_hold, issued = fetch_finmind_single(date_str, code)
        else:
            f_ratio, f_hold, issued = 0.0, 0, 0
            
        cursor.execute('''
            INSERT INTO institutional_data (date, code, foreign_buy, trust_buy, dealer_buy, foreign_ratio, foreign_holding, issued_shares)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date, code) DO UPDATE SET
                foreign_buy = excluded.foreign_buy,
                trust_buy = excluded.trust_buy,
                dealer_buy = excluded.dealer_buy,
                foreign_ratio = excluded.foreign_ratio,
                foreign_holding = excluded.foreign_holding,
                issued_shares = excluded.issued_shares
        ''', (formatted_date, code, val['foreign'], val['trust'], val['dealer'], f_ratio, f_hold, issued))
        
    # Insert TPEx
    for code, val in tpex_data.items():
        if code in target_codes:
            f_ratio, f_hold, issued = fetch_finmind_single(date_str, code)
        else:
            f_ratio, f_hold, issued = 0.0, 0, 0
            
        cursor.execute('''
            INSERT INTO institutional_data (date, code, foreign_buy, trust_buy, dealer_buy, foreign_ratio, foreign_holding, issued_shares)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date, code) DO UPDATE SET
                foreign_buy = excluded.foreign_buy,
                trust_buy = excluded.trust_buy,
                dealer_buy = excluded.dealer_buy,
                foreign_ratio = excluded.foreign_ratio,
                foreign_holding = excluded.foreign_holding,
                issued_shares = excluded.issued_shares
        ''', (formatted_date, code, val['foreign'], val['trust'], val['dealer'], f_ratio, f_hold, issued))
        
    conn.commit()
    print(f" -> SQLite 寫入成功 (共 {len(twse_data) + len(tpex_data)} 檔)", end='')

def main():
    parser = argparse.ArgumentParser(description="抓取三大法人籌碼資料並同步至 SQLite 資料庫")
    parser.add_argument("--days", type=int, default=1, help="回溯抓取的交易日天數")
    parser.add_argument("--force", action="store_true", help="強制重新抓取已存在之日期資料")
    args = parser.parse_args()

    print(f"啟動三大法人籌碼歷史爬蟲 (回溯天數: {args.days})...")
    conn = init_sqlite_db()
    db = load_inst_data()
    
    today = datetime.date.today()
    twse_symbols = [s.replace('.TW', '') for s in CORE_SYMBOLS if '.TW' in s]
    tpex_symbols = [s.replace('.TWO', '') for s in CORE_SYMBOLS if '.TWO' in s]
    
    fetched_count = 0
    for i in range(args.days):
        target_date = today - datetime.timedelta(days=i)
        if target_date.weekday() >= 5: 
            continue # 跳過週末
            
        iso_date = target_date.isoformat()
        date_str = target_date.strftime("%Y%m%d")
        
        # 檢查 SQLite 資料庫中是否已存在當日資料
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM institutional_data WHERE date = ?", (iso_date,))
        db_exists = cursor.fetchone()[0] > 0
        
        # 若資料已存在且無 --force 參數，則跳過
        if db_exists and not args.force and iso_date in db:
            continue
            
        print(f"正在抓取 {iso_date} 的法人籌碼...", end='', flush=True)
        
        twse_data = fetch_twse(date_str)
        time.sleep(2.0) # 防鎖 IP 延遲
        tpex_data = fetch_tpex(date_str)
        time.sleep(2.0)
        
        if not twse_data and not tpex_data:
            print(" (當日無市場交易資料)")
            # 假日或無交易日，也在 JSON 做一個標記避免重複抓取
            db[iso_date] = {}
        else:
            # 寫入 SQLite
            save_to_sqlite(conn, date_str, twse_data, tpex_data)
            
            # 同時寫入舊的 JSON 以保持 CORE_SYMBOLS 相容性
            db[iso_date] = {}
            for code in twse_symbols:
                if code in twse_data:
                    db[iso_date][f"{code}.TW"] = twse_data[code]
            for code in tpex_symbols:
                if code in tpex_data:
                    db[iso_date][f"{code}.TWO"] = tpex_data[code]
            print(f" | JSON 同步完成 (CORE={len(db[iso_date])})")
            
        save_inst_data(db)
        fetched_count += 1
        
    conn.close()
    print(f"三大法人籌碼抓取完畢！本次共處理 {fetched_count} 個交易日。")

if __name__ == "__main__":
    main()
