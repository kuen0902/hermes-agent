import json
import urllib.request
import ssl
import sys
from datetime import datetime
import pytz

def is_market_open(symbol="2330.TW"):
    """
    Checks if the market is open based on the last transaction time of a bellwether stock.
    Returns True if latest data matches today's date in Taipei.
    """
    ctx = ssl._create_unverified_context()
    # Use standard browser-like UA to avoid 403/429
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            data = json.loads(response.read().decode())
            meta = data['chart']['result'][0]['meta']
            market_time = meta.get('regularMarketTime')
            
            if not market_time:
                return False
                
            # Convert market time (Unix) to Taipei Date
            taipei_tz = pytz.timezone('Asia/Taipei')
            market_date = datetime.fromtimestamp(market_time, taipei_tz).date()
            
            # Current date in Taipei
            today_taipei = datetime.now(taipei_tz).date()
            
            return market_date == today_taipei
    except Exception as e:
        # Fallback to False if unsure (to prevent erroneous cron reports during outages)
        return False

if __name__ == "__main__":
    # If called as a script, exits with 0 if open, 1 if closed
    # Use like: python3 market_gatekeeper.py || exit 0
    if is_market_open():
        sys.exit(0)
    else:
        sys.exit(1)
