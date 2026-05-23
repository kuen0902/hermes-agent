#!/Users/bookid/.hermes/.venv/bin/python
import os
import glob
import pandas as pd
import duckdb
import argparse

# Configuration
DATA_DIR = os.path.expanduser("~/.hermes/data")
SAVE_DIR = os.path.expanduser("~/Documents/StockData_History_5Y")
DB_PATH = os.path.join(DATA_DIR, "potential_analysis.ddb")

def prune_csv_files(dry_run=False):
    print("=========================================================================")
    print(f"  🧹 啟動「已同步 CSV 資料」安全清理與空間釋放計畫 ({'DRY RUN' if dry_run else '實體執行'})")
    print("=========================================================================")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ 找不到 DuckDB 資料庫: {DB_PATH}，無法執行審計，取消清理。")
        return
        
    try:
        conn = duckdb.connect(DB_PATH)
    except Exception as e:
        print(f"❌ 無法連接至 DuckDB: {e}，取消清理。")
        return
        
    deleted_count = 0
    deleted_bytes = 0
    preserved_count = 0
    
    # 1. 審查 ~/Documents/StockData_History_5Y/ 底下的每日 CSV 檔案
    daily_csv_files = glob.glob(os.path.join(SAVE_DIR, "*.csv"))
    print(f"\n正在掃描 {SAVE_DIR} 目錄中的 {len(daily_csv_files)} 個每日價量與法人 CSV...")
    
    for f in daily_csv_files:
        try:
            basename = os.path.basename(f)
            # Ticker extraction: e.g. 2303.TW_聯電.csv
            ticker = basename.split('_')[0]
            code = ticker.split('.')[0]
            
            # Read CSV rows to verify
            df = pd.read_csv(f, nrows=2)
            
            # Check if this is a daily price file (should have Open, Close, and Date)
            if 'Date' in df.columns and 'Close' in df.columns:
                # Query DuckDB daily_stock_data to verify row count
                res = conn.execute("SELECT count(*) FROM daily_stock_data WHERE code=?", (code,)).fetchone()
                db_rows = res[0] if res else 0
                
                # If db has data, read full CSV length to check
                if db_rows > 0:
                    df_full = pd.read_csv(f)
                    csv_rows = len(df_full)
                    
                    # Safe prune condition: DuckDB row count is at least equal to CSV row count
                    if db_rows >= csv_rows:
                        file_size = os.path.getsize(f)
                        deleted_count += 1
                        deleted_bytes += file_size
                        if not dry_run:
                            os.remove(f)
                            # Re-write an empty/dummy placeholder or completely delete?
                            # Completely deleting is cleaner as DuckDB is the source of truth.
                            print(f"  ✓ [已刪除] 已同步之日 K 線與籌碼 CSV: {basename} ({file_size/1024:.1f} KB)")
                        else:
                            print(f"  ✦ [模擬刪除] 已同步之日 K 線與籌碼 CSV: {basename} ({file_size/1024:.1f} KB)")
                    else:
                        print(f"  ℹ️ [保留] DuckDB 筆數 ({db_rows}) 少於 CSV 筆數 ({csv_rows})，數據未完全同步: {basename}")
                        preserved_count += 1
                else:
                    print(f"  ℹ️ [保留] DuckDB 中無此股票數據: {basename}")
                    preserved_count += 1
            else:
                print(f"  ℹ️ [保留] 非日 K 線格式 CSV: {basename}")
                preserved_count += 1
        except Exception as e:
            print(f"  ⚠️ 讀取/處理 {basename} 時發生錯誤: {e}")
            preserved_count += 1
            
    # 2. 審查 ~/.hermes/data/ 底下的五分高頻 CSV 檔案
    data_csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    print(f"\n正在掃描 {DATA_DIR} 目錄中的 {len(data_csv_files)} 個盤中與五分高頻 CSV...")
    
    for f in data_csv_files:
        basename = os.path.basename(f)
        # 5m K 線資料與盤中 Log 資料庫中無對應 tables，必須智慧保留！
        print(f"  ℹ️ [智慧保留] 未同步至 DuckDB (5m 高頻快取/盤中快照) 之 CSV: {basename}")
        preserved_count += 1
        
    conn.close()
    
    print("\n=========================================================================")
    print("  📊 清理報告摘要：")
    print(f"  - 成功刪除實體 CSV 檔案數量：{deleted_count} 檔")
    print(f"  - 釋放硬碟空間：{deleted_bytes / (1024 * 1024):.2f} MB")
    print(f"  - 智慧安全保留 CSV 檔案數量：{preserved_count} 檔")
    print("=========================================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prune safely synchronized daily CSVs.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate deletion without removing files.")
    args = parser.parse_args()
    
    prune_csv_files(dry_run=args.dry_run)
