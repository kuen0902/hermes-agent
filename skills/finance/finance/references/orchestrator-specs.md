# TAIEX Orchestrator Logic

The `taiex_orchestrator.py` serves as the CLI entry point for the entire automation suite.

## Execution Sequence
1. **Sync**: Runs `taiex_central_data_sync.py` to update the central JSON cache from Numbers.app.
2. **Distribution**: Runs monitor scripts in sequence:
   - `stock_monitor.py` (Personal)
   - `william_stock_monitor.py` (William)
   - `group_stock_monitor.py` (Group)

## Deduplication (The 8-Minute Rule)
Each monitor script implements a lock check:
- Lock File Path: `~/.hermes/data/<monitor_prefix>_sent.lock`
- Content: Unix timestamp (float).
- Logic: If `time.time() - last_run < 480` (8 minutes), the script exits silently to avoid notification spam during cron runs or accidental double-triggers.

## Environment Requirements
- **macOS Numbers.app**: Must be open with the document `StockTracking_Daily.numbers` active or accessible.
- **Python Dependencies**: `yfinance`, `pandas`.
- **Network**: Needs access to `query1.finance.yahoo.com` and `api.telegram.org`.
