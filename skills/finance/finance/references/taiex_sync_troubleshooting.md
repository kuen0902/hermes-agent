# TAIEX Sync & Monitoring Troubleshooting

## The 'Single Quote' Prefix Pitfall
In Apple Numbers, users often prefix Stock IDs with a single quote (e.g., `'2330`) to force the cell to treat the number as text and prevent it from being formatted as a currency or getting `.0` appended.
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
If data-fetching fails (e.g., due to rate limits), monitoring scripts may fail with `UnboundLocalError` if variables like `top3` are defined inside an `if stats:` block but accessed later without checking.
- **Fix**: Always initialize aggregation variables (e.g., `top3 = [], bottom3 = []`) at the start of `main()` or wrap the entire summary generation inside the `if stats:` guard.

## Batch TAIEX Ticker Mapping
When using `yf.download([list_of_codes])` for TAIEX:
- Codes like `2330` should be transformed into a search list `['2330.TW', '2330.TWO']`.
- The returned DataFrame index will be a MultiIndex. Use `df.xs('Close', axis=1, level=1)` or iterate levels to extract the correct symbol-specific price series.

## Telegram Formatting Pitfalls
When sending combined reports (e.g., merging ADR + NQ reports), ensure the `parse_mode` is explicitly set to `Markdown` in the `sendMessage` API call. If a single special character (like `_` or `*`) is unclosed in either sub-report, the entire message will fail with a `400 Bad Request`.
- **Fallback**: Implement a `try...except` that retries with `parse_mode=None` if the first attempt fails.
