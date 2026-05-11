import subprocess
import json
import urllib.request
import sys

def get_holdings(numbers_file, sheet_name="Portfolio", table_name="表格 1", column=1):
    """Extract stock codes from an Apple Numbers sheet."""
    script = f"""
    tell application "Numbers"
        try
            open POSIX file "{numbers_file}"
            delay 1
            tell document 1 to tell sheet "{sheet_name}" to tell table "{table_name}"
                set stockCodes to value of every cell of column {column}
                return stockCodes
            end tell
        on error
            return ""
        end try
    end tell
    """
    try:
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        if result.returncode == 0:
            raw = result.stdout.strip()
            if not raw: return []
            codes = [c.strip("'\" ") for c in raw.split(", ")]
            valid_codes = []
            for c in codes:
                if not c or c in ["ID", "missing value", "Stock Code", "代號"]: continue
                if c.startswith("'"): c = c[1:]
                valid_codes.append(c)
            return list(set(valid_codes))
        return []
    except:
        return []

def fetch_yahoo(symbol):
    """Direct Yahoo Finance API fetch without web search."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            res_list = data.get('chart', {}).get('result')
            if not res_list: return None
            res = res_list[0]
            meta = res.get('meta', {})
            
            # Extract indicators for Open price
            indicators = res.get('indicators', {}).get('quote', [{}])[0]
            open_prices = indicators.get('open', [])
            today_open = open_prices[0] if open_prices and open_prices[0] is not None else meta.get('regularMarketOpen')
            
            return {
                'symbol': meta.get('symbol'),
                'name': meta.get('shortName', symbol),
                'price': meta.get('regularMarketPrice'),
                'open': today_open,
                'prev_close': meta.get('chartPreviousClose')
            }
    except:
        return None

def get_stock_data(symbol):
    """Resolve symbol suffixes for Taiwan stocks."""
    if "." in symbol:
        return fetch_yahoo(symbol)
    for suffix in [".TW", ".TWO"]:
        data = fetch_yahoo(symbol + suffix)
        if data and data['price'] is not None: return data
    return fetch_yahoo(symbol)

def main():
    # Example usage: Replace with your actual filepath
    FILEPATH = "/Users/bookid/Documents/StockTracking_Daily.numbers"
    holdings = get_holdings(FILEPATH)
    
    if not holdings:
        print("⚠️ No holdings found.")
        return

    holdings.sort()
    results = []
    market_opened = False
    
    for code in holdings:
        data = get_stock_data(code)
        if data and data['price'] is not None:
            price = data['price']
            baseline = data['open'] if data['open'] is not None else data['prev_close']
            if data['open'] is not None: market_opened = True
            
            if baseline is not None:
                diff = price - baseline
                pct = (diff / baseline * 100) if baseline > 0 else 0
                trend = "🔴" if diff < 0 else "🟢" if diff > 0 else "⚪"
                results.append(f"{trend} *{data['name']}* (`{data['symbol']}`)\n   價格: *{price}* | 漲跌: *{diff:+.2f}* ({pct:+.2f}%)")
    
    if results:
        status = "(Intraday vs Open)" if market_opened else "(Pre-market vs Prev Close)"
        print(f"📊 **Portfolio Tracking {status}**\n" + "\n\n".join(results))

if __name__ == "__main__":
    main()
