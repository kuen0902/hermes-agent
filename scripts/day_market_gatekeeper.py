import json
import urllib.request
import ssl
import sys
from datetime import datetime
import pytz

def get_taiex_last_trading_date(symbol="2330.TW"):
    ctx = ssl._create_unverified_context()
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            data = json.loads(response.read().decode())
            meta = data['chart']['result'][0]['meta']
            market_time = meta.get('regularMarketTime')
            if not market_time: return None
            
            taipei_tz = pytz.timezone('Asia/Taipei')
            return datetime.fromtimestamp(market_time, taipei_tz).date()
    except:
        return None

if __name__ == "__main__":
    taipei_tz = pytz.timezone('Asia/Taipei')
    today = datetime.now(taipei_tz).date()
    last_trading = get_taiex_last_trading_date()
    
    # If today matches the last trading date of TSM (2330.TW), market was open today.
    if last_trading == today:
        print(f"Market was OPEN today ({today}). Proceeding.")
        sys.exit(0)
    else:
        print(f"Market was CLOSED today (Last open: {last_trading}, Today: {today}). Aborting.")
        sys.exit(1)
