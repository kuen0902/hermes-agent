#!/Users/bookid/.hermes/.venv/bin/python
# -*- coding: utf-8 -*-
import sqlite3
import sys
import os

def print_help():
    print("使用方式: qdb [資料庫路徑] [可選: 資料表名稱]")
    print("或直接:  qdb [資料表名稱]  (會使用預設 portfolio.db)")
    print("預設路徑: ~/.hermes/data/portfolio.db")

def main():
    db_path = os.path.expanduser("~/.hermes/data/portfolio.db")
    target_table = None
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ["-h", "--help"]:
            print_help()
            return
        
        # 判斷第一個參數是否為現存檔案
        possible_path = os.path.expanduser(sys.argv[1])
        if os.path.exists(possible_path):
            db_path = possible_path
            if len(sys.argv) > 2:
                target_table = sys.argv[2]
        else:
            # 第一個參數不是檔案，當作預設資料庫中的 Table 名稱
            target_table = sys.argv[1]

    if not os.path.exists(db_path):
        print(f"\033[1;31m❌ 找不到資料庫檔案: {db_path}\033[0m")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 取得所有 Table 資訊
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cursor.fetchall() if r[0] != 'sqlite_sequence']
        
        print("\033[1;36m=== 🗄️ SQLite Quick Look ===\033[0m")
        print(f"📍 資料庫位置: {db_path}")
        print(f"📊 共有 {len(tables)} 個資料表: {', '.join(tables)}")
        print("\033[1;36m" + "=" * 60 + "\033[0m")
        
        if target_table:
            if target_table not in tables:
                print(f"\033[1;31m❌ 找不到資料表: {target_table}\033[0m")
                print(f"可用的資料表為: {', '.join(tables)}")
                return
            show_table_detail(cursor, target_table)
        else:
            # 預設展示所有 Table 的 Schema 概要與筆數
            for t in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {t};")
                count = cursor.fetchone()[0]
                print(f"\n\033[1;33m📌 資料表: {t} ({count} 筆資料)\033[0m")
                cursor.execute(f"PRAGMA table_info({t});")
                columns = cursor.fetchall()
                print(" ├─ 欄位結構:")
                for col in columns:
                    pk_label = " 🔑 [PK]" if col[5] else ""
                    null_label = " NOT NULL" if col[3] else ""
                    print(f" │  • {col[1]} ({col[2]}){pk_label}{null_label}")
                
                # 顯示前 3 筆樣品數據
                cursor.execute(f"SELECT * FROM {t} LIMIT 3;")
                rows = cursor.fetchall()
                if rows:
                    print(" └─ 樣本數據 (前 3 筆):")
                    col_names = [c[1] for c in columns]
                    print(f"    \033[0;32m{col_names}\033[0m")
                    for r in rows:
                        print(f"    {list(r)}")
                else:
                    print(" └─ (暫無資料)")
                print("\033[0;36m" + "-" * 60 + "\033[0m")
        conn.close()
    except Exception as e:
        print(f"\033[1;31m❌ 預覽失敗: {str(e)}\033[0m")

def show_table_detail(cursor, table):
    cursor.execute(f"SELECT COUNT(*) FROM {table};")
    count = cursor.fetchone()[0]
    print(f"\n\033[1;32m📖 詳細檢視資料表: {table} ({count} 筆資料)\033[0m")
    
    cursor.execute(f"PRAGMA table_info({table});")
    columns = cursor.fetchall()
    col_names = [c[1] for c in columns]
    
    # 顯示前 15 筆數據
    cursor.execute(f"SELECT * FROM {table} LIMIT 15;")
    rows = cursor.fetchall()
    
    print("\033[1;32m┌" + "─" * 80 + "┐\033[0m")
    print(f"\033[1;32m│\033[0m 欄位: {col_names}")
    print("\033[1;32m├" + "─" * 80 + "┤\033[0m")
    for r in rows:
        print(f"\033[1;32m│\033[0m {list(r)}")
    print("\033[1;32m└" + "─" * 80 + "┘\033[0m")
    if count > 15:
        print(f"💡 僅顯示前 15 筆資料 (共 {count} 筆)")

if __name__ == "__main__":
    main()
