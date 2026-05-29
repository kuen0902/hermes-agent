#!/Users/bookid/.hermes/.venv/bin/python
import os
import sys
import json
import io
import re
import glob
import time
import random
import requests
import pandas as pd
import duckdb
from datetime import datetime

# Paths
DATA_DIR = os.path.expanduser("~/.hermes/data")
DB_PATH = os.path.join(DATA_DIR, "potential_analysis.ddb")
RETAINED_MD = os.path.join(DATA_DIR, "active_retained_stocks.md")
SUCCESS_REGISTRY_JSON = os.path.join(DATA_DIR, "backfill_success_registry.json")
FULL_CSV_DIR = os.path.join(DATA_DIR, "StockData_History_Full")
FINAL_CSV_DIR = os.path.join(DATA_DIR, "StockData_History_Final")

os.makedirs(FULL_CSV_DIR, exist_ok=True)

# 20 years timestamps for Yahoo
END_TS = int(time.time())
START_TS = END_TS - (20 * 365 * 24 * 3600)

# Date strings for FinMind
START_DATE_STR = "2006-01-01"
END_DATE_STR = datetime.now().strftime("%Y-%m-%d")

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0"
]

def get_retained_stocks():
    """Loads and parses stocks from active_retained_stocks.md"""
    if not os.path.exists(RETAINED_MD):
        print(f"❌ 找不到保留股審查清單: {RETAINED_MD}")
        return {}
    try:
        content = open(RETAINED_MD, "r", encoding="utf-8").read()
        # Parse: | <seq> | <code> | <ticker> | <name> | ...
        rows = re.findall(r'\|\s*\d+\s*\|\s*(\w+)\s*\|\s*([\w\.]+)\s*\|\s*([^\|]+)', content)
        stocks = {}
        for r in rows:
            code = r[0].strip()
            ticker = r[1].strip()
            name = r[2].strip()
            stocks[code] = {"ticker": ticker, "name": name}
        return stocks
    except Exception as e:
        print(f"❌ 讀取/解析保留股清單失敗: {e}")
        return {}

def load_success_registry(conn, stocks):
    """Loads success registry, auto-populating old stocks with >2000 rows as successful"""
    registry = set()
    
    if os.path.exists(SUCCESS_REGISTRY_JSON):
        try:
            with open(SUCCESS_REGISTRY_JSON, "r", encoding="utf-8") as f:
                registry = set(json.load(f))
        except Exception:
            pass

    for code in stocks.keys():
        if code in registry:
            continue
        try:
            res = conn.execute("SELECT count(*) FROM full_daily_prices WHERE code = ?", (code,)).fetchone()
            if res and res[0] > 2000:
                registry.add(code)
        except Exception:
            pass

    save_success_registry(registry)
    return registry

def save_success_registry(registry):
    """Saves success registry to JSON file"""
    try:
        with open(SUCCESS_REGISTRY_JSON, "w", encoding="utf-8") as f:
            json.dump(sorted(list(registry)), f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ 無法寫入成功回補紀錄檔: {e}")

def fetch_finmind_history(code, name, ticker):
    """Downloads full history directly from FinMind Open Data API (Aggregated TWSE/TPEx Data)"""
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": code,
        "start_date": START_DATE_STR,
        "end_date": END_DATE_STR
    }
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    
    try:
        r = requests.get(url, params=params, headers=headers, timeout=12)
        if r.status_code == 200:
            res_data = r.json()
            if res_data.get("status") == 200 and res_data.get("data"):
                raw_data = res_data["data"]
                df = pd.DataFrame(raw_data)
                
                df = df.rename(columns={
                    "date": "date",
                    "open": "open",
                    "max": "high",
                    "min": "low",
                    "close": "close",
                    "Trading_Volume": "volume"
                })
                
                df["code"] = code
                df["ticker"] = ticker
                df["name"] = name
                df["adj_close"] = df["close"]
                df["date"] = pd.to_datetime(df["date"]).dt.date
                
                df = df[["date", "code", "ticker", "name", "open", "high", "low", "close", "adj_close", "volume"]]
                for col in ["open", "high", "low", "close", "adj_close", "volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df = df.dropna(subset=["date", "open", "high", "low", "close", "volume"])
                df["volume"] = df["volume"].astype("int64")
                
                if not df.empty:
                    print(f"  ⚡ 管道 5 成功抓取 (FinMind 證交所鏡像源)！")
                    return df
    except Exception:
        pass
    return None

def fetch_yahoo_history(ticker, name):
    """Downloads 20-year history with 4 levels of Yahoo fallbacks"""
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    
    channels = [
        {"type": "json", "url": f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}", "params": {"range": "20y", "interval": "1d"}},
        {"type": "json", "url": f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}", "params": {"range": "20y", "interval": "1d"}},
        {"type": "csv", "url": f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}", "params": {"period1": START_TS, "period2": END_TS, "interval": "1d", "events": "history", "includeAdjustedClose": "true"}},
        {"type": "csv", "url": f"https://query2.finance.yahoo.com/v7/finance/download/{ticker}", "params": {"period1": START_TS, "period2": END_TS, "interval": "1d", "events": "history", "includeAdjustedClose": "true"}}
    ]
    
    for idx, ch in enumerate(channels, 1):
        try:
            url = ch["url"]
            params = ch["params"]
            if isinstance(url, str) and isinstance(params, dict):
                r = requests.get(url, params=params, headers=headers, timeout=12)
            else:
                continue
            if r.status_code == 200:
                if ch["type"] == "json":
                    df = _parse_json(r.json(), ticker, name)
                else:
                    df = _parse_csv(r.text, ticker, name)
                    
                if df is not None and not df.empty:
                    ch_name = "JSON_Query1" if idx==1 else "JSON_Query2" if idx==2 else "CSV_Query1" if idx==3 else "CSV_Query2"
                    print(f"  ⚡ 管道 {idx} 成功抓取 ({ch_name})！")
                    return df
        except Exception:
            pass
            
    if ticker.endswith(".TW") and not ticker.startswith("00"):
        alt_ticker = ticker.replace(".TW", ".TWO")
        print(f"🔄 嘗試備用市場代碼 {alt_ticker}...")
        return fetch_yahoo_history(alt_ticker, name)
        
    return None

def _parse_json(data, ticker, name):
    try:
        result = data["chart"]["result"][0]
        timestamps = result.get("timestamp", [])
        indicators = result.get("indicators", {}).get("quote", [{}])[0]
        adj_close = result.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])
        
        if not timestamps:
            return None
            
        df = pd.DataFrame({
            "date": [datetime.fromtimestamp(ts).date() for ts in timestamps],
            "open": indicators.get("open", []),
            "high": indicators.get("high", []),
            "low": indicators.get("low", []),
            "close": indicators.get("close", []),
            "adj_close": adj_close if adj_close else indicators.get("close", []),
            "volume": indicators.get("volume", [])
        })
        
        df["code"] = ticker.split(".")[0]
        df["ticker"] = ticker
        df["name"] = name
        
        for col in ["open", "high", "low", "close", "adj_close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            
        df = df.dropna(subset=["date", "open", "high", "low", "close", "volume"])
        df["volume"] = df["volume"].astype("int64")
        return df
    except Exception:
        return None

def _parse_csv(csv_text, ticker, name):
    try:
        df = pd.read_csv(io.StringIO(csv_text))
        if df.empty or "Date" not in df.columns:
            return None
            
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        df = df.rename(columns={"adj_close**": "adj_close", "date": "date"})
        
        df["code"] = ticker.split(".")[0]
        df["ticker"] = ticker
        df["name"] = name
        df["date"] = pd.to_datetime(df["date"]).dt.date
        
        df = df[["date", "code", "ticker", "name", "open", "high", "low", "close", "adj_close", "volume"]]
        
        for col in ["open", "high", "low", "close", "adj_close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            
        df = df.dropna(subset=["date", "open", "high", "low", "close", "volume"])
        df["volume"] = df["volume"].astype("int64")
        return df
    except Exception:
        return None

def main():
    print("=========================================================================")
    print("  🦆 HERMES QUANT: 全市場在線保留個股 15 年歷史日線分批回補引擎 (v2.0)")
    print("=========================================================================")
    
    # Default batch size limit: 100 stocks
    batch_limit = 100
    for arg in sys.argv:
        if arg.startswith("--batch-size="):
            try:
                batch_limit = int(arg.split("=")[1])
            except ValueError:
                pass
                
    print(f"💡 系統優化：已內建分批執行模式，本次最多僅處理前 {batch_limit} 檔個股。")
    print("💡 下載機制：5 種極致備援管道 + 智慧略過已完成個股")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ 找不到 DuckDB 資料庫: {DB_PATH}")
        sys.exit(1)
        
    stocks = get_retained_stocks()
    if not stocks:
        if os.path.exists(RETAINED_MD):
            print("🎉 所有保留股已回補完畢，或審查清單無剩餘待處理個股，程序結束。")
            sys.exit(0)
        else:
            print("❌ 找不到保留股審查清單，程序結束。")
            sys.exit(1)
        
    conn = duckdb.connect(DB_PATH)
    
    # 確保資料表存在
    conn.execute("""
        CREATE TABLE IF NOT EXISTS full_daily_prices (
            date DATE,
            code VARCHAR,
            ticker VARCHAR,
            name VARCHAR,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            adj_close DOUBLE,
            volume BIGINT,
            PRIMARY KEY (date, code)
        )
    """)
    
    # 載入成功回補紀錄
    success_registry = load_success_registry(conn, stocks)
    
    # 篩選出尚未成功回補的股票
    pending_stocks_all = {k: v for k, v in stocks.items() if k not in success_registry}
    
    print(f"📌 當前審查在線活躍商品共 {len(stocks)} 檔。")
    print(f"✨ 已累計成功回補 {len(success_registry)} 檔 (自動略過)。")
    print(f"⏳ 全市場剩餘待補全商品共 {len(pending_stocks_all)} 檔。")
    
    if not pending_stocks_all:
        print("\n🎉 所有審查在線個股已全部成功回補完畢！無須再次下載。")
        conn.close()
        sys.exit(0)
        
    # Limit to current batch size
    pending_stocks = dict(list(pending_stocks_all.items())[:batch_limit])
    print(f"🚀 [分批下載啟動] 本批次將處理前 {len(pending_stocks)} 檔待補全個股。")
    
    success_count = 0
    
    for idx, (code, info) in enumerate(pending_stocks.items(), 1):
        ticker = info["ticker"]
        name = info["name"]
        print(f"\n[{idx}/{len(pending_stocks)}] 正在處理: {name} ({code}) ➔ 解析代碼: {ticker}")
        
        # 取得舊筆數
        try:
            res_old = conn.execute("SELECT count(*) FROM full_daily_prices WHERE ticker = ?", (ticker,)).fetchone()
            old_cnt = res_old[0] if res_old is not None else 0
        except Exception:
            old_cnt = 0
            
        # 1. Try Yahoo
        df = fetch_yahoo_history(ticker, name)
        
        # 2. Try FinMind Fallback
        if df is None or df.empty:
            print("  ⚠️ Yahoo 管道全數受限，啟動 FinMind (TWSE/TPEx 官方源) 進行直連物理回補...")
            df = fetch_finmind_history(code, name, ticker)
            
        if df is not None and not df.empty:
            real_ticker = df["ticker"].iloc[0]
            real_name = name.replace("/", "_")
            
            try:
                # 寫入 DuckDB
                df_db = df[["date", "code", "ticker", "name", "open", "high", "low", "close", "adj_close", "volume"]]
                conn.execute("INSERT OR REPLACE INTO full_daily_prices SELECT * FROM df_db")
                
                res_new = conn.execute("SELECT count(*) FROM full_daily_prices WHERE ticker = ?", (real_ticker,)).fetchone()
                new_cnt = res_new[0] if res_new is not None else 0
                added = new_cnt - old_cnt
                
                # 同步寫入 CSV 快取備份
                csv_path = os.path.join(FULL_CSV_DIR, f"{real_ticker}_{real_name}.csv")
                df_csv = df[["date", "open", "high", "low", "close", "adj_close", "volume"]].copy()
                df_csv.columns = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
                df_csv.to_csv(csv_path, index=False)
                
                # 寫入成功紀錄檔
                success_registry.add(code)
                save_success_registry(success_registry)
                
                print(f"  🟢 成功匯入！舊筆數: {old_cnt} ➔ 新筆數: {new_cnt} (新增/覆蓋 {added} 筆)")
                success_count += 1
            except Exception as e:
                print(f"  ❌ 寫入資料庫/CSV 失敗: {e}")
        else:
            print(f"  ❌ 無法取得歷史價格，所有 5 種備援管道皆已失敗。")
            
        # 禮貌間隔，防範 IP 封鎖
        time.sleep(random.uniform(0.3, 0.5))
        
    conn.close()
    
    print("\n" + "="*80)
    print("  🎉 批次保留活躍自選股歷史資料回補程序執行完畢")
    print("="*80)
    print(f"【執行結果】本批次成功回補: {success_count} / {len(pending_stocks)} 檔個股")
    print(f"【累積進度】全市場已累計完成: {len(success_registry)} / {len(stocks)} 檔個股")
    print(f"💡 貼心提醒：還有 {len(pending_stocks_all) - success_count} 檔個股待下載，下次執行將自動接續！")
    print("="*80)

if __name__ == "__main__":
    main()
