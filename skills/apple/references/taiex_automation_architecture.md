# TAIEX Automation Architecture (bookid)

The stock automation system in this environment follows an Orchestrator-Gatherer-Distributor pattern to handle multi-channel reporting.

## Directory Structure
- **Scripts**: `/Users/bookid/.hermes/scripts/`
- **Data/Cache**: `/Users/bookid/.hermes/data/`
- **Portfolio Source**: `/Users/bookid/Documents/StockTracking_Daily.numbers`

## Execution Sequence
1. **`taiex_orchestrator.py`**: The entry point (run by cron).
2. **`taiex_central_data_sync.py`**:
   - Reads the portfolio from Numbers.
   - Fetches market data for all combined tickers (Personal + William + Group).
   - Saves to `central_stock_data.json`.
3. **Distribution Bots** (Parallel/Sequential):
   - `stock_monitor.py`: Personal損益報告.
   - `william_stock_monitor.py`: William's monitor.
   - `group_stock_monitor.py`: Group (高潮不斷) monitor.

## Key Data Artifact: `central_stock_data.json`
Structure used by all distributors:
```json
{
  "metadata": { "last_sync": "ISO_DATE", "status": "Healthy" },
  "personal_data": { "CODE": { "name": "...", "qty": 0, "avg": 0 } },
  "william_codes": ["CODE1", "CODE2"],
  "group_codes": ["CODE1", "CODE2"],
  "full_mapping": { "CODE": "ZH_NAME" },
  "data": {
    "CODE": {
      "symbol": "CODE.TW",
      "price": 0.0,
      "prev_close": 0.0,
      "pct": 0.0
    }
  }
}
```

## Known Channel Issues & Troubleshooting
- **William Bot (Chat ID 8695583357)**: 
    - Recurring `400: chat not found` errors. 
    - **Diagnosis**: This usually indicates the bot (`taiwangupiaoBot`) has lost the "started" state for that chat ID. 
    - **Fix**: The recipient (William) must search for the bot and send `/start` or a message to re-authorize the bot.
    - **Historical Context**: The bot token changed around 2026-05-07 from an `856...` token (old) to `873...` (new).

- **Numbers Consistency**:
    - The system relies on `StockTracking_Daily.numbers` being present in `~/Documents`. 
    - If the user mentions "Sync Numbers filename", verify that the orchestrator and sync scripts are pointed to the current file on disk (default: `StockTracking_Daily.numbers`).

## Troubleshooting
- **Telegram 400 Bad Request**: If a specific channel fails, verify with `curl`. William's channel often fails if the bot token or ID is stale or the session isn't initialized with `/start`.
- **Numbers Lock**: If script times out, ensure Numbers.app is not stuck on a dialog.
