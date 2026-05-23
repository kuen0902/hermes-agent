#!/Users/bookid/.hermes/.venv/bin/python
import os
import yfinance as yf
import pandas as pd
import subprocess

DATA_DIR = os.path.expanduser("~/.hermes/data")
OUTPUT_5M_PATH = os.path.join(DATA_DIR, "2303_intraday_5m.csv")

def backfill_5m_data():
    print("--- 啟動聯電 (2303.TW) 5分鐘高頻 K 線資料補全計畫 ---")
    ticker = "2303.TW"
    
    print(f"正在從 yfinance 下載 {ticker} 過去 60 天 (API 支援之最大限制) 的 5m 資料...")
    try:
        df = yf.download(ticker, period="60d", interval="5m", progress=False)
        if df.empty:
            print("❌ yfinance 返回空資料，補全失敗。")
            return False
            
        # Flatten MultiIndex if returned
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
        df = df.reset_index()
        df.rename(columns={'Datetime': 'timestamp'}, inplace=True)
        
        # Save to common location
        df.to_csv(OUTPUT_5M_PATH, index=False)
        print(f"✓ 成功將聯電 60 天 5 分鐘高頻資料儲存至: {OUTPUT_5M_PATH} ({len(df)} 筆記錄)")
        return True
    except Exception as e:
        print(f"❌ 下載五分資料時發生錯誤: {e}")
        return False

def sync_duckdb_institutional():
    print("\n--- 啟動三大法人 DuckDB 資料庫數據同步與校準 ---")
    init_db_script = os.path.expanduser("~/.hermes/scripts/ml/init_potential_db.py")
    
    if not os.path.exists(init_db_script):
        print(f"❌ 找不到 DuckDB 初始化腳本: {init_db_script}")
        return False
        
    try:
        print("正在將所有新下載的三大法人與價量 CSV 向量化批量重新載入 DuckDB...")
        result = subprocess.run(
            ["/Users/bookid/.hermes/.venv/bin/python", init_db_script],
            capture_output=True,
            text=True,
            check=True
        )
        print("✓ DuckDB 向量化 bulk 導入成功！")
        return True
    except Exception as e:
        print(f"❌ 執行 DuckDB 同步時發生錯誤: {e}")
        return False

if __name__ == "__main__":
    backfill_5m_data()
    sync_duckdb_institutional()
