import json
import urllib.request
import ssl
import sys
from datetime import datetime, timedelta
import pytz

def get_taiex_last_trading_date(symbol="2330.TW"):
    ctx = ssl._create_unverified_context()
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
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

def is_night_session_active():
    taipei_tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(taipei_tz)
    last_trading_date = get_taiex_last_trading_date()
    if not last_trading_date: return False

    if now.hour >= 15:
        return last_trading_date == now.date()
    elif now.hour < 6:
        yesterday_date = (now - timedelta(days=1)).date()
        return last_trading_date == yesterday_date
    return False

if __name__ == "__main__":
    if is_night_session_active(): sys.exit(0)
    else: sys.exit(1)
