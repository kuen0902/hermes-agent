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

def get_stock_suffix(code):
    # Determine suffix based on database or mapping
    # By default, check if we can query daily_stock_data to find if it has TW or TWO
    suffix = ".TW"
    if os.path.exists(DB_PATH):
        try:
            conn = duckdb.connect(DB_PATH, read_only=True)
            res = conn.execute("SELECT ticker FROM daily_stock_data WHERE code = ? LIMIT 1", (code,)).fetchone()
            conn.close()
            if res and res[0]:
                if ".TWO" in res[0]:
                    suffix = ".TWO"
        except:
            pass
    return suffix

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
    
    for code, gaps in list(gap_registry.items()):
        suffix = get_stock_suffix(code)
        ticker = f"{code}{suffix}"
        output_path = os.path.join(DATA_DIR, f"{code}_intraday_5m.csv")
        
        total_gaps_days = len(gaps.get("missing", [])) + len(gaps.get("incomplete", []))
        print(f"\n[補全] {ticker} ... 缺漏/不足天數: {total_gaps_days} 天")
        
        # 1. 下載完整的 60 天 5m 數據 (覆蓋所有缺漏日)
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
            df_yf_clean = df_yf[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']]
            
            # 2. 合併本地已有的 CSV 資料以防遺失更久以前的快取
            if os.path.exists(output_path):
                try:
                    df_local = pd.read_csv(output_path)
                    df_local['timestamp'] = pd.to_datetime(df_local['timestamp']).dt.tz_localize('UTC', ambiguous='NaT').dt.strftime('%Y-%m-%d %H:%M:%S+00:00')
                    df_combined = pd.concat([df_local, df_yf_clean], ignore_index=True)
                    df_combined = df_combined.drop_duplicates(subset=['timestamp'], keep='last')
                    df_combined = df_combined.sort_values('timestamp').reset_index(drop=True)
                except Exception as merge_err:
                    print(f"  ⚠️ 合併本地資料失敗，採用最新下載資料: {merge_err}")
                    df_combined = df_yf_clean
            else:
                df_combined = df_yf_clean
                
            # 3. 限制長度並寫回 CSV
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
                        'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'
                    }, inplace=True)
                    
                    df_db_sync = df_db_sync[['timestamp', 'code', 'ticker', 'name', 'open', 'high', 'low', 'close', 'volume']]
                    
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
            print(f"  ❌ 處理 {ticker} 發生異常: {e}")
            
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
