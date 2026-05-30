#!/Users/bookid/.hermes/.venv/bin/python
# -*- coding: utf-8 -*-
import os
import json
import time
import duckdb
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime

DATA_DIR = os.path.expanduser("~/.hermes/data")
DB_PATH = os.path.join(DATA_DIR, "potential_analysis.ddb")
AUDIT_JSON = os.path.join(DATA_DIR, "missing_5m_audit.json")

GER_TOKEN = "8513436203:AAHcvVxNgLEqQ_U_JH55mZaENCWfl4VTFJ4"
JOJO_CHAT_ID = "6326497055"

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

def load_stock_suffixes(active_codes):
    """Loads all stock suffixes for active codes in a single highly-optimized DuckDB batch query."""
    suffixes = {}
    otc_set = {"3105", "3211", "3260", "3709", "4543", "4925", "5289", "5347", "6125", "6147", "6290", "6510", "6877", "7815", "7843", "7828", "8299"}
    for code in active_codes:
        suffixes[code] = ".TWO" if code in otc_set else ".TW"
        
    if os.path.exists(DB_PATH):
        try:
            conn = duckdb.connect(DB_PATH, read_only=True)
            rows = conn.execute("SELECT DISTINCT code, ticker FROM daily_stock_data").fetchall()
            conn.close()
            for code_db, ticker in rows:
                if code_db and ticker:
                    c = str(code_db).strip()
                    t = str(ticker).strip()
                    if t.endswith(".TWO"):
                        suffixes[c] = ".TWO"
                    elif t.endswith(".TW"):
                        suffixes[c] = ".TW"
        except Exception as e:
            print(f"⚠️ 批次讀取 DuckDB 股號後綴失敗: {e}")
    return suffixes

def backfill_gaps():
    print("=========================================================================")
    print(" 🚀 啟動 5m 高頻資料缺漏與不足交易日之自動補全回補程序 (03:00 AM)")
    print("=========================================================================")
    
    if not os.path.exists(AUDIT_JSON):
        print("ℹ️ 未發現待回補的 5m 缺漏清單，結束。")
        return
        
    try:
        with open(AUDIT_JSON, 'r', encoding='utf-8') as f:
            gap_registry = json.load(f)
    except Exception as e:
        print(f"❌ 讀取缺漏清單失敗: {e}")
        return
        
    if not gap_registry:
        print("ℹ️ 缺漏清單為空，無須回補。")
        return
        
    print(f"發現共有 {len(gap_registry)} 檔個股存在高頻資料缺漏，開始進行補全...")
    
    success_count = 0
    fixed_details = []
    
    # 📌 批次一次性解析載入所有股票後綴快取，避免在迴圈內重複連接資料庫 (O(1) 效能優化)
    active_codes = list(gap_registry.keys())
    stock_suffixes = load_stock_suffixes(active_codes)
    
    for code, gaps in list(gap_registry.items()):
        try:
            suffix = stock_suffixes.get(code, ".TW")
            ticker = f"{code}{suffix}"
            output_path = os.path.join(DATA_DIR, f"{code}_intraday_5m.csv")
            
            total_gaps_days = len(gaps.get("missing", [])) + len(gaps.get("incomplete", []))
            print(f"\n[補全] {ticker} ... 缺漏/不足天數: {total_gaps_days} 天")
            
            # 1. 下載完整的 60 天 5m 數據 (覆蓋所有缺漏日)
            df_yf_clean = None
            finmind_success = False
            try:
                print(f"  ▸ 正在從 FinMind 下載 60 天 5m 歷史資料...")
                sixty_days_ago = (datetime.now() - pd.Timedelta(days=62)).strftime("%Y-%m-%d")
                url = "https://api.finmindtrade.com/api/v4/data"
                params = {
                    'dataset': 'TaiwanStockKBar',
                    'data_id': code,
                    'start_date': sixty_days_ago,
                    'token': "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiYm9va2lkIiwiZW1haWwiOiJib29raWQyMDAwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjB9.MaUs7zQVYm5qKtlpIRdZ-s-I6WXCfcdtIowZiR7mXM4"
                }
                r = requests.get(url, params=params, timeout=30, verify=False)
                if r.status_code == 200:
                    res_data = r.json()
                    if res_data.get('status') == 200 or res_data.get('msg') == 'success':
                        raw_data = res_data.get('data', [])
                        if raw_data:
                            df_raw = pd.DataFrame(raw_data)
                            df_raw['timestamp'] = pd.to_datetime(df_raw['date'] + ' ' + df_raw['minute'])
                            df_raw = df_raw.set_index('timestamp').sort_index()
                            
                            # 轉換為數值
                            for col in ['open', 'high', 'low', 'close', 'volume', 'turnover', 'transaction']:
                                if col in df_raw.columns:
                                    df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0.0)
                            
                            # 重採樣成 5m
                            resampled = df_raw.resample('5Min', closed='right', label='right').agg({
                                'open': 'first',
                                'high': 'max',
                                'low': 'min',
                                'close': 'last',
                                'volume': 'sum',
                                'turnover': 'sum',
                                'transaction': 'sum'
                            }).dropna()
                            
                            resampled = resampled[resampled['volume'] > 0.0].reset_index()
                            resampled.rename(columns={
                                'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume',
                                'turnover': 'Amount', 'transaction': 'Transaction'
                            }, inplace=True)
                            
                            # 轉為 ISO UTC 時區
                            resampled['timestamp'] = pd.to_datetime(resampled['timestamp']).dt.tz_localize('Asia/Taipei').dt.tz_convert('UTC').dt.strftime('%Y-%m-%d %H:%M:%S+00:00')
                            df_yf_clean = resampled[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Transaction']]
                            finmind_success = True
                            print(f"  ✓ [FinMind] 成功下載 60日全維度數據。")
            except Exception as fm_err:
                print(f"  ⚠️ 從 FinMind 下載 60d 失敗: {fm_err}")
                
            # yfinance 備援降級方案
            if not finmind_success:
                try:
                    print(f"  ▸ 正在從 yfinance 下載 60 天 5m 歷史資料...")
                    df_yf = yf.download(ticker, period="60d", interval="5m", progress=False)
                    if df_yf.empty:
                        print(f"  ❌ 下載 {ticker} 失敗或無資料。")
                        continue
                        
                    if isinstance(df_yf.columns, pd.MultiIndex):
                        df_yf.columns = df_yf.columns.get_level_values(0)
                        
                    df_yf = df_yf[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
                    df_yf = df_yf.reset_index()
                    df_yf.rename(columns={'Datetime': 'timestamp'}, inplace=True)
                    
                    # 轉換為 UTC ISO 格式
                    df_yf['timestamp'] = pd.to_datetime(df_yf['timestamp']).dt.tz_convert('UTC').dt.strftime('%Y-%m-%d %H:%M:%S+00:00')
                    df_yf['Amount'] = 0.0
                    df_yf['Transaction'] = 0
                    df_yf_clean = df_yf[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Transaction']]
                except Exception as yf_err:
                    print(f"  ❌ 處理 {ticker} (yfinance) 發生異常: {yf_err}")
                    continue

            if df_yf_clean is None or df_yf_clean.empty:
                print(f"  ❌ 無法下載 {ticker} 歷史價格，所有備援管道皆已失敗。")
                continue

            # 2. 合併本地已有的 CSV 資料以防遺失更久以前的快取
            df_combined = None
            if os.path.exists(output_path):
                try:
                    df_local = pd.read_csv(output_path)
                    # 補全欄位以相容於新 Schema
                    if 'Amount' not in df_local.columns and 'amount' in df_local.columns:
                        df_local.rename(columns={'amount': 'Amount'}, inplace=True)
                    if 'Transaction' not in df_local.columns and 'transaction' in df_local.columns:
                        df_local.rename(columns={'transaction': 'Transaction'}, inplace=True)
                        
                    for col in ['Amount', 'Transaction']:
                        if col not in df_local.columns:
                            df_local[col] = 0.0 if col == 'Amount' else 0
                            
                    df_local['timestamp'] = pd.to_datetime(df_local['timestamp']).dt.tz_localize('UTC', ambiguous='NaT').dt.strftime('%Y-%m-%d %H:%M:%S+00:00')
                    df_combined = pd.concat([df_local, df_yf_clean], ignore_index=True)
                    df_combined = df_combined.drop_duplicates(subset=['timestamp'], keep='last') # type: ignore
                    df_combined = df_combined.sort_values('timestamp').reset_index(drop=True)
                except Exception as merge_err:
                    print(f"  ⚠️ 合併本地資料失敗，採用最新下載資料: {merge_err}")
                    df_combined = df_yf_clean
            else:
                df_combined = df_yf_clean
                
            # 3. 限制長度並寫回 CSV
            if df_combined is not None:
                df_combined = df_combined.tail(10000)
                df_combined.to_csv(output_path, index=False)
                print(f"  ✓ 成功儲存 5m 高頻資料至 CSV: {output_path} (共 {len(df_combined)} 筆)")
                
                # 4. 寫回 DuckDB kbars_5m 主庫
                if os.path.exists(DB_PATH):
                    try:
                        conn = duckdb.connect(DB_PATH)
                        
                        # 獲取名稱
                        stock_name = code
                        res_name = conn.execute("SELECT name FROM daily_stock_data WHERE code = ? LIMIT 1", (code,)).fetchone()
                        if res_name and res_name[0]:
                            stock_name = res_name[0]
                            
                        # 重構 df 寫入 DuckDB 格式
                        df_db_sync = df_combined.copy()
                        df_db_sync['timestamp'] = pd.to_datetime(df_db_sync['timestamp'])
                        df_db_sync['code'] = code
                        df_db_sync['ticker'] = ticker
                        df_db_sync['name'] = stock_name
                        
                        df_db_sync.rename(columns={
                            'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume',
                            'Amount': 'amount', 'Transaction': 'transaction'
                        }, inplace=True)
                        
                        df_db_sync = df_db_sync[['timestamp', 'code', 'ticker', 'name', 'open', 'high', 'low', 'close', 'volume', 'amount', 'transaction']]
                        
                        conn.execute("INSERT OR REPLACE INTO kbars_5m SELECT * FROM df_db_sync")
                        conn.commit()
                        conn.close()
                        print(f"  ✓ 成功同步寫入 DuckDB kbars_5m")
                        success_count += 1
                        fixed_details.append(f"• `{code}` ({stock_name}): 成功修復 `{total_gaps_days}` 天缺漏")
                        
                        # 從待回補清單中移除
                        gap_registry.pop(code, None)
                    except Exception as db_err:
                        print(f"  ❌ 寫入 DuckDB 失敗: {db_err}")
                
            time.sleep(1.0) # respect API rate limit
        except Exception as e:
            print(f"  ❌ 處理 {code} 發生異常: {e}")
            
    # 5. 更新快取清單以防重複處理
    with open(AUDIT_JSON, 'w', encoding='utf-8') as f:
        json.dump(gap_registry, f, indent=2, ensure_ascii=False)
        
    print(f"\n✓ 5m 高頻補全回補程序完成！成功修復: {success_count} 檔個股")
    print("=========================================================================")
    
    # 📌 6. 發送 Telegram 報告至「黃金體驗-鎮魂曲」 (GER Bot)
    if fixed_details:
        detail_msg = "\n".join(fixed_details)
        ger_msg = f"""🌅 **「黃金體驗-鎮魂曲」：5m 高頻資料回補報告 🌅**
缺漏的過去已全部被強制作為「無效」，現在只留下現實。

### 📊 **高頻補全修復清單**
{detail_msg}

**無駄！** 所有被標記的 5m 數據缺失與不足已全部重構補全。"""
        send_telegram(GER_TOKEN, JOJO_CHAT_ID, ger_msg)

if __name__ == "__main__":
    backfill_gaps()
