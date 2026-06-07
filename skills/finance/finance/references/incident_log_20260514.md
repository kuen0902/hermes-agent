# Incident Log: 2026-05-14

## Context
User reported excessive monitoring alerts ("高潮不斷") and a privacy leak (personal holdings being shared in a public/group channel).

## Root Cause
1. **Low Threshold**: The previous monitoring threshold was 3%. In a volatile market, this triggered too many messages.
2. **Profile Blending**: The `group` profile logic in `monitor_engine.py` was pulling from `personal_data` (source: Numbers) and reporting it to the group chat ID.

## Resolution
1. **Threshold Adjustment**: Initially adjusted to 5%, then restored to 3% as per user's "精密" preference, but with better noise filtering. 
2. **Privacy Patch**: Permanently removed the link between `personal_data` and the `group` profile in `monitor_engine.py`.
3. **Portfolio Sync**: Successfully synced new purchases (WIN Semi 3105, PSMC 6770, AUO 2409, MediaTek 2454) and removed sold positions (Advantech 2395) using a Python-wrapped AppleScript bridge for reliability.

## 2026-05-14 17:30 (EOD Sync Failure)
- **Problem**: `Portfolio-Analysis-1430` (9e38a92a90d1) failed with "Permission denied" followed by timeout.
- **Root Cause**:
    1. Executable bit missing on `.sh` wrapper.
    2. Syncing 1,975 symbols midday was too slow for the 60s timeout limit.
- **Resolution**: Implemented `Fast Sync` flag in `daily_historical_sync.py` to only process monitored tickers. Updated the cronjob wrapper to use this flag. Resolved dependency issue by installing `pandas-ta-classic`.
- **Lessons Learned**:
    - Periodical `chmod +x` is necessary when maintaining local script-based automation.
    - Always decouple "Full System Sync" (Nightly) from "Critical Path Sync" (Intraday/EOD).
