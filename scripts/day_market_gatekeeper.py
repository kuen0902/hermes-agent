import json
import urllib.request
import ssl
import sys
from datetime import datetime
import pytz

def is_market_open_today():
    taipei_tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(taipei_tz)
    
    # 1. Weekend check (Saturday=5, Sunday=6)
    if now.weekday() >= 5:
        print(f"Market closed: Weekend ({now.strftime('%A')})")
        return False
        
    # 2. Time range check (Standard TAIEX 09:00 - 13:30 + cushion)
    # We allow early checks for open-report at 08:30-09:00
    current_time = now.strftime('%H:%M')
    if current_time < '08:30' or current_time > '15:30':
        # Allow night session checks if needed, but for Day Gatekeeper, we cap it.
        print(f"Outside day market hours: {current_time}")
        return False

    # 3. Dynamic check via 2330.TW (TSMC) - The most reliable indicator
    # We use the quote summary instead of chart for better freshness
    ctx = ssl._create_unverified_context()
    headers = {'User-Agent': 'Mozilla/5.0'}
    # Use regular quote endpoint
    url = "https://query2.finance.yahoo.com/v7/finance/quote?symbols=2330.TW"
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            data = json.loads(response.read().decode())
            result = data.get('quoteResponse', {}).get('result', [])
            if not result: return True # Default to open if API fails but it is business hours
            
            quote = result[0]
            market_state = quote.get('marketState') # PRE, REGULAR, POST, CLOSED
            
            # If Yahoo says REGULAR or POST, it's definitely an open day (or was)
            if market_state in ['REGULAR', 'POST', 'PRE']:
                print(f"Market state: {market_state}. Proceeding.")
                return True
                
            # Check price hint
            last_trade_time = quote.get('regularMarketTime')
            if last_trade_time:
                last_trade_date = datetime.fromtimestamp(last_trade_time, taipei_tz).date()
                if last_trade_date == now.date():
                    print(f"Last trade date matches today ({last_trade_date}). Proceeding.")
                    return True
    except Exception as e:
        print(f"API Check failed ({e}), defaulting to weekday/hours logic.")
        return True # Default to open during Mon-Fri hours

    print("Market appears closed based on all checks.")
    return False

if __name__ == "__main__":
    if is_market_open_today():
        sys.exit(0)
    else:
        sys.exit(1)
