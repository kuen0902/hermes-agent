# Watchlist Group Maintenance SOP (清單更新標準作業程序)

When a user requests to change or update a specific stock group/watchlist (e.g., "William's List", "Kim's List"), you MUST perform the following 5-step synchronization to ensure system-wide consistency across the Registry, Database, Sync Engine, and Swift Monitor.

## 1. Update Central Registry
Modify `~/.hermes/data/master_stock_registry.json`.
- Update the specific list key (e.g., `william_codes`).
- Ensure all new codes have their Chinese names registered in `official_names`.

## 2. Synchronize SQLite Database
The `portfolio.db` (in `~/.hermes/data/`) is the source for TUI and certain automated reports.
- **Table**: `watchlist`
- **Columns**: `code`, `name`, `added_at`, `group_name`
- **Action**: 
  1. `DELETE FROM watchlist WHERE group_name = 'William哥推薦組';` (or relevant group)
  2. `INSERT OR REPLACE` the new codes. Use `datetime('now')` for `added_at`.

## 3. Patch Python Sync Engine
The `taiex_central_data_sync.py` often contains hardcoded `william_defaults` or `group_defaults` used as fallbacks when the Numbers sheet or DB is inaccessible.
- **Path**: `~/.hermes/scripts/taiex_central_data_sync.py`
- **Action**: Update the dictionary values matching the new user request.

## 4. Patch Swift Monitoring Engine
The `hermes_monitor.swift` script handles real-time Telegram alerts and has its own category mapping logic.
- **Path**: `~/.hermes/scripts/hermes_monitor.swift`
- **Action**: Locate `getTargetStocks` function and update the array for the relevant `profileName` (e.g., `william`, `group`).
- **Binary**: Since we use `/usr/bin/swift` to run code directly now (Session 2026-05-20), no recompilation is needed, but verifying the script syntax is mandatory.

## 5. Verification Gate
- **Sync**: Run `/Users/bookid/.hermes/.venv/bin/python /Users/bookid/.hermes/scripts/taiex_central_data_sync.py --force`.
- **Monitor**: Test the Swift output with `swift /Users/bookid/.hermes/scripts/hermes_monitor.swift --profile <name> --report-only`.
- **Personality**: Confirm completion with "無駄無駄無駄！".

## ⚠️ Pitfalls
- **Naming Mismatches**: Ensure the `group_name` string in the DB matches exactly what the Swift/Python logic expects (e.g., "William哥推薦組" vs "William觀察名單").
- **Delisted Stocks**: If the sync returns 404/Delisted, cross-check with the user before removing.
- **Schema Variance**: Always check `.schema watchlist` before inserting, as columns like `added_at` vs `updated_at` may vary.
