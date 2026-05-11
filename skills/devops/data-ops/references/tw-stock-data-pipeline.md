# TW Stock Data Pipeline — Health Check & Merge Workflow

**Session**: 2026-05-06 | **Category**: data-science | **Source**: cron job delivery

## Context
Merging TW stock CSV data between `StockData_History/` (recent updates, ~2025-02 to 2026-05) and `StockData_History_Full/` (historical, 2010-2025) into `StockData_History_Final/`.

## Health Check Results

| Folder | Files | Damaged | Date Range | Rows |
|---|---|---|---|---|
| StockData_History/ | 1,969 | 0 (0.0%) | 2025-02-03 ~ 2026-05-04 | 591,194 |
| StockData_History_Full/ | 418 | 0 (0.0%) | 2010-01-04 ~ 2025-01-22 | 1,353,204 |

**Overlap**: 417 files (both sources have same ticker base names)
**Gateway**: PASS — both folders below 5% corruption threshold

## Merge Results

- Unique files: 1,970 (union of both sources)
- Merged successfully: 1,970/1,970 (0 failures)
- Final date range: 2010-01-04 ~ 2026-05-04 (~16.4 years)
- Total data rows: 1,944,398
- Row count stats: Min=17, Median=303, Avg=987, Max=3,989
- Large-cap old stocks (台泥, 味全, etc.): ~3,989 rows = historical (~3,686) + recent (~303)

## Notes
- `StockData_History_Full/` had 1 file (`4178.TW_永笙-KY.csv`) not in `StockData_History/` (35 rows only, likely recently listed)
- yFinance download generated many "possibly delisted" and OperationalError failures — expected for illiquid TW OTC stocks
- `fetch_tw_historical_custom.py` had a `__main__` escape bug (lines 84) that needed patching
- `merge_stock_data.py` had the same `__main__` escape bug (lines 71) that needed patching
