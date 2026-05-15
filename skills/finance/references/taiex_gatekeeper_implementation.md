# TAIEX Market Gatekeeper Implementation

To prevent automated trading scripts from running on holidays or outside market hours, use the following robust Python implementation.

## Strategy: TSMC (2330.TW) Quote Verification
Relying on simple `datetime` checks is insufficient for TAIEX because of irregular holidays. Checking the specific `marketState` of the most traded stock provides the highest accuracy.

```python
import json, urllib.request, ssl, sys
from datetime import datetime
import pytz

def is_market_open_today():
    taipei_tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(taipei_tz)
    
    # 1. Weekend check
    if now.weekday() >= 5: return False
        
    # 2. Time range check (08:30 - 15:30)
    current_time = now.strftime('%H:%M')
    if current_time < '08:30' or current_time > '15:30': return False

    # 3. Dynamic check via Yahoo Finance Quote API
    url = "https://query2.finance.yahoo.com/v7/finance/quote?symbols=2330.TW"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            quote = data['quoteResponse']['result'][0]
            state = quote.get('marketState')
            
            # Open/Pre/Post are valid for automation runs
            if state in ['REGULAR', 'POST', 'PRE']: return True
                
            # Double check trade time match
            trade_time = quote.get('regularMarketTime')
            if trade_time:
                trade_date = datetime.fromtimestamp(trade_time, taipei_tz).date()
                if trade_date == now.date(): return True
    except:
        return True # Default to open during Mon-Fri if API is unreachable

    return False

if __name__ == "__main__":
    sys.exit(0 if is_market_open_today() else 1)
```

## Integration in .sh Wrappers
```bash
PYTHON="/path/to/venv/bin/python"
$PYTHON gatekeeper.py || exit 0
# Rest of the script...
```
