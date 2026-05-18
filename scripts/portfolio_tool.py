#!/Users/bookid/.hermes/.venv/bin/python
import os
import sqlite3
import json
import datetime
import argparse

DATA_DIR = os.path.expanduser("~/.hermes/data")
DB_PATH = os.path.join(DATA_DIR, "portfolio.db")
REGISTRY_FILE = os.path.join(DATA_DIR, "master_stock_registry.json")

def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS current_holdings (
            code TEXT PRIMARY KEY,
            name TEXT,
            qty REAL,
            avg_price REAL,
            updated_at TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            code TEXT PRIMARY KEY,
            name TEXT,
            added_at TEXT,
            group_name TEXT DEFAULT '個人追蹤'
        )
    ''')
    try:
        cursor.execute("ALTER TABLE watchlist ADD COLUMN group_name TEXT DEFAULT '個人追蹤'")
    except sqlite3.OperationalError:
        # Column already exists
        pass
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pnl_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            name TEXT,
            sell_qty REAL,
            buy_price REAL,
            sell_price REAL,
            realized_pnl REAL,
            closed_at TEXT
        )
    ''')
    conn.commit()
    return conn

def get_name(code):
    try:
        with open(REGISTRY_FILE, 'r') as f:
            registry = json.load(f)
            return registry.get("official_names", {}).get(code, code)
    except:
        return code

def add_position(code, qty, price):
    conn = init_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name, qty, avg_price FROM current_holdings WHERE code = ?", (code,))
    row = cursor.fetchone()
    
    now = datetime.datetime.now().isoformat()
    name = get_name(code)
    
    if row:
        _, old_qty, old_avg = row
        total_cost = (old_qty * old_avg) + (qty * price)
        new_qty = old_qty + qty
        new_avg = total_cost / new_qty
        cursor.execute('''
            UPDATE current_holdings SET qty = ?, avg_price = ?, updated_at = ? WHERE code = ?
        ''', (new_qty, new_avg, now, code))
        print(f"✅ [加碼] 成功加碼 {name}({code}) {qty}張 @ {price}。目前總持股: {new_qty}張，最新均價: {new_avg:.2f}")
    else:
        cursor.execute('''
            INSERT INTO current_holdings (code, name, qty, avg_price, updated_at) VALUES (?, ?, ?, ?, ?)
        ''', (code, name, qty, price, now))
        print(f"✅ [建倉] 成功買進 {name}({code}) {qty}張 @ {price}。")
        
    conn.commit()
    conn.close()

def reduce_position(code, qty, price):
    conn = init_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name, qty, avg_price FROM current_holdings WHERE code = ?", (code,))
    row = cursor.fetchone()
    
    if not row:
        print(f"❌ 錯誤：目前沒有持有 {code}，無法減碼。")
        return
        
    name, old_qty, old_avg = row
    
    if qty > old_qty:
        print(f"❌ 錯誤：減碼數量 ({qty}) 大於目前庫存 ({old_qty})。")
        return
        
    realized_pnl = (price - old_avg) * qty * 1000
    now = datetime.datetime.now().isoformat()
    
    # Write to PnL history
    cursor.execute('''
        INSERT INTO pnl_history (code, name, sell_qty, buy_price, sell_price, realized_pnl, closed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (code, name, qty, old_avg, price, realized_pnl, now))
    
    new_qty = old_qty - qty
    
    if new_qty <= 0.001:
        cursor.execute("DELETE FROM current_holdings WHERE code = ?", (code,))
        print(f"✅ [清倉] 成功賣出所有 {name}({code}) {qty}張 @ {price}。")
    else:
        cursor.execute('''
            UPDATE current_holdings SET qty = ?, updated_at = ? WHERE code = ?
        ''', (new_qty, now, code))
        print(f"✅ [減碼] 成功賣出 {name}({code}) {qty}張 @ {price}。剩餘持股: {new_qty}張。")
        
    profit_str = "🔴 獲利" if realized_pnl > 0 else "🟢 虧損" if realized_pnl < 0 else "⚪ 損益兩平"
    print(f"📊 本次減碼已實現損益: {profit_str} {realized_pnl:,.2f} 元")
        
    conn.commit()
    conn.close()

def get_portfolio():
    conn = init_db()
    cursor = conn.cursor()
    cursor.execute("SELECT code, name, qty, avg_price FROM current_holdings ORDER BY code")
    rows = cursor.fetchall()
    conn.close()
    
    # Also output as JSON format for swift to parse easily
    port_dict = {}
    for code, name, qty, avg in rows:
        port_dict[code] = {"name": name, "qty": qty, "avg": avg}
    return port_dict

def export_portfolio_json():
    print(json.dumps(get_portfolio(), ensure_ascii=False))

def print_portfolio():
    port = get_portfolio()
    
    live_prices = {}
    try:
        with open(os.path.join(DATA_DIR, "central_stock_data.json"), 'r') as f:
            cdata = json.load(f)
            live_prices = cdata.get("data", {})
    except:
        pass

    print("\n【📈 目前持股狀況】")
    print("-" * 48)
    
    total_cost = 0
    total_value = 0
    
    port_list = []
    for code, info in port.items():
        qty = info['qty']
        avg = info['avg']
        
        live_price = avg
        if code in live_prices and "price" in live_prices[code]:
            live_price = float(live_prices[code]["price"])
            
        cost = qty * 1000 * avg
        value = qty * 1000 * live_price
        pnl = value - cost
        pct = (pnl / cost) * 100 if cost > 0 else 0
        port_list.append((code, info['name'], qty, avg, live_price, pnl, pct))
        
        total_cost += cost
        total_value += value

    port_list.sort(key=lambda x: x[6], reverse=True)

    for code, name, qty, avg, live_price, pnl, pct in port_list:
        icon = "🔴" if pnl >= 0 else "🟢"
        sign = "+" if pnl > 0 else ""
        
        print(f"[{code.ljust(6)}] {name} ({int(qty)}張)")
        print(f"均: {avg:7.2f} | 現: {live_price:7.2f} | {icon} {sign}{pct:6.2f}% ({sign}{int(pnl):,})")

    print("-" * 48)
    overall_pnl = total_value - total_cost
    overall_pct = (overall_pnl / total_cost) * 100 if total_cost > 0 else 0
    overall_icon = "🔴" if overall_pnl >= 0 else "🟢"
    sign_all = "+" if overall_pnl > 0 else ""
    print(f"💰 總投入成本: {int(total_cost):,}")
    print(f"💵 總目前現值: {int(total_value):,}")
    print(f"📊 總未實現損益: {overall_icon} {sign_all}{int(overall_pnl):,} ({sign_all}{overall_pct:.2f}%)")

def add_watchlist(code, group_name="個人追蹤"):
    conn = init_db()
    cursor = conn.cursor()
    name = get_name(code)
    now = datetime.datetime.now().isoformat()
    try:
        cursor.execute("INSERT INTO watchlist (code, name, added_at, group_name) VALUES (?, ?, ?, ?)", (code, name, now, group_name))
        conn.commit()
        print(f"✅ 成功將 {name}({code}) 加入觀測清單 [{group_name}]！")
    except sqlite3.IntegrityError:
        cursor.execute("UPDATE watchlist SET group_name = ? WHERE code = ?", (group_name, code))
        conn.commit()
        print(f"⚠️ {name}({code}) 已經在觀測清單中，已將其群組更新為 [{group_name}]。")
    conn.close()

def remove_watchlist(code):
    conn = init_db()
    cursor = conn.cursor()
    name = get_name(code)
    cursor.execute("DELETE FROM watchlist WHERE code = ?", (code,))
    if cursor.rowcount > 0:
        print(f"✅ 成功將 {name}({code}) 從觀測清單移除！")
    else:
        print(f"⚠️ 觀測清單中找不到 {code}。")
    conn.commit()
    conn.close()

def print_watchlist():
    conn = init_db()
    cursor = conn.cursor()
    cursor.execute("SELECT code, name, group_name FROM watchlist ORDER BY group_name, added_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    print("\n👁️ 系統專屬觀測清單:")
    print("-" * 50)
    if not rows:
        print("目前沒有追蹤任何股票。")
    else:
        # Group the items by group_name
        grouped = {}
        for code, name, grp in rows:
            g = grp or "個人追蹤"
            if g not in grouped:
                grouped[g] = []
            grouped[g].append((code, name))
            
        for g, items in grouped.items():
            print(f"📂 【 {g} 】")
            for code, name in items:
                print(f"   📌 {name.ljust(8)} ({code})")
            print()
    print("-" * 50)
    print(f"總計: {len(rows)} 檔追蹤中\n")

def print_quote(code):
    name = get_name(code)
    try:
        with open(os.path.join(DATA_DIR, "central_stock_data.json"), 'r') as f:
            cdata = json.load(f)
            data = cdata.get("data", {})
            if code in data:
                info = data[code]
                price = float(info.get("price", 0))
                change = float(info.get("change", 0))
                pct = float(info.get("pct", 0))
                volume = int(info.get("volume", 0))
                
                icon = "🔴" if change >= 0 else "🟢"
                sign = "+" if change > 0 else ""
                
                print(f"📈 【 {name} ({code}) 】 最新報價")
                print("-" * 30)
                print(f"現價: {price:.2f}")
                print(f"漲跌: {icon} {sign}{change:.2f} ({sign}{pct:.2f}%)")
                print(f"成交量: {volume:,} 張")
                print("-" * 30)
                return
    except Exception as e:
        pass
        
    print(f"⚠️ 找不到 {name}({code}) 的最新即時報價，可能目前未在監控排程內。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hermes Portfolio Tool")
    parser.add_argument("--add", nargs=3, metavar=("CODE", "QTY", "PRICE"), help="加碼或買進股票")
    parser.add_argument("--reduce", nargs=3, metavar=("CODE", "QTY", "PRICE"), help="減碼或賣出股票")
    parser.add_argument("--view", action="store_true", help="檢視目前持股")
    parser.add_argument("--export-json", action="store_true", help="匯出持股 JSON 供 Swift 使用")
    
    # Legacy backward compatibility flags
    parser.add_argument("--action", help="Legacy Telegram UI action (buy, sell, check, watch_list, quote)")
    parser.add_argument("--code", help="Legacy stock code")
    parser.add_argument("--qty", help="Legacy quantity")
    parser.add_argument("--price", help="Legacy price")
    
    args = parser.parse_args()
    
    # Handle legacy Gateway --action calls
    if args.action:
        if args.action == "check":
            print_portfolio()
        elif args.action == "buy" and args.code and args.qty and args.price:
            add_position(args.code, float(args.qty), float(args.price))
        elif args.action == "sell" and args.code and args.qty and args.price:
            reduce_position(args.code, float(args.qty), float(args.price))
        elif args.action == "watch_list":
            print_watchlist()
        elif args.action == "watch_add" and args.code:
            add_watchlist(args.code)
        elif args.action == "watch_rm" and args.code:
            remove_watchlist(args.code)
        elif args.action == "quote" and args.code:
            print_quote(args.code)
        else:
            print("❌ Invalid legacy arguments or missing parameters")
    # Handle new SQLite calls
    elif args.add:
        add_position(args.add[0], float(args.add[1]), float(args.add[2]))
    elif args.reduce:
        reduce_position(args.reduce[0], float(args.reduce[1]), float(args.reduce[2]))
    elif args.view:
        print_portfolio()
    elif args.export_json:
        export_portfolio_json()
    else:
        init_db()
