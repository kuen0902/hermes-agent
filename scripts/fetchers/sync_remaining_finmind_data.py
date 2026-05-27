#!/Users/bookid/.hermes/.venv/bin/python
# -*- coding: utf-8 -*-
import os
import time
import datetime
import json
import requests
import sqlite3
import duckdb
import urllib3

# Suppress warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATA_DIR = os.path.expanduser("~/.hermes/data")
DB_PATH = os.path.join(DATA_DIR, "portfolio.db")
DUCK_PATH = os.path.join(DATA_DIR, "potential_analysis.ddb")
CENTRAL_JSON = os.path.join(DATA_DIR, "central_stock_data.json")

FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiYm9va2lkIiwiZW1haWwiOiJib29raWQyMDAwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjB9.MaUs7zQVYm5qKtlpIRdZ-s-I6WXCfcdtIowZiR7mXM4"
GER_TOKEN = "8513436203:AAHcvVxNgLEqQ_U_JH55mZaENCWfl4VTFJ4"
JOJO_CHAT_ID = "6326497055"

CORE_SYMBOLS = [
    "2330.TW", "2454.TW", "3037.TW", "2382.TW", "2327.TW",
    "8996.TW", "5289.TWO", "4966.TWO", "3583.TW", "8210.TW",
    "5347.TWO", "6510.TWO", "3211.TWO", "6290.TWO", "6669.TW",
    "1513.TW", "2049.TW", "2408.TW", "2313.TW", "6285.TW"
]

def load_target_codes():
    target_codes = set()
    for s in CORE_SYMBOLS:
        target_codes.add(s.replace(".TW", "").replace(".TWO", "").strip())
    
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT code FROM current_holdings")
            for row in cursor.fetchall():
                code = str(row[0]).replace(".TW", "").replace(".TWO", "").strip()
                target_codes.add(code)
            conn.close()
        except Exception as e:
            print(f"⚠️ 無法讀取持股清單: {e}")
            
    if os.path.exists(CENTRAL_JSON):
        try:
            with open(CENTRAL_JSON, 'r', encoding='utf-8') as f:
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
            print(f"⚠️ 無法讀取監控清單: {e}")
            
    return sorted(list(target_codes))

def send_telegram(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram failed: {e}")

def get_report_date(date_str):
    parts = date_str.split('-')
    year = int(parts[0])
    month = int(parts[1])
    if month == 3: return f"{year}-05-15"
    elif month == 6: return f"{year}-08-15"
    elif month == 9: return f"{year}-11-15"
    elif month == 12: return f"{year+1}-04-01"
    return date_str

def main():
    print("=========================================================================")
    print(" 🚀 啟動在線商品 FinMind 剩餘資料 (月營收與財務季報) 每日增量同步常式")
    print("=========================================================================")
    
    start_time = time.time()
    target_codes = load_target_codes()
    print(f"在線個股總數: {len(target_codes)} 檔")
    
    if not target_codes:
        print("❌ 無核心個股需要同步，結束。")
        return
        
    conn = duckdb.connect(DUCK_PATH)
    
    # 1. 同步最近兩個月之月營收
    success_rev = 0
    new_rev_records = 0
    # 查詢起始日：前一個月的第一天
    today = datetime.datetime.now()
    start_date_rev = (today - datetime.timedelta(days=60)).replace(day=1).strftime("%Y-%m-%d")
    
    print(f"\n  [1/2] 正在同步最近月營收資料 (起始日: {start_date_rev})...")
    
    for idx, code in enumerate(target_codes, 1):
        url = "https://api.finmindtrade.com/api/v4/data"
        params = {
            'dataset': 'TaiwanStockMonthRevenue',
            'data_id': code,
            'start_date': start_date_rev,
            'token': FINMIND_TOKEN
        }
        try:
            r = requests.get(url, params=params, timeout=15, verify=False)
            if r.status_code == 200:
                data = r.json().get('data', [])
                if data:
                    cursor = conn.cursor()
                    batch = []
                    for row in data:
                        date = str(row.get("date", ""))
                        rev = int(row.get("revenue", 0))
                        month = int(row.get("revenue_month", 0))
                        year = int(row.get("revenue_year", 0))
                        out_val = int(row.get("out", 0))
                        in_val = int(row.get("in", 0))
                        yoy = float(row.get("during_manifest_yoy", 0.0))
                        mom = float(row.get("during_manifest_mom", 0.0))
                        batch.append((date, code, rev, month, year, out_val, in_val, yoy, mom))
                        
                    if batch:
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
                        ''', batch)
                        conn.commit()
                        success_rev += 1
                        new_rev_records += len(batch)
            time.sleep(0.1)
        except Exception as e:
            print(f"    ⚠️ 同步 {code} 月營收失敗: {e}")
            
    # 2. 同步最近兩個季度之財務季報 (全市場批次查詢)
    success_fin = 0
    new_fin_records = 0
    quarter_ends = []
    y = today.year
    # 前後一年的季度以覆蓋最近 2 季度
    for yr in [y-1, y]:
        for m in ["03-31", "06-30", "09-30", "12-31"]:
            q_date = f"{yr}-{m}"
            if q_date <= today.strftime("%Y-%m-%d"):
                quarter_ends.append(q_date)
    # 取最近兩個
    quarter_ends = sorted(quarter_ends)[-2:]
    
    print(f"\n  [2/2] 正在同步最近季度財務報表... (季度截止日: {quarter_ends})")
    
    for q_date in quarter_ends:
        url = "https://api.finmindtrade.com/api/v4/data"
        params = {
            'dataset': 'TaiwanStockFinancialStatements',
            'start_date': q_date,
            'token': FINMIND_TOKEN
        }
        try:
            r = requests.get(url, params=params, timeout=30, verify=False)
            if r.status_code == 200:
                data = r.json().get('data', [])
                if data:
                    stock_quarters = {}
                    for row in data:
                        stock_id = str(row.get("stock_id", "")).strip()
                        if stock_id not in target_codes:
                            continue
                        t = str(row.get("type", ""))
                        try:
                            v = float(row.get("value", 0.0))
                        except:
                            v = 0.0
                        if stock_id not in stock_quarters:
                            stock_quarters[stock_id] = {}
                        stock_quarters[stock_id][t] = v
                        
                    cursor = conn.cursor()
                    batch = []
                    for stock_id, q_data in stock_quarters.items():
                        rev = q_data.get('Revenue', 0.0)
                        gp = q_data.get('GrossProfit', 0.0)
                        op = q_data.get('OperatingIncome', 0.0)
                        net = q_data.get('IncomeAfterTaxes', 0.0)
                        eps = q_data.get('EPS', 0.0)
                        
                        gp_margin = gp / rev if rev > 0 else 0.0
                        op_margin = op / rev if rev > 0 else 0.0
                        net_margin = net / rev if rev > 0 else 0.0
                        report_date = get_report_date(q_date)
                        
                        batch.append((q_date, stock_id, report_date, eps, gp_margin, op_margin, net_margin))
                        
                    if batch:
                        cursor.executemany('''
                            INSERT INTO financial_statements (date, code, report_date, eps, gross_profit_margin, operating_profit_margin, net_profit_margin)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(date, code) DO UPDATE SET
                                report_date = excluded.report_date,
                                eps = excluded.eps,
                                gross_profit_margin = excluded.gross_profit_margin,
                                operating_profit_margin = excluded.operating_profit_margin,
                                net_profit_margin = excluded.net_profit_margin
                        ''', batch)
                        conn.commit()
                        success_fin += len(batch)
                        new_fin_records += len(batch)
            time.sleep(0.5)
        except Exception as e:
            print(f"    ⚠️ 同步 {q_date} 財務報表失敗: {e}")
            
    conn.close()
    
    # 📌 3. 執行 5m 高頻資料健康體檢與缺漏自動回補
    try:
        print("\n⏳ 啟動 5m 高頻資料健康體檢與缺漏自動回補...")
        import subprocess
        # 執行體檢
        subprocess.run(["/Users/bookid/.hermes/.venv/bin/python", "/Users/bookid/.hermes/scripts/fetchers/audit_5m_data.py"])
        # 執行回補
        subprocess.run(["/Users/bookid/.hermes/.venv/bin/python", "/Users/bookid/.hermes/scripts/fetchers/backfill_missing_5m.py"])
        print("✓ 5m 高頻資料健康體檢與自動回補完成！")
    except Exception as e:
        print(f"⚠️ 5m 高頻資料體檢或回補失敗: {e}")

    elapsed = time.time() - start_time
    print(f"\n  ✓ 同步完成！月營收增量個股: {success_rev} 檔 | 季報新增/更新個股: {success_fin} 檔 | 總耗時: {elapsed:.2f} 秒")

    
    # 📌 3. 發送 summary 報告至「黃金體驗-鎮魂曲」 (GER Bot)
    ger_msg = f"""🌅 **「黃金體驗-鎮魂曲」：現實同步 (月營收與財務季報) 🌅**
偏離的意志已歸於「零」。這就是目前的絕對現實。

### 📊 **FinMind 剩餘資料每日同步摘要**
*   **同步個股總數**：`{len(target_codes)}` 檔
*   **月營收更新成功**：`{success_rev}` 檔 (`{new_rev_records}` 筆月份紀錄)
*   **財務季報更新成功**：`{success_fin}` 檔 (`{new_fin_records}` 筆季度紀錄)
*   **數據同步總耗時**：`{elapsed:.2f}` 秒

**無駄！** 所有在線商品之剩餘指標均已完成增量同步。"""
    
    send_telegram(GER_TOKEN, JOJO_CHAT_ID, ger_msg)
    print("✓ 增量同步報告已發送至 Telegram 黃金體驗-鎮魂曲！")

if __name__ == "__main__":
    main()
