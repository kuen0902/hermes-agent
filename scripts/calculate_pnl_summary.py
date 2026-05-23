#!/Users/bookid/.hermes/.venv/bin/python
import os
import sqlite3
import json
import datetime
from pathlib import Path

DATA_DIR = os.path.expanduser("~/.hermes/data")
DB_PATH = os.path.join(DATA_DIR, "portfolio.db")

def get_pnl_summary():
    if not os.path.exists(DB_PATH):
        return {"error": "Database not found."}
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Calculate Today's PnL
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    cursor.execute('''
        SELECT code, name, sell_qty, buy_price, sell_price, realized_pnl 
        FROM pnl_history 
        WHERE date(closed_at) = ?
    ''', (today,))
    
    today_trades = cursor.fetchall()
    
    # Calculate Total Historical PnL
    cursor.execute('SELECT SUM(realized_pnl) FROM pnl_history')
    total_pnl_row = cursor.fetchone()
    total_pnl = total_pnl_row[0] if total_pnl_row and total_pnl_row[0] else 0.0
    
    # Calculate Top 3 Strongest Trades by PnL
    cursor.execute('''
        SELECT code, name, sell_qty, buy_price, sell_price, realized_pnl 
        FROM pnl_history 
        ORDER BY realized_pnl DESC 
        LIMIT 3
    ''')
    top_trades = cursor.fetchall()
    
    conn.close()
    
    today_total = sum(t[5] for t in today_trades)
    
    report = {
        "date": today,
        "today_total_pnl": today_total,
        "historical_total_pnl": total_pnl,
        "trades": [],
        "top_3_trades": []
    }
    
    for code, name, qty, b_price, s_price, pnl in today_trades:
        report["trades"].append({
            "code": code,
            "name": name,
            "qty": qty,
            "buy_price": b_price,
            "sell_price": s_price,
            "pnl": pnl
        })
        
    for code, name, qty, b_price, s_price, pnl in top_trades:
        return_pct = ((s_price - b_price) / b_price * 100) if b_price > 0 else 0.0
        report["top_3_trades"].append({
            "code": code,
            "name": name,
            "qty": qty,
            "buy_price": b_price,
            "sell_price": s_price,
            "pnl": pnl,
            "return_pct": return_pct
        })
        
    return report

if __name__ == "__main__":
    report = get_pnl_summary()
    output_path = os.path.join(DATA_DIR, "pnl_summary_today.json")
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps(report, indent=2, ensure_ascii=False))
