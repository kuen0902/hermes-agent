# Weekend Silence Logic (Taipei Time)

To prevent redundant "stale" reports when the market is closed on weekends (Saturday/Sunday), implement a temporal gatekeeper in orchestration scripts.

## Logic Overview
The US market closes at Saturday 04:00/05:00 AM Taipei Time. After a final "settlement" sync at 06:00 AM, all subsequent reports until Monday afternoon are redundant.

## Python Implementation Example

```python
import pytz
from datetime import datetime

def is_stale_weekend():
    taipei_tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(taipei_tz)
    
    # Saturday (weekday 5) after 06:00 AM (post-US sync)
    # Sunday (weekday 6) all day
    if (now.weekday() == 5 and now.hour >= 6) or now.weekday() == 6:
        return True
    return False

if __name__ == "__main__":
    if is_stale_weekend():
        print("Weekend detected. Suppressing stale reports.")
        exit(0)
    # ... proceed with data fetching
```

## Maintenance Note
This logic complements the `market_gatekeeper.py` (which checks actual ticker activity) by providing a deterministic time-based block for recurring cron jobs.
