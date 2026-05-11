# TAIEX Session Logic & Gatekeeping

To prevent redundant reporting during holidays or weekends, use a bellwether stock (2330.TW) to probe market activity.

## Logical Flow

### 1. Active Day Check (Day Session)
Check if `regularMarketTime` of `2330.TW` matches the current local date (Taipei).
- **Logic**: `datetime.fromtimestamp(market_time, taipei_tz).date() == datetime.now(taipei_tz).date()`

### 2. Active Night Check (Night Session)
The Night Session spans two calendar days (15:00 - 05:00).
- **Condition A (15:00 - 23:59)**: Active if *Today* was a trading day.
- **Condition B (00:00 - 06:00)**: Active if *Yesterday* was a trading day.

## Reference Script Implementation
See `scripts/night_market_gatekeeper.py` for the implementation used in this environment.

---
*Note: Always use query2.finance.yahoo.com as it is more stable for REST queries.*
