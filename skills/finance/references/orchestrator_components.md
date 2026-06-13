# TAIEX Orchestrator Components

Architecture for the automated Taiwan Stock monitoring system located in `~/.hermes/scripts/`.

## 1. Master Orchestrator (`taiex_orchestrator.py`)
- **Role**: Sequential trigger for the pipeline.
- **Workflow**:
    1. Runs `taiex_central_data_sync.py`.
    2. Runs `stock_monitor.py` (Personal Channel).
    3. Runs `william_stock_monitor.py` (William).
    4. Runs `group_stock_monitor.py` (Group Channel).

## 2. Central Data Sync (`taiex_central_data_sync.py`)
- **Inputs**: 
    - `StockTracking_Daily.numbers` (via AppleScript).
    - `yfinance` (Yahoo Finance API).
- **Outputs**: `~/.hermes/data/central_stock_data.json`.
- **Logic**:
    - Aggregates unique tickers from multiple sources.
    - Suffix fallback: If `<CODE>.TW` fails, retry with `<CODE>.TWO`.
    - Health Log: Records sync status and success rates in `central_fetcher_health.json`.

## 3. Reporting Bots
- **Shared Pattern**:
    - Read data from `central_stock_data.json`.
    - Calculate deltas vs `stock_last_prices.json`.
    - Calculate P/L based on cost/qty from the central cache.
    - Check timestamp lock in `~/.hermes/data/*.sent.lock` (8min dedupe).
    - Send Markdown formatted messages via Telegram Bot API using an unverified SSL context.

## 4. Key Paths
- **Scripts**: `/Users/bookid/.hermes/scripts/`
- **Data Cache**: `/Users/bookid/.hermes/data/`
- **Source Numbers**: `/Users/bookid/Documents/StockTracking_Daily.numbers`
