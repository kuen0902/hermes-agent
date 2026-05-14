# TAIEX Sync & Monitoring Troubleshooting

## 1. Monitor Silence (No Messages Received)
- **Cause A: Shell Script Permissions**. Scripts like `run_portfolio_eod.sh` may lose executable bits if edited outside the terminal.
    - **Fix**: Run `chmod +x /Users/bookid/.hermes/scripts/*.sh`.
- **Cause B: Sync Timeouts (High Volume)**. Synchronizing 1,900+ stock CSVs can exceed 60s, causing cron failure (Exit Code 124).
    - **Fix**: Use the `Fast Sync` mode (`--fast`). This restricts historical updates to tickers defined in the central cache.
- **Cause C: Empty Central Cache**. If `taiex_central_data_sync.py` fails to read Numbers (e.g., Numbers is closed), the `personal_data` field in the central JSON becomes `{}`. Monitors reading this will have no tickers to check.
    - **Fix**: Check `pgrep Numbers`. Use `open StockTracking_Daily.numbers` to force it open.
- **Cause B: Stale Telegram Token**. Even if the script finds 10+ changes, it will fail to send if the token is unauthorized (401).
    - **Fix**: Test the token with `curl https://api.telegram.org/bot<TOKEN>/getMe`.
- **Cause D: Missing Cost Basis (0.0)**. If `central_stock_data.json` shows cost as `0.0`, the P/L calculation in reports will be skewed or hidden.
    - **Fix**: Ensure the Numbers file `Portfolio` sheet has valid numbers in Column 5. AppleScript may return `missing value` if cells are formatted as plain text or are empty. Check `taiex_central_data_sync.py` logs for `Numbers Fetch Error`.
- **Cause E: Lock Files**. Check for `*.lock` files in `~/.hermes/data/`. If a script crashed before releasing a lock, it might skip the next run.

## 2. Numbers Extraction Index Errors
- **Symptom**: `execution error: Numbers Creator Studio發生錯誤：無法取得「document 1」。索引錯誤。 (-1719)`
- **Reason**: AppleScript's `document 1` refers to the currently active window. If the user has multiple files open or No file open, it fails.
- **Fix**: Use the "Dynamic Finder" pattern in `finance/SKILL.md` (Section 7) to find the document by its name prefixing with `StockTracking`.

- **Symptom**: `yfinance` or market scrapers return 404/Not Found for the ticker `'2330.TW`.
- **Fix**: In your Python parser, use `ticker.strip("'")` before appending the `.TW` suffix.

## Emerging Stocks (興櫃) Visibility
Stock codes in the 7000+ range or recently listed symbols (e.g., `7815 新特`) may be on the Emerging Board (興櫃).
- **Symptom**: `taiex_central_data_sync.py` returns `Failed` or 'Empty' for symbols in the 7-series or 68-series.
- **Cause**: TWSE API handles Main (`tse`) and OTC (`otc`) separately from Emerging (`eb`). Standard gathering loops often only iterate `tse` and `otc`.
- **Fix (API)**: Add `eb_<CODE>.tw` to the `ex_ch` query string (e.g., `https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=eb_7815.tw`).
- **Fix (Fallback)**: If the TWSE API fails, use the `yfinance` provider as a secondary data source.

## Orchestrator vs. Night Session
For this user, monitoring is split into two distinct modes:
1. **Day Session (Orchestrator)**: `*/10 9-13 * * 1-5`.
   - Script: `taiex_orchestrator.py`
   - Role: Coordinates `central_data_sync` followed by distribution to multiple niche bots (William, Group, User).
2. **Night Session**: `*/20 15-23,0-5 * * *`.
   - Script: `run_night_report.py`
   - Role: Monitors NQ (Nasdaq), TSM (ADR), and EWT (ETF) to provide leading indicators for the next morning's open.

## UnboundLocalError in Reporting
If data-fetching fails (e.g., due to rate limits), monitoring scripts may fail with `UnboundLocalError`.
- **The Unpacking Trap**: ⚠️ **Avoid using a variable as its own default value in the same unpacking line.**
    - **Bad**: `price, prev, open_p = data['price'], data['prev_close'], data.get('open', price)` (Raises error because `price` is not yet defined).
    - **Fix**: Split the assignment into two steps:
        ```python
        price = data['price']
        open_p = data.get('open', price) # price is now defined
        ```
- **Fallback**: Always initialize aggregation variables (e.g., `top3 = [], bottom3 = []`) at the start of `main()`.

## Batch TAIEX Ticker Mapping
When using `yf.download([list_of_codes])` for TAIEX:
- Codes like `2330` should be transformed into a search list `['2330.TW', '2330.TWO']`.
- The returned DataFrame index will be a MultiIndex. Use `df.xs('Close', axis=1, level=1)` or iterate levels to extract the correct symbol-specific price series.

## Telegram Formatting Pitfalls
When sending combined reports (e.g., merging ADR + NQ reports), ensure the `parse_mode` is explicitly set to `Markdown` in the `sendMessage` API call. If a single special character (like `_` or `*`) is unclosed in either sub-report, the entire message will fail with a `400 Bad Request`.
- **Fallback**: Implement a `try...except` that retries with `parse_mode=None` if the first attempt fails.
