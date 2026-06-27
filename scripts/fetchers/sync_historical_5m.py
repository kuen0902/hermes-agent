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
import time
import yfinance as yf
import pandas as pd
import duckdb
from datetime import datetime, timedelta

# Configuration
DATA_DIR = os.path.expanduser("~/.hermes/data")
DB_PATH = os.path.join(DATA_DIR, "portfolio.db")
REGISTRY_PATH = os.path.join(DATA_DIR, "master_stock_registry.json")

def load_stock_suffixes(active_codes):
    """Loads all stock suffixes for active codes in a single highly-optimized DuckDB batch query."""
    suffixes = {}
    
    # 1. Fallback initializations using the static OTC list
    otc_set = {"3105", "3211", "3260", "3709", "4543", "4925", "5289", "5347", "6125", "6147", "6290", "6510", "6877", "7815", "7843", "7828", "8299"}
    for code in active_codes:
        suffixes[code] = ".TWO" if code in otc_set else ".TW"
        
    # 2. Try single optimized batch query in DuckDB
    potential_ddb = os.path.join(DATA_DIR, "potential_analysis.ddb")
    if os.path.exists(potential_ddb):
        try:
            conn = duckdb.connect(potential_ddb, read_only=True)
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
            print(f"  ⚠️ 批次讀取 DuckDB 股號後綴失敗: {e}")
            
    return suffixes

def load_historically_active_codes():
    """Compiles ALL market stock codes in the system for full market ML simulation."""
    codes = set()
    
    potential_ddb = os.path.join(DATA_DIR, "potential_analysis.ddb")
    if os.path.exists(potential_ddb):
        try:
            import duckdb
            conn = duckdb.connect(potential_ddb, read_only=True)
            # Fetch all codes that have daily data
            rows = conn.execute("SELECT DISTINCT code FROM daily_stock_data").fetchall()
            for r in rows:
                codes.add(str(r[0]).strip())
            conn.close()
        except Exception as e:
            print(f"⚠️ 無法讀取 DuckDB 獲取全市場股號: {e}")
            
    # 2. Fallback to registry if DuckDB is empty
    if not codes and os.path.exists(REGISTRY_PATH):
        try:
            with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            for code in registry.get("official_names", {}).keys():
                codes.add(str(code).strip())
                
        except Exception as e:
            print(f"⚠️ 無法讀取 Registry JSON: {e}")
            
    # Filter out empty or non-digit codes
    valid_codes = {c for c in codes if c.isdigit()}
    return sorted(list(valid_codes))

def sync_5m_data():
    print("=========================================================================")
    print(f" ⏳ 啟動「歷史股票」5分鐘高頻價量數據每日同步常式 [{datetime.now().strftime('%Y-%m-%d %H:%M')}]")
    print("=========================================================================")
    
    active_codes = load_historically_active_codes()
    print(f"  偵測到系統歷史累積股票共 {len(active_codes)} 檔。正在逐一更新 5m K 線檔案...")
    
    success_count = 0
    fail_count = 0
    dfs_to_sync = []
    
    # 📌 唯讀模式開啟 DuckDB 連線，避免併發寫入鎖定衝突
    potential_ddb = os.path.join(DATA_DIR, "potential_analysis.ddb")
    conn = None
    if os.path.exists(potential_ddb):
        try:
            conn = duckdb.connect(potential_ddb, read_only=True)
            print("  ✓ 成功建立 DuckDB 唯讀資料連線，啟動高速本地同步。")
        except Exception as e:
            print(f"  ⚠️ 無法以唯讀模式連接 DuckDB: {e}")
            
    # 📌 批次一次性解析載入所有股票後綴快取，避免在迴圈內重複連接資料庫 (O(1) 效能優化)
    stock_suffixes = load_stock_suffixes(active_codes)
    
    for idx, code in enumerate(active_codes, 1):
        suffix = stock_suffixes.get(code, ".TW")
        ticker = f"{code}{suffix}"
        output_path = os.path.join(DATA_DIR, f"{code}_intraday_5m.csv")
        
        print(f"  [{idx}/{len(active_codes)}] 正在同步 {ticker} 5m 價量...")
        time.sleep(0.5)
        
        df_db_clean = None
        
        # 1. 優先從本地 DuckDB kbars_5m 資料表提取高頻歷史數據 (極速、零網路開銷)
        if conn:
            try:
                query = """
                    SELECT timestamp, open AS Open, high AS High, low AS Low, close AS Close, volume AS Volume, amount AS Amount, transaction AS Transaction
                    FROM kbars_5m
                    WHERE code = ?
                    ORDER BY timestamp DESC
                    LIMIT 10000
                """
                df_db = conn.execute(query, (code,)).fetchdf()
                if not df_db.empty:
                    # 排序調整回升冪 (時間先到後)
                    df_db = df_db.sort_values('timestamp').reset_index(drop=True)
                    
                    # 📌 轉換為與 yfinance 完全一致的 UTC 時區與 ISO 字串格式
                    df_db['timestamp'] = pd.to_datetime(df_db['timestamp']) # type: ignore
                    if df_db['timestamp'].dt.tz is None: # type: ignore
                        df_db['timestamp'] = df_db['timestamp'].dt.tz_localize('Asia/Taipei').dt.tz_convert('UTC') # type: ignore
                    else:
                        df_db['timestamp'] = df_db['timestamp'].dt.tz_convert('UTC') # type: ignore
                    df_db['timestamp'] = df_db['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S+00:00') # type: ignore
                    
                    df_db_clean = df_db[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Transaction']]
            except Exception as d_err:
                print(f"    ⚠️ 從 DuckDB 讀取 {code} 失敗: {d_err}")
                
        # 2. 抓取 150 天的 5m 價量與全維度籌碼
        df_latest = None
        # A. 優先嘗試 FinMind API (拉取 1m 資料並重採樣為 5m)
        finmind_success = False
        try:
            target_start_date = (datetime.now() - timedelta(days=150)).strftime("%Y-%m-%d")
            url = "https://api.finmindtrade.com/api/v4/data"
            params = {
                'dataset': 'TaiwanStockKBar',
                'data_id': code,
                'start_date': target_start_date,
                'token': "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiYm9va2lkIiwiZW1haWwiOiJib29raWQyMDAwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjB9.MaUs7zQVYm5qKtlpIRdZ-s-I6WXCfcdtIowZiR7mXM4"
            }
            
            # FinMind Robust Retry Loop
            for _retry in range(3):
                r = requests.get(url, params=params, timeout=25, verify=False)
                if r.status_code == 200:
                    res_data = r.json()
                    fm_status = res_data.get('status')
                    fm_msg = res_data.get('msg', '')
                    
                    if fm_status == 200 or fm_msg == 'success':
                        raw_data = res_data.get('data', [])
                        if raw_data:
                            df_raw = pd.DataFrame(raw_data)
                            df_raw['timestamp'] = pd.to_datetime(df_raw['date'] + ' ' + df_raw['minute'])
                            df_raw = df_raw.set_index('timestamp').sort_index()
                            
                            # 轉換為數值並確保必要欄位存在
                            for col in ['open', 'high', 'low', 'close', 'volume', 'turnover', 'transaction']:
                                if col not in df_raw.columns:
                                    df_raw[col] = 0.0
                                else:
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
                            df_latest = resampled[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Transaction']]
                            finmind_success = True
                            print(f"    ✓ [FinMind] 成功同步最新 150日 全維度增量數據。")
                            
                            # [防護機制] 雖然有 20000 次額度，但為避免單秒鐘內發送過多請求觸發 IP Banned (DDoS防護)，
                            # 每次成功抓取後微幅休眠 0.5 秒
                            time.sleep(0.5)
                        break  # Break out of retry loop on success
                        
                    elif fm_status == 402 or "limit" in str(fm_msg).lower() or "warning" in str(fm_msg).lower() or "too many" in str(fm_msg).lower():
                        # API Limit or Warning Received: Force 30 minutes CD as per user experience
                        wait_seconds = 1800  # 30 minutes
                        print(f"    ⏳ [FinMind API] 收到額度上限或警告 ({fm_msg})，強制休眠 30 分鐘 (1800秒) 以確保額度重置...")
                        time.sleep(wait_seconds)
                        print("    ⏰ 休眠結束，重試抓取！")
                        continue  # Retry after sleeping
                    else:
                        print(f"    ⚠️ 從 FinMind 下載失敗: {fm_msg}")
                        break
                        
                elif r.status_code == 402:
                    # HTTP 402 Payment Required / Quota Exceeded (From User Screenshot)
                    wait_seconds = 1800  # 30 minutes
                    print(f"    ⏳ [FinMind API] 收到 HTTP 402 (額度上限)，強制休眠 30 分鐘 (1800秒) 以確保額度重置...")
                    time.sleep(wait_seconds)
                    print("    ⏰ 休眠結束，重試抓取！")
                    continue
                    
                elif r.status_code == 429:
                    print("    ⚠️ [FinMind API] 請求過於頻繁 (HTTP 429)，休眠 5 秒後重試...")
                    time.sleep(5)
                    continue
                elif r.status_code == 403:
                    try:
                        res_data = r.json()
                        if "banned" in str(res_data.get('msg', '')).lower():
                            retry_after = res_data.get('retry_after', 1800)
                            print(f"    ⏳ [FinMind API] 收到 HTTP 403 (IP Banned)，需冷卻 {retry_after} 秒，強制休眠...")
                            time.sleep(retry_after + 10)
                            print("    ⏰ 休眠結束，重試抓取！")
                            continue
                    except:
                        pass
                    print(f"    ⚠️ 從 FinMind 下載失敗 HTTP 403")
                    break
                else:
                    print(f"    ⚠️ 從 FinMind 下載失敗 HTTP {r.status_code}")
                    break
            
            # [終極防護] 根據官方文件，短時間內累積太多 4xx 錯誤（如碰到無效股號）會觸發 IP 封鎖。
            # 所以不管成功還是失敗（如 400 錯誤），每次請求完都必須強制休眠 0.5 秒，避免錯誤瞬間累積。
            time.sleep(0.5)

        except Exception as fm_err:
            print(f"    ⚠️ 從 FinMind 下載 {ticker} 150日增量例外錯誤: {fm_err}")
            time.sleep(0.5)
            
        # B. 降級備用方案：若 FinMind 失敗，則使用 yfinance 抓取 OHLCV，並把 Amount 與 Transaction 補 0
        if not finmind_success:
            try:
                df_yf = yf.download(ticker, period="60d", interval="5m", progress=False)
                if not df_yf.empty:
                    if isinstance(df_yf.columns, pd.MultiIndex):
                        df_yf.columns = df_yf.columns.get_level_values(0)
                        
                    df_yf = df_yf[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
                    df_yf = df_yf.reset_index()
                    df_yf.rename(columns={'Datetime': 'timestamp'}, inplace=True)
                    df_yf['timestamp'] = pd.to_datetime(df_yf['timestamp']).dt.tz_convert('UTC').dt.strftime('%Y-%m-%d %H:%M:%S+00:00')
                    
                    df_yf['Amount'] = 0.0
                    df_yf['Transaction'] = 0
                    
                    df_latest = df_yf[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Transaction']]
                    print(f"    ⚠️ [yfinance 備援] 已降級下載 {ticker} 60日基本價量資料。")
            except Exception as e:
                print(f"    ❌ 從 yfinance 下載 {ticker} 60日增量失敗: {e}")

        # 3. 合併歷史與最新增量數據
        df = None
        if df_db_clean is not None and df_latest is not None:
            df = pd.concat([df_db_clean, df_latest], ignore_index=True) # type: ignore
            df = df.drop_duplicates(subset=['timestamp'], keep='last')
            df = df.sort_values('timestamp').reset_index(drop=True)
        elif df_db_clean is not None:
            df = df_db_clean
        elif df_latest is not None:
            df = df_latest
            
        # 4. 如果兩者皆空，作為最後防線，嘗試下載 60d yfinance 備份
        if df is None or df.empty:
            print(f"    ⚠️ 無本地與增量資料，嘗試下載 60d yfinance 備份...")
            try:
                df_yf = yf.download(ticker, period="60d", interval="5m", progress=False)
                if not df_yf.empty:
                    if isinstance(df_yf.columns, pd.MultiIndex):
                        df_yf.columns = df_yf.columns.get_level_values(0)
                        
                    df_yf = df_yf[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
                    df_yf = df_yf.reset_index()
                    df_yf.rename(columns={'Datetime': 'timestamp'}, inplace=True)
                    df_yf['timestamp'] = pd.to_datetime(df_yf['timestamp']).dt.tz_convert('UTC').dt.strftime('%Y-%m-%d %H:%M:%S+00:00')
                    
                    df_yf['Amount'] = 0.0
                    df_yf['Transaction'] = 0
                    
                    df = df_yf[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Transaction']]
            except Exception as e:
                print(f"    ❌ 下載 {ticker} 60d 備份失敗: {e}")
                
        # 5. 儲存 CSV 檔，並收集以供批次回寫資料庫
        if df is not None and not df.empty:
            try:
                # 限制檔案最大長度，只保留最近 10000 筆高頻 K 線
                df = df.tail(10000)
                df.to_csv(output_path, index=False)
                print(f"    ✓ 成功更新 5m 高頻資料檔案: {output_path} ({len(df)} 筆)")
                success_count += 1
                
                # 收集資料，加入 code, ticker, name 供批次寫入 DuckDB
                df_temp = df.copy()
                df_temp['code'] = code
                df_temp['ticker'] = ticker
                
                reg_name = None
                if os.path.exists(REGISTRY_PATH):
                    try:
                        with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
                            registry = json.load(f)
                        reg_name = registry.get("official_names", {}).get(code)
                    except:
                        pass
                        
                fixes = {
                    "3481": "群創", "2330": "台積電", "2317": "鴻海", "2454": "聯發科",
                    "2382": "廣達", "2409": "友達", "2408": "南亞科", "2327": "國巨",
                    "1513": "中興電", "2049": "上銀", "5347": "世界", "4543": "萬在",
                    "3709": "鑫聯大投控", "3260": "威剛", "6770": "力積電", "5443": "均豪",
                    "2368": "金像電", "2344": "華邦電", "1802": "台玻", "0050": "元大台灣50",
                    "00965": "元大航太防衛科技", "00981A": "主動統一台股增長", "0052": "富邦科技",
                }
                
                final_name = reg_name if (reg_name and reg_name != code) else fixes.get(code, code)
                df_temp['name'] = final_name
                df_temp.rename(columns={
                    'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume',
                    'Amount': 'amount', 'Transaction': 'transaction'
                }, inplace=True)
                df_temp = df_temp[['timestamp', 'code', 'ticker', 'name', 'open', 'high', 'low', 'close', 'volume', 'amount', 'transaction']]
                dfs_to_sync.append(df_temp)
            except Exception as e:
                print(f"    ❌ 儲存 {ticker} CSV 檔失敗: {e}")
                fail_count += 1
        else:
            print(f"    ❌ 同步 {ticker} 失敗：無可用之 5m 數據")
            fail_count += 1
            
    if conn:
        try:
            conn.close()
        except:
            pass
            
    # 📌 6. 批次將更新後的最新高頻增量數據寫回 DuckDB 保持快取新鮮度 (自我修復)
    if dfs_to_sync:
        print("\n  ⏳ 正在將更新後的 5m 高頻快取數據批次寫入 DuckDB...")
        try:
            df_all_sync = pd.concat(dfs_to_sync, ignore_index=True)
            df_all_sync['timestamp'] = pd.to_datetime(df_all_sync['timestamp'])
            
            conn_write = duckdb.connect(potential_ddb)
            conn_write.execute("""
                CREATE TABLE IF NOT EXISTS kbars_5m (
                    timestamp TIMESTAMP,
                    code VARCHAR,
                    ticker VARCHAR,
                    name VARCHAR,
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume DOUBLE,
                    amount DOUBLE,
                    transaction DOUBLE,
                    PRIMARY KEY (timestamp, code)
                )
            """)
            conn_write.execute("INSERT OR REPLACE INTO kbars_5m SELECT * FROM df_all_sync")
            conn_write.commit()
            conn_write.close()
            print(f"  ✓ 成功批次更新 DuckDB kbars_5m 主庫 (共 {len(df_all_sync)} 筆資料)")
        except Exception as db_err:
            print(f"  ❌ 批次寫入 DuckDB 失敗: {db_err}")
            
    print("=========================================================================")
    print(f"  🎉 歷史股票 5m 同步完成！ 成功：{success_count} 檔 | 失敗：{fail_count} 檔")
    print("=========================================================================")

if __name__ == "__main__":
    sync_5m_data()
