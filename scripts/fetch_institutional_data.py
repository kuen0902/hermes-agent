import os
import json
import time
import datetime
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATA_DIR = os.path.expanduser("~/.hermes/data")
INST_FILE = os.path.join(DATA_DIR, "institutional_data.json")

CORE_SYMBOLS = [
    "2330.TW", "2454.TW", "3037.TW", "2382.TW", "2327.TW",
    "8996.TW", "5289.TWO", "4966.TWO", "3583.TW", "8210.TW",
    "5347.TWO", "6510.TWO", "3211.TWO", "6290.TWO", "6669.TW",
    "1513.TW", "2049.TW", "2408.TW", "2313.TW", "6285.TW"
]

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
    # TPEx uses ROC year: YYY/MM/DD
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
            # New format:
            # 4: 外資(不含自營)買賣超, 13: 投信買賣超, 22: 自營商合計買賣超
            foreign_idx, trust_idx, dealer_idx = 4, 13, 22
        elif 'aaData' in data:
            rows = data['aaData']
            # Old format:
            # 4: 外資, 7: 投信, 10: 自營商
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

def main():
    print("啟動三大法人籌碼歷史爬蟲...")
    db = load_inst_data()
    
    # We want past 60 days
    today = datetime.date.today()
    
    twse_symbols = [s.replace('.TW', '') for s in CORE_SYMBOLS if '.TW' in s]
    tpex_symbols = [s.replace('.TWO', '') for s in CORE_SYMBOLS if '.TWO' in s]
    
    for i in range(60):
        target_date = today - datetime.timedelta(days=i)
        if target_date.weekday() >= 5: continue # 週末跳過
            
        iso_date = target_date.isoformat()
        if iso_date in db:
            continue # 已有資料
            
        date_str = target_date.strftime("%Y%m%d")
        print(f"正在抓取 {iso_date} 的法人籌碼...", end='', flush=True)
        
        twse_data = fetch_twse(date_str)
        time.sleep(2) # 防鎖 IP
        tpex_data = fetch_tpex(date_str)
        time.sleep(2)
        
        if not twse_data and not tpex_data:
            print(" (無資料)")
            # 可能是假日，還是紀錄一個空字典避免未來重複抓
            db[iso_date] = {}
        else:
            db[iso_date] = {}
            for code in twse_symbols:
                if code in twse_data:
                    db[iso_date][f"{code}.TW"] = twse_data[code]
            for code in tpex_symbols:
                if code in tpex_data:
                    db[iso_date][f"{code}.TWO"] = tpex_data[code]
            print(f" (成功: TWSE={len(twse_data)}, TPEx={len(tpex_data)})")
            
        save_inst_data(db)

if __name__ == "__main__":
    main()
