# TAIEX Orchestrator Flow (Gatherer-Reporter)

The current TAIEX automation in this environment follows a multi-script, decoupled architecture managed by a central orchestrator.

## Component Breakdown

1. **Orchestrator**: `/Users/bookid/.hermes/scripts/taiex_orchestrator.py`
    - **Purpose**: Master trigger for the entire pipeline.
    - **Logic**: Sequential execution of the Gatherer, followed by the specific Reporter bots.
    - **Timeout Note**: Takes ~2-3 minutes; requires `terminal(timeout=300)`.

2. **The Gatherer**: `/Users/bookid/.hermes/scripts/taiex_central_data_sync.py`
    - **Input 1 (Numbers)**: Fetches `Code`, `Name`, `Qty`, `Avg Cost` from `StockTracking_Daily.numbers` (Portfolio sheet).
    - **Dynamic Integration**: Reporter scripts (like `group_stock_monitor.py`) now prioritize `personal_data` from the central JSON. Instead of hardcoded watchlists, they dynamically generate a "我的核心持股" (Core Holdings) category. This ensures updates in the Numbers file reflect immediately in Telegram without script modifications.
    - **Input 2 (Hardcoded)**: Fallback dictionaries for William and Group channels.
    - **Logic**: \n        - Deduplicates all tickers.\n        - Fetches via `yfinance` with `.TW` -> `.TWO` retry logic.\n        - **Synchronous Data**: Captures Price + **Volume**.\n        - **Persistence**: Appends every 10-minute snapshot to `~/.hermes/data/intraday_data_log.csv` for intraday momentum analysis.\n        - Checks health (>80% fetch rate = Healthy).
    - **Output**: Writes unified state to `~/.hermes/data/central_stock_data.json`.

3. **The Reporters** (Personal, William, Group):
    - `stock_monitor.py`
    - `william_stock_monitor.py`
    - `group_stock_monitor.py`
    - **Logic**:
        - Read *only* from `central_stock_data.json` (no external API calls).
        - **Reporting Pacing**: Use file-based locks (`~/.hermes/data/*.lock`) with an **18-minute dedupe** window. This ensures that even though the Orchestrator runs every 10 minutes, the user only receives reports every 20 minutes (frequency decoupling).
        - Calculate unrealized P/L based on Numbers data.
        - Send to specific Telegram Chat IDs (Personal/William/Group).

4. **The EOD Analyzer**: `/Users/bookid/.hermes/scripts/run_portfolio_eod.sh`
    - **Trigger**: 14:30 Daily.
    - **Logic**: 
        - Runs `daily_historical_sync.py --fast` to sync history for core holdings.
        - Runs `confluence_eod_analysis.py` to combine intraday volume momentum with ML macro trend signals.
        - **Output**: Generates Markdown reports in `~/Documents/Reports/Analysis_Logs/Daily_Confluence/`.

## Data Schema Summary
- **Primary Data**: `~/.hermes/data/central_stock_data.json`
- **Delta/10M Tracking**: `~/.hermes/data/*_last_prices.json`
- **Locks**: `~/.hermes/data/*.lock`
