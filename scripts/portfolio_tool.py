#!/usr/bin/env python3
import json
import os
import shutil
import argparse
import yfinance as yf
from datetime import datetime
import unicodedata
import requests  # type: ignore[import-untyped]
from requests.adapters import HTTPAdapter  # type: ignore[import-untyped]
from urllib3.util.retry import Retry
import time

def is_cron_imminent(threshold_seconds=30):
    jobs_file = os.path.expanduser('~/.hermes/cron/jobs.json')
    if not os.path.exists(jobs_file):
        return False
    try:
        with open(jobs_file, 'r', encoding='utf-8') as f:
            jobs_data = json.load(f)
            
        now = datetime.now()
        for job in jobs_data.get("jobs", []):
            if job.get("enabled") and job.get("next_run_at"):
                next_run_str = job["next_run_at"]
                try:
                    next_run = datetime.fromisoformat(next_run_str)
                    if next_run.tzinfo is not None:
                        now_aware = now.astimezone(next_run.tzinfo)
                        diff = (next_run - now_aware).total_seconds()
                    else:
                        diff = (next_run - now).total_seconds()
                        
                    if 0 <= diff <= threshold_seconds:
                        return True
                except ValueError:
                    pass
    except Exception as e:
        pass
    return False

def get_yf_session():
    session = requests.Session()
    # Spoof a modern browser to bypass basic rate limits / 403s
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,zh-TW;q=0.8,zh;q=0.7',
    })
    retry = Retry(
        total=5,
        read=5,
        connect=5,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)  # type: ignore[arg-type]
    session.mount('https://', adapter)  # type: ignore[arg-type]
    return session

def display_len(s):
    return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in str(s))

def pad_str(s, width, align='left'):
    s = str(s)
    l = display_len(s)
    if l >= width:
        return s
    pad = width - l
    if align == 'left':
        return s + ' ' * pad
    elif align == 'right':
        return ' ' * pad + s
    else:
        return ' ' * (pad // 2) + s + ' ' * (pad - pad // 2)

DATA_FILE = os.path.expanduser('~/.hermes/data/central_stock_data.json')
BACKUP_FILE = os.path.expanduser('~/.hermes/data/central_stock_data.json.bak')

_mis_opener = None

def get_mis_opener():
    global _mis_opener
    if _mis_opener is None:
        import urllib.request
        import urllib.error
        import ssl
        from http.cookiejar import CookieJar
        context = ssl._create_unverified_context()
        cj = CookieJar()
        _mis_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPSHandler(context=context))
        req_session = urllib.request.Request("https://mis.twse.com.tw/stock/index.jsp", headers={'User-Agent': 'Mozilla/5.0'})
        try:
            _mis_opener.open(req_session, timeout=5)
        except Exception:
            pass
    return _mis_opener

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"personal_data": {}, "group_codes": [], "william_codes": [], "full_mapping": {}, "data": {}}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    if os.path.exists(DATA_FILE):
        shutil.copy2(DATA_FILE, BACKUP_FILE)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_live_price(symbol):
    session = get_yf_session()
    
    for suffix in [".TW", ".TWO"]:
        try:
            yf_symbol = f"{symbol}{suffix}"
            ticker = yf.Ticker(yf_symbol)
            history = ticker.history(period="5d")
            if not history.empty:
                return float(history['Close'].iloc[-1])
        except Exception:
            continue
            
    # Ultimate Fallback: TWSE/TPEx Official MIS API
    try:
        opener = get_mis_opener()
        for market in ["tse", "otc"]:
            url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={market}_{symbol}.tw&json=1&delay=0"
            try:
                import urllib.request
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
                with opener.open(req, timeout=5) as response:
                    res = json.loads(response.read().decode('utf-8'))
                    msgArray = res.get("msgArray", [])
                    if msgArray:
                        stock = msgArray[0]
                        z = stock.get("z", "-")
                        y = stock.get("y", 0)
                        
                        price = float(z) if z != "-" else float(y)
                        if price > 0:
                            return price
            except Exception:
                continue
    except Exception:
        pass
        
    return None

def check_portfolio(data):
    personal = data.get("personal_data", {})
    cache = data.get("data", {})
    
    total_cost = 0.0
    total_value = 0.0
    
    items_to_print = []
    
    for code, info in personal.items():
        name = info.get("name", "Unknown")
        qty_shares = info.get("qty", 0) * 1000  # 張 -> 股
        avg_cost = info.get("avg", 0.0)
        
        if qty_shares <= 0:
            continue
            
        cost_basis = qty_shares * avg_cost
        
        # Get current price
        current_price = None
        if code in cache and "price" in cache[code]:
            current_price = cache[code]["price"]
        else:
            current_price = fetch_live_price(code)
            
        qty_str = f"{qty_shares/1000:g}張"
        
        pnl_amt = 0
        pnl_str = ""
        current_value = cost_basis
            
        if current_price:
            current_value = qty_shares * current_price
            pnl_pct = ((current_price - avg_cost) / avg_cost) * 100 if avg_cost > 0 else 0
            pnl_amt = current_value - cost_basis
            
            pnl_pct_str = f"{'+' if pnl_pct >= 0 else ''}{pnl_pct:.2f}%"
            pnl_amt_str = f"({'+' if pnl_amt >= 0 else ''}{int(pnl_amt):,})"
            
            pnl_str = f"🔴 {pnl_pct_str:>8} {pnl_amt_str:>12}" if pnl_pct >= 0 else f"🟢 {pnl_pct_str:>8} {pnl_amt_str:>12}"
            
        total_cost += cost_basis
        total_value += current_value
            
        items_to_print.append({
            "code": code,
            "name": name,
            "qty_str": qty_str,
            "avg_cost": avg_cost,
            "current_price": current_price,
            "pnl_str": pnl_str,
            "pnl_amt": pnl_amt
        })
        
    items_to_print.sort(key=lambda x: x["pnl_amt"], reverse=True)
    
    print("【📈 目前持股狀況】")
    print("-" * 48)
    for item in items_to_print:
        print(f"[{item['code']:<6}] {item['name']} ({item['qty_str']})")
        if item['current_price']:
            print(f"均: {item['avg_cost']:>7.2f} | 現: {item['current_price']:>7.2f} | {item['pnl_str']}")
        else:
            print(f"均: {item['avg_cost']:>7.2f} | 現: {'-':>7} | {'-':>24}")
            
    print("-" * 48)
    overall_pnl = total_value - total_cost
    overall_pct = (overall_pnl / total_cost * 100) if total_cost > 0 else 0
    sign = "🔴" if overall_pnl >= 0 else "🟢"
    print(f"💰 總投入成本: {int(total_cost):,}")
    print(f"💵 總目前現值: {int(total_value):,}")
    print(f"📊 總未實現損益: {sign} {int(overall_pnl):,} ({overall_pct:.2f}%)")

def resolve_stock_name(code, fallback_dict=None):
    if fallback_dict is None:
        fallback_dict = {}
    name = f"股票_{code}"
    try:
        mapping_file = os.path.expanduser("~/.hermes/data/stock_mapping.json")
        if os.path.exists(mapping_file):
            import json
            with open(mapping_file, 'r', encoding='utf-8') as f:
                stock_mapping = json.load(f)
                reversed_mapping = {}
                for k, v in stock_mapping.items():
                    reversed_mapping[str(v).strip()] = str(k).strip()
                
                safe_code = str(code).strip()
                if safe_code in reversed_mapping:
                    return reversed_mapping[safe_code]
    except Exception:
        pass
        
    return fallback_dict.get(code, name)

def buy_stock(data, code, name, qty, price):
    personal = data.setdefault("personal_data", {})
    mapping = data.setdefault("full_mapping", {})
    
    if not name:
        name = resolve_stock_name(code, mapping)
    mapping[code] = name
        
    qty_張 = float(qty)
    buy_price = float(price)
    
    if code in personal:
        old_qty = float(personal[code].get("qty", 0))
        old_avg = float(personal[code].get("avg", 0.0))
        
        # 加權平均: (舊張數*舊價 + 新張數*新價) / 總張數
        total_qty = old_qty + qty_張
        if total_qty > 0:
            new_avg = (old_qty * old_avg + qty_張 * buy_price) / total_qty
        else:
            new_avg = 0.0
            
        personal[code]["qty"] = total_qty
        personal[code]["avg"] = new_avg
        personal[code]["name"] = name
        print(f"✅ 已加碼 {name}({code}): 買進 {qty_張}張 @ {buy_price}。最新總張數: {total_qty}張，加權均價: {new_avg:.2f}")
    else:
        personal[code] = {
            "name": name,
            "qty": qty_張,
            "avg": buy_price
        }
        print(f"✅ 已建倉 {name}({code}): 買進 {qty_張}張 @ {buy_price}。")
        
    save_data(data)

def sell_stock(data, code, qty, price):
    personal = data.get("personal_data", {})
    if code not in personal:
        print(f"❌ 錯誤: 找不到持股 {code}。")
        return
        
    name = personal[code].get("name")
    if not name or name.startswith("股票_") or name == code:
        name = resolve_stock_name(code, data.get("full_mapping", {}))
    
    old_qty = float(personal[code].get("qty", 0))
    sell_qty = float(qty)
    avg_cost = float(personal[code].get("avg", 0.0))
    sell_price = float(price)
    
    if sell_qty > old_qty:
        print(f"⚠️ 警告: 賣出張數 ({sell_qty}) 大於現有持股張數 ({old_qty})。將全部清倉。")
        sell_qty = old_qty
        
    new_qty = old_qty - sell_qty
    realized_pnl = (sell_price - avg_cost) * sell_qty * 1000
    pnl_ratio = ((sell_price - avg_cost) / avg_cost) * 100 if avg_cost > 0 else 0
    
    if new_qty <= 0:
        del personal[code]
        print(f"✅ 已全數清倉 {name}({code})。賣出均價: {sell_price}")
        print(f"📊 已實現損益: {int(realized_pnl):,} (損益比: {pnl_ratio:.2f}%)")
        print("\n=== TRANSACTION_METRICS ===")
        print(json.dumps({
            "status": "cleared",
            "code": code,
            "name": name,
            "sell_price": sell_price,
            "quantity": sell_qty,
            "realized_pnl": int(realized_pnl),
            "pnl_ratio_percent": round(pnl_ratio, 2)
        }, ensure_ascii=False))
        print("===========================")
    else:
        personal[code]["qty"] = new_qty
        print(f"✅ 已減碼 {name}({code}): 賣出 {sell_qty}張 @ {sell_price}。剩餘張數: {new_qty}張。")
        print(f"📊 本次實現損益: {int(realized_pnl):,} (損益比: {pnl_ratio:.2f}%)")
        print("\n=== TRANSACTION_METRICS ===")
        print(json.dumps({
            "status": "partial_sell",
            "code": code,
            "name": name,
            "sell_price": sell_price,
            "quantity": sell_qty,
            "realized_pnl": int(realized_pnl),
            "pnl_ratio_percent": round(pnl_ratio, 2),
            "remaining_qty": new_qty
        }, ensure_ascii=False))
        print("===========================")
        
    save_data(data)

def watch_add(data, code, name, group):
    target = data.setdefault(group, [])
    mapping = data.setdefault("full_mapping", {})
    
    if not name:
        name = resolve_stock_name(code, mapping)
    mapping[code] = name
        
    if code not in target:
        target.append(code)
        save_data(data)
        print(f"✅ 已將 {name}({code}) 加入觀測清單 [{group}]")
    else:
        print(f"ℹ️ {name}({code}) 已經在觀測清單 [{group}] 中")

def watch_rm(data, code, group):
    target = data.get(group, [])
    if code in target:
        target.remove(code)
        save_data(data)
        name = resolve_stock_name(code, data.get("full_mapping", {}))
        print(f"✅ 已將 {name}({code}) 從觀測清單 [{group}] 移除")
    else:
        print(f"ℹ️ 觀測清單 [{group}] 找不到 {code}")

def list_watchlist(data):
    groups = {
        "group_codes": "主要觀測清單",
        "william_codes": "William 觀測清單"
    }
    found_any = False
    for group_key, group_name in groups.items():
        codes = data.get(group_key, [])
        if codes:
            found_any = True
            print(f"【{group_name}】")
            print("-" * 48)
            for code in codes:
                name = resolve_stock_name(code, data.get("full_mapping", {}))
                print(f"[{code:<6}] {name}")
            print()
    
    if not found_any:
        print("ℹ️ 目前觀測清單是空的。")

def quote_stock(data, code):
    personal = data.get("personal_data", {})
    william = data.get("william_codes", [])
    group = data.get("group_codes", [])
    
    name = resolve_stock_name(code, data.get("full_mapping", {}))
    watchlist = set(personal.keys()) | set(william) | set(group)
    
    current_price = None
    prev_close = None
    
    # Path A: Cache Hit
    if code in watchlist and code in data.get("data", {}):
        cached_info = data["data"][code]
        current_price = cached_info.get("price")
        prev_close = cached_info.get("prev_close")
        
    # Path B: Not in watchlist or missing from cache
    if not current_price:
        if code not in watchlist and is_cron_imminent(30):
            print(f"⚠️ 系統即將進行大盤快取更新，為避免觸發 API 流量限制，進入等待佇列...")
            mtime_start = os.path.getmtime(DATA_FILE) if os.path.exists(DATA_FILE) else 0
            waited = 0
            while waited < 60:
                time.sleep(2)
                waited += 2
                current_mtime = os.path.getmtime(DATA_FILE) if os.path.exists(DATA_FILE) else 0
                if current_mtime > mtime_start:
                    break
                    
        session = get_yf_session()
        for suffix in [".TW", ".TWO"]:
            try:
                ticker = yf.Ticker(f"{code}{suffix}")
                history = ticker.history(period="5d")
                if not history.empty and len(history) >= 2:
                    current_price = float(history['Close'].iloc[-1])
                    prev_close = float(history['Close'].iloc[-2])
                    break
                elif not history.empty and len(history) == 1:
                    current_price = float(history['Close'].iloc[-1])
                    prev_close = current_price
                    break
            except Exception:
                continue
                
        # Ultimate Fallback: TWSE/TPEx Official MIS API
        if not current_price:
            try:
                opener = get_mis_opener()
                import urllib.request
                for market in ["tse", "otc"]:
                    url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={market}_{code}.tw&json=1&delay=0"
                    try:
                        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                        with opener.open(req, timeout=5) as response:
                            res = json.loads(response.read().decode('utf-8'))
                            msgArray = res.get("msgArray", [])
                            if msgArray:
                                stock = msgArray[0]
                                z = stock.get("z", "-")
                                y = float(stock.get("y", 0))
                                temp_price = float(z) if z != "-" else y
                                if temp_price > 0:
                                    current_price = temp_price
                                    prev_close = y
                                    mis_name = stock.get("n", "")
                                    if mis_name:
                                        name = mis_name
                                    break
                    except Exception:
                        continue
            except Exception:
                pass
            
    if not current_price:
        print(f"❌ 無法取得 {code} 的報價資料。")
        return
        
    diff = current_price - prev_close if prev_close else 0
    pct_change = (diff / prev_close * 100) if prev_close and prev_close > 0 else 0
    
    sign = "🔴" if diff > 0 else ("🟢" if diff < 0 else "⚪")
    diff_str = f"+{diff:.2f}" if diff > 0 else f"{diff:.2f}"
    pct_str = f"+{pct_change:.2f}%" if diff > 0 else f"{pct_change:.2f}%"
    
    status_str = "未持有"
    if code in personal:
        qty = personal[code].get("qty", 0)
        avg = personal[code].get("avg", 0)
        status_str = f"已持有 ({qty:g}張, 均價: {avg:.2f})"
        
    print(f"【即時報價】[{code}] {name}")
    print(f"現價: {current_price:.2f} | 漲跌: {sign} {diff_str} ({pct_str})")
    print(f"狀態: {status_str}")

def main():
    parser = argparse.ArgumentParser(description="Hermes Portfolio Manager")
    parser.add_argument("--action", required=True, choices=["check", "buy", "sell", "watch_add", "watch_rm", "quote", "watch_list"])
    parser.add_argument("--code", help="股票代號 (e.g. 2330)")
    parser.add_argument("--name", help="股票名稱")
    parser.add_argument("--qty", type=float, help="張數 (1張=1000股)")
    parser.add_argument("--price", type=float, help="成交價")
    parser.add_argument("--group", default="group_codes", help="觀測清單分組 (預設 group_codes)")
    
    args = parser.parse_args()
    data = load_data()
    
    if args.action == "check":
        check_portfolio(data)
    elif args.action == "buy":
        if not args.code or not args.qty or not args.price:
            print("❌ --buy 需要 --code, --qty, --price")
            return
        buy_stock(data, args.code, args.name, args.qty, args.price)
    elif args.action == "sell":
        if not args.code or not args.qty or not args.price:
            print("❌ --sell 需要 --code, --qty, --price")
            return
        sell_stock(data, args.code, args.qty, args.price)
    elif args.action == "watch_add":
        if not args.code:
            print("❌ --watch_add 需要 --code")
            return
        watch_add(data, args.code, args.name, args.group)
    elif args.action == "watch_rm":
        if not args.code:
            print("❌ --watch_rm 需要 --code")
            return
        watch_rm(data, args.code, args.group)
    elif args.action == "watch_list":
        list_watchlist(data)
    elif args.action == "quote":
        if not args.code:
            print("❌ --quote 需要 --code")
            return
        quote_stock(data, args.code)

if __name__ == "__main__":
    main()
