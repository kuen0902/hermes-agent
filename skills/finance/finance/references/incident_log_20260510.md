# Incident Log: 2026-05-10
**Context**: Syncing historical data for 1,970股票 during weekend.

## Issues Identified
1. **yfinance SQLite Lock**: Frequent `OperationalError: unable to open database file` when using `threads=True` or rapid sequential calls.
2. **Weekend Spam**: Night session reports were sending stale Friday data on Saturday afternoon.
3. **Missing SYNA Context**: User required addition of SYNA to night monitoring as a new priority.

## Fixes Applied
1. **Sync Optimization**: Created `daily_historical_sync.py` with `threads=False`. Cleaned `~/.cache/py-yfinance/*`.
2. **Weekend Gatekeeper**: Deployed `night_market_gatekeeper.py` to detect session activity based on `2330.TW` regular market time.
3. **Night Report Logic**: Patched `run_night_report.py` to exit silently if the market is closed according to the gatekeeper.

## Result
System is now fully automated and aware of holidays/weekends, preventing redundant notifications. SYNA is now a permanent part of the night session monitored ADRs.
