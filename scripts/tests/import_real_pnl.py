#!/Users/bookid/.hermes/.venv/bin/python
import os
import sqlite3
import pandas as pd
import glob
from datetime import datetime

DATA_DIR = os.path.expanduser("~/.hermes/data")
DB_PATH = os.path.join(DATA_DIR, "portfolio.db")
EXCEL_PATTERN = "/Users/bookid/Downloads/已實現損益*.xlsx"

def import_all_excel_data():
    print("--- 啟動全歷史已實現損益批次合併與導入引擎 ---")
    
    # 1. 搜尋所有已實現損益 Excel 檔案
    excel_files = glob.glob(EXCEL_PATTERN)
    if not excel_files:
        print(f"❌ 在 Downloads 資料夾中找不到任何符合 {EXCEL_PATTERN} 的檔案。")
        return False
        
    print(f"發現以下 {len(excel_files)} 個已實現損益 Excel 檔案，即將進行合併與去重：")
    for f in excel_files:
        print(f" - {os.path.basename(f)}")
        
    if not os.path.exists(DB_PATH):
        print(f"❌ 找不到資料庫: {DB_PATH}")
        return False
        
    try:
        # 2. 讀取並合併所有 Excel 檔案
        dfs = []
        for file_path in excel_files:
            df = pd.read_excel(file_path)
            dfs.append(df)
            
        combined_df = pd.concat(dfs, ignore_index=True)
        print(f"合併完成，原始記錄共 {len(combined_df)} 筆。")
        
        # 3. 建立特徵鍵進行資料精準去重 (Deduplication)
        # 用成交日期、商品、成交股數、投資損益建立唯一的 Signature
        combined_df['dedup_key'] = (
            combined_df['成交日期'].astype(str) + '_' + 
            combined_df['商品'].astype(str) + '_' + 
            combined_df['成交股數'].astype(str) + '_' + 
            combined_df['投資損益'].astype(str)
        )
        
        unique_df = combined_df.drop_duplicates(subset=['dedup_key']).copy()
        print(f"去重完成，篩選出 100% 獨立的真實交易記錄共 {len(unique_df)} 筆。")
        
        # 4. 數值欄位格式清洗與轉換
        def clean_val(val):
            if pd.isna(val):
                return 0.0
            if isinstance(val, (int, float)):
                return float(val)
            val_str = str(val).replace(',', '').strip()
            return float(val_str)
            
        unique_df['成交股數'] = unique_df['成交股數'].apply(clean_val)
        unique_df['投入成本'] = unique_df['投入成本'].apply(clean_val)
        unique_df['賣出金額'] = unique_df['賣出金額'].apply(clean_val)
        unique_df['投資損益'] = unique_df['投資損益'].apply(clean_val)
        
        # 5. 連接資料庫並清空原有數據
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("正在清除資料庫歷史損益數據 (pnl_history)...")
        cursor.execute("DELETE FROM pnl_history")
        
        # 6. 按成交日期由舊到新排序，確保時序累加與繪圖的正確性
        unique_df['parsed_date'] = pd.to_datetime(unique_df['成交日期'])
        unique_df_sorted = unique_df.sort_values(by='parsed_date', ascending=True)
        
        inserted_count = 0
        total_realized_pnl = 0.0
        
        for _, row in unique_df_sorted.iterrows():
            prod_str = str(row['商品']).strip()
            if '/' not in prod_str:
                print(f"⚠️ 商品格式錯誤，跳過: {prod_str}")
                continue
                
            parts = prod_str.split('/')
            name = parts[0].strip()
            code = parts[1].strip()
            
            # 成交股數轉為「張」
            shares = row['成交股數']
            qty = round(shares / 1000.0, 3)
            
            # 計算平均買入與賣出單價
            buy_price = round(row['投入成本'] / shares, 2) if shares > 0 else 0.0
            sell_price = round(row['賣出金額'] / shares, 2) if shares > 0 else 0.0
            
            realized_pnl = row['投資損益']
            total_realized_pnl += realized_pnl
            
            # 轉換為標準 closed_at ISO 時間格式 (設定在當日下午 13:30 收盤時間)
            closed_at = row['parsed_date'].strftime("%Y-%m-%dT13:30:00.000000")
            
            cursor.execute('''
                INSERT INTO pnl_history (code, name, sell_qty, buy_price, sell_price, realized_pnl, closed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (code, name, qty, buy_price, sell_price, realized_pnl, closed_at))
            
            inserted_count += 1
            
        conn.commit()
        conn.close()
        
        print(f"✓ 歷史交易紀錄合併導入成功！共導入 {inserted_count} 筆交易。")
        print(f"🏆 九個月歷史累計已實現淨損益: {total_realized_pnl:+,.2f} 元。")
        return True
        
    except Exception as e:
        print(f"❌ 歷史數據合併與導入失敗: {e}")
        return False

if __name__ == "__main__":
    import_all_excel_data()
