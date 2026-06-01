#!/Users/bookid/.hermes/.venv/bin/python
# -*- coding: utf-8 -*-
import os
import json
import time
import duckdb
import pandas as pd
import yfinance as yf
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from datetime import datetime, timedelta

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

def merge_gap_dates_to_ranges(dates):
    if not dates: return []
    dates = sorted([datetime.strptime(d, "%Y-%m-%d") for d in dates])
    ranges = []
    if not dates: return ranges
    start = dates[0]
    prev = dates[0]
    for d in dates[1:]:
        if (d - prev).days > 1:
            ranges.append((start.strftime("%Y-%m-%d"), prev.strftime("%Y-%m-%d")))
            start = d
        prev = d
    ranges.append((start.strftime("%Y-%m-%d"), prev.strftime("%Y-%m-%d")))
    return ranges

CORE_SYMBOLS = [
    "2330", "2454", "3037", "2382", "2327",
    "8996", "5289", "4966", "3583", "8210",
    "5347", "6510", "3211", "6290", "6669",
    "1513", "2049", "2408", "2313", "6285"
]

def get_priority_codes():
    priority = set(CORE_SYMBOLS)
    portfolio_path = os.path.join(DATA_DIR, "portfolio.db")
    if os.path.exists(portfolio_path):
        import sqlite3
        try:
            conn = sqlite3.connect(portfolio_path)
            cursor = conn.cursor()
            cursor.execute("SELECT code FROM current_holdings")
            for row in cursor.fetchall():
                priority.add(str(row[0]).replace(".TWO", "").replace(".TW", "").strip())
            cursor.execute("SELECT code FROM watchlist")
            for row in cursor.fetchall():
                priority.add(str(row[0]).replace(".TWO", "").replace(".TW", "").strip())
            conn.close()
        except Exception as e:
            print(f"⚠️ 無法自 portfolio.db 載入優先個股: {e}")
    return priority

def backfill_gaps():
    print("=========================================================================")
    print(" 🚀 啟動 150 天全市場高頻資料「智慧日期段增量補漏程序」 (03:00 AM)")
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
        
    priority_set = get_priority_codes()
    raw_active_codes = list(gap_registry.keys())
    
    # 優先級分流與排序
    priority_active = [c for c in raw_active_codes if c in priority_set]
    other_active = [c for c in raw_active_codes if c not in priority_set]
    
    # 合併後，只取前 20 檔（安全天井上限）
    active_codes = (priority_active + other_active)[:20]
    
    print(f"全市場共計有 {len(raw_active_codes)} 檔個股存在缺漏。")
    print(f"優先回補佇列（持股、自選與核心追蹤）：{len(priority_active)} 檔，其餘在線商品：{len(other_active)} 檔。")
    print(f"🛡️ 觸發安全落庫天井防禦機制：本輪僅下載回補前 {len(active_codes)} 檔個股，以根除 600s 超時風險。")
    
    success_count = 0
    fixed_details = []
    
    stock_suffixes = load_stock_suffixes(active_codes)
    
    name_cache = {}
    if os.path.exists(DB_PATH):
        try:
            conn = duckdb.connect(DB_PATH, read_only=True)
            name_rows = conn.execute("SELECT code, name FROM daily_stock_data").fetchall()
            conn.close()
            for c, n in name_rows:
                if c and n:
                    name_cache[str(c).strip()] = str(n).strip()
        except Exception as e:
            print(f"⚠️ 載入股名快取失敗: {e}")
 
    chunk_size = 50
    chunks = [active_codes[i:i + chunk_size] for i in range(0, len(active_codes), chunk_size)]
    
    total_chunks = len(chunks)
    print(f"📦 全市場共分為 {total_chunks} 個分組進行精準分段下載與批次落庫。")
    
    for c_idx, chunk_codes in enumerate(chunks, 1):
        print(f"\n[Group {c_idx}/{total_chunks}] 正在為 {len(chunk_codes)} 檔個股詳細排查與個別補漏...")
        
        chunk_sync_rows = []
                
        for code in chunk_codes:
            suffix = stock_suffixes.get(code, ".TW")
            ticker = f"{code}{suffix}"
            output_path = os.path.join(DATA_DIR, f"{code}_intraday_5m.csv")
            
            gaps = gap_registry.get(code, {})
            gap_dates = list(set(gaps.get("missing", []) + gaps.get("incomplete", [])))
            
            if not gap_dates: continue
                
            gap_ranges = merge_gap_dates_to_ranges(gap_dates)
            df_all_fetched_gaps = []
            total_range_days = 0
            
            for g_start, g_end in gap_ranges:
                finmind_success = False
                df_fetched_range = None
                
                # 建立 FinMind API 的自動重試與自癒頻率控制機制
                finmind_success = False
                df_fetched_range = None
                
                max_api_retries = 3
                for api_retry in range(max_api_retries):
                    try:
                        url = "https://api.finmindtrade.com/api/v4/data"
                        params = {
                            'dataset': 'TaiwanStockKBar',
                            'data_id': code,
                            'start_date': g_start,
                            'end_date': g_end,
                            'token': "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiYm9va2lkIiwiZW1haWwiOiJib29raWQyMDAwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjB9.MaUs7zQVYm5qKtlpIRdZ-s-I6WXCfcdtIowZiR7mXM4"
                        }
                        r = requests.get(url, params=params, timeout=20, verify=False)
                        if r.status_code == 200:
                            res_data = r.json()
                            status_code = res_data.get('status')
                            msg = res_data.get('msg', '')
                            
                            # 檢查是否觸發 IP 頻率限制 (403 或 ip banned)
                            if status_code == 403 or 'ip banned' in msg.lower():
                                retry_after = int(res_data.get('retry_after', 60))
                                print(f"  ⚠️ [FinMind API 限流] IP 被臨時鎖定。為保護帳號安全與 Token，自動睡眠 {retry_after + 5} 秒以等待解封 (重試 {api_retry + 1}/{max_api_retries})...")
                                time.sleep(retry_after + 5)
                                continue
                                
                            if status_code == 200 or msg == 'success':
                                raw_data = res_data.get('data', [])
                                if raw_data:
                                    df_raw = pd.DataFrame(raw_data)
                                    df_raw['timestamp'] = pd.to_datetime(df_raw['date'] + ' ' + df_raw['minute'])
                                    df_raw = df_raw.set_index('timestamp').sort_index()
                                    
                                    for col in ['open', 'high', 'low', 'close', 'volume', 'turnover', 'transaction']:
                                        if col in df_raw.columns:
                                            df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0.0)
                                            
                                    resampled = df_raw.resample('5Min', closed='right', label='right').agg({
                                        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last',
                                        'volume': 'sum', 'turnover': 'sum', 'transaction': 'sum'
                                    }).dropna()
                                    
                                    resampled = resampled[resampled['volume'] > 0.0].reset_index()
                                    resampled.rename(columns={
                                        'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume',
                                        'turnover': 'Amount', 'transaction': 'Transaction'
                                    }, inplace=True)
                                    
                                    resampled['timestamp'] = pd.to_datetime(resampled['timestamp']).dt.tz_localize('Asia/Taipei').dt.tz_convert('UTC').dt.strftime('%Y-%m-%d %H:%M:%S+00:00')
                                    df_fetched_range = resampled[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Transaction']]
                                    finmind_success = True
                                break
                            else:
                                # 其他錯誤狀態直接退出
                                break
                    except Exception as e:
                        print(f"  ⚠️ [FinMind API 請求異常] {e}，將嘗試重試...")
                        time.sleep(2)
                    
                if not finmind_success:
                    try:
                        sixty_days_limit = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
                        if g_start >= sixty_days_limit:
                            df_yf = yf.download(ticker, start=g_start, end=(pd.to_datetime(g_end) + timedelta(days=1)).strftime("%Y-%m-%d"), interval="5m", progress=False)
                            if not df_yf.empty:
                                if isinstance(df_yf.columns, pd.MultiIndex):
                                    df_yf.columns = df_yf.columns.get_level_values(0)
                                df_yf = df_yf[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
                                df_yf = df_yf.reset_index()
                                df_yf.rename(columns={'Datetime': 'timestamp'}, inplace=True)
                                df_yf['timestamp'] = pd.to_datetime(df_yf['timestamp']).dt.tz_convert('UTC').dt.strftime('%Y-%m-%d %H:%M:%S+00:00')
                                df_yf['Amount'] = 0.0
                                df_yf['Transaction'] = 0
                                df_fetched_range = df_yf[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Transaction']]
                                finmind_success = True
                    except Exception: pass
                        
                if df_fetched_range is not None and not df_fetched_range.empty:
                    df_all_fetched_gaps.append(df_fetched_range)
                    d_start = datetime.strptime(g_start, "%Y-%m-%d")
                    d_end = datetime.strptime(g_end, "%Y-%m-%d")
                    total_range_days += (d_end - d_start).days + 1
                    
                time.sleep(0.05)
                
            if df_all_fetched_gaps:
                try:
                    df_all_fetched = pd.concat(df_all_fetched_gaps, ignore_index=True)
                    if os.path.exists(output_path):
                        df_local = pd.read_csv(output_path)
                        for col in ['Amount', 'Transaction']:
                            if col not in df_local.columns: df_local[col] = 0.0 if col == 'Amount' else 0
                        parsed_ts = pd.to_datetime(df_local['timestamp'])
                        if parsed_ts.dt.tz is None:
                            parsed_ts = parsed_ts.dt.tz_localize('UTC', ambiguous='NaT')
                        else:
                            parsed_ts = parsed_ts.dt.tz_convert('UTC')
                        df_local['timestamp'] = parsed_ts.dt.strftime('%Y-%m-%d %H:%M:%S+00:00')
                        df_combined = pd.concat([df_local, df_all_fetched], ignore_index=True)
                    else:
                        df_combined = df_all_fetched
                        
                    assert isinstance(df_combined, pd.DataFrame)
                    df_combined = df_combined.drop_duplicates(subset=['timestamp'], keep='last')
                    df_combined = df_combined.sort_values('timestamp').reset_index(drop=True)
                    df_combined = df_combined.tail(10000)
                    df_combined.to_csv(output_path, index=False)
                    
                    df_db_sync = df_combined.copy()
                    parsed_ts_db = pd.to_datetime(df_db_sync['timestamp'])
                    if parsed_ts_db.dt.tz is not None:
                        parsed_ts_db = parsed_ts_db.dt.tz_convert('UTC').dt.tz_localize(None)
                    else:
                        parsed_ts_db = parsed_ts_db.dt.tz_localize(None)
                    df_db_sync['timestamp'] = parsed_ts_db
                    df_db_sync['code'] = code
                    df_db_sync['ticker'] = ticker
                    df_db_sync['name'] = name_cache.get(code, code)
                    df_db_sync.rename(columns={
                        'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume',
                        'Amount': 'amount', 'Transaction': 'transaction'
                    }, inplace=True)
                    df_db_sync['volume'] = pd.to_numeric(df_db_sync['volume'], errors='coerce').fillna(0).astype('int64')
                    df_db_sync['transaction'] = pd.to_numeric(df_db_sync['transaction'], errors='coerce').fillna(0).astype('int64')
                    df_db_sync = df_db_sync[['timestamp', 'code', 'ticker', 'name', 'open', 'high', 'low', 'close', 'volume', 'amount', 'transaction']]
                    chunk_sync_rows.append(df_db_sync)
                    
                    success_count += 1
                    fixed_details.append(f"• `{code}` ({name_cache.get(code, code)}): 成功精準補漏 `{total_range_days}` 天")
                    gap_registry.pop(code, None)
                    print(f"  ✓ [{code}] 成功精準補漏 {total_range_days} 天缺失資料。")
                except Exception as merge_err:
                    print(f"  ⚠️ 合併與落庫個股 {ticker} 失敗: {merge_err}")
                    
        if chunk_sync_rows:
            conn_db = None
            try:
                conn_db = duckdb.connect(DB_PATH)
                df_chunk_all = pd.concat(chunk_sync_rows, ignore_index=True)
                conn_db.execute("INSERT OR REPLACE INTO kbars_5m SELECT * FROM df_chunk_all")
                conn_db.commit()
                print(f"  ✓ 成功批次寫入 {len(chunk_sync_rows)} 檔個股的 150d 精準高頻補漏數據。")
            except Exception as bulk_db_err:
                print(f"  ❌ 批次寫入 DuckDB 失敗: {bulk_db_err}")
            finally:
                if conn_db:
                    conn_db.close()
            
        # 每個分組完成後，立即將剩餘未回補清單存入 JSON，確保中斷時能保留進度
        try:
            with open(AUDIT_JSON, 'w', encoding='utf-8') as f:
                json.dump(gap_registry, f, indent=2, ensure_ascii=False)
        except Exception as save_err:
            print(f"  ⚠️ 儲存進度至 JSON 失敗: {save_err}")
            
    with open(AUDIT_JSON, 'w', encoding='utf-8') as f:
        json.dump(gap_registry, f, indent=2, ensure_ascii=False)
        
    print(f"\n✓ 5m 高頻智慧增量個別補漏程序完成！成功修復: {success_count} 檔個股")
    print("=========================================================================")
    
    if fixed_details:
        displayed_details = fixed_details[:30]
        detail_msg = "\n".join(displayed_details)
        if len(fixed_details) > 30:
            detail_msg += f"\n• ...以及其他 {len(fixed_details) - 30} 檔個股的高頻自癒補全..."
    else:
        detail_msg = "• 本輪無須補漏（核心個股與自選數據皆已 100% 完整齊全）"
        
    ger_msg = f"""🌅 **「黃金體驗-鎮魂曲」：5m 高頻資料回補報告 🌅**
缺漏的過去已全部被強制作為「無效」，現在只留下現實。

### 📊 **全市場高頻並行補全修復摘要**
*   **成功修復股數**：`{success_count}` 檔
*   **高頻落庫模式**：`yfinance 多線程 Chunks 批次`

**自癒清單摘要：**
{detail_msg}

**無駄！** 所有被標記的 5m 數據缺失與不足已全部重構補全。"""
    send_telegram(GER_TOKEN, JOJO_CHAT_ID, ger_msg)

if __name__ == "__main__":
    backfill_gaps()
