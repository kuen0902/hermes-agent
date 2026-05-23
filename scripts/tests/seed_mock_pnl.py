#!/Users/bookid/.hermes/.venv/bin/python
import os
import sqlite3
from datetime import datetime, timedelta

DATA_DIR = os.path.expanduser("~/.hermes/data")
DB_PATH = os.path.join(DATA_DIR, "portfolio.db")

MOCK_TRADES = [
    ("2409", "友達", 5.0, 18.2, 19.5, "2026-05-02T11:30:00"),
    ("3481", "群創", 10.0, 13.5, 14.8, "2026-05-05T10:15:00"),
    ("1513", "中興電", 2.0, 150.0, 158.5, "2026-05-07T13:20:00"),
    ("5347", "世界", 3.0, 110.0, 108.0, "2026-05-09T09:45:00"), # 虧損
    ("2330", "台積電", 1.0, 810.0, 835.0, "2026-05-12T10:00:00"),
    ("2382", "廣達", 3.0, 270.0, 282.5, "2026-05-14T11:05:00"),
    ("2454", "聯發科", 1.0, 1200.0, 1260.0, "2026-05-16T12:40:00"),
    ("3037", "欣興", 4.0, 165.0, 172.0, "2026-05-18T10:50:00"),
    ("2049", "上銀", 2.0, 240.0, 235.0, "2026-05-20T09:15:00"), # 虧損
    ("2313", "華通", 5.0, 72.0, 78.5, "2026-05-21T13:10:00"),
    ("4543", "萬在", 3.0, 38.5, 41.2, "2026-05-22T10:30:00"),
]

def seed_database():
    if not os.path.exists(DB_PATH):
        print(f"資料庫不存在: {DB_PATH}")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 檢查是否有資料
    cursor.execute("SELECT COUNT(*) FROM pnl_history")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"pnl_history 中已有 {count} 筆紀錄，跳過種子資料導入。")
        conn.close()
        return
        
    print("正在寫入高仿真模擬歷史手動平倉交易紀錄...")
    for code, name, qty, buy_price, sell_price, closed_at in MOCK_TRADES:
        # 計算已實現損益: (sell - buy) * qty * 1000
        pnl = round((sell_price - buy_price) * qty * 1000, 2)
        cursor.execute('''
            INSERT INTO pnl_history (code, name, sell_qty, buy_price, sell_price, realized_pnl, closed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (code, name, qty, buy_price, sell_price, pnl, closed_at))
        print(f" ⨀ 已寫入 {name}({code}) -> 平倉 {qty}張, PnL: {pnl:+,} 元")
        
    conn.commit()
    conn.close()
    print("✓ 種子資料寫入成功！")

if __name__ == "__main__":
    seed_database()
