# Swift Native Engine: Stock Mapping Audit

The Swift-based sync engine (`hermes_sync.swift`) and monitor (`hermes_monitor.swift`) rely on two primary sources for name mapping:

1. **Portfolio Source**: `personal_data` extracted from SQLite via `portfolio_tool.py`.
2. **Registry Source**: `/Users/bookid/.hermes/data/master_stock_registry.json`.

## 🚨 Critical Failure: Missing Name in Group Alerts
If a stock code (e.g., `2409`) shows up in a Telegram alert without its name, the mapping has failed.

### Verification Flow:
1. **Check Master Registry**: Open `~/.hermes/data/master_stock_registry.json`. Ensure the code exists in `official_names`.
   ```json
   "official_names": {
     "2409": "友達"
   }
   ```
2. **Run Manual Sync**: Execute the sync script to propagate the new registry data into the runtime cache (`central_stock_data.json`).
   ```bash
   # Run the Swift orchestrator wrapper
   /Users/bookid/.hermes/scripts/run_hermes_sync.sh
   ```
3. **Verify Central Cache**: Grep the code in `~/.hermes/data/central_stock_data.json`. The `full_mapping` object must contain the name.
   ```bash
   grep "2409" ~/.hermes/data/central_stock_data.json
   ```

### Case Study: 2409 (友達)
On 2026-05-19, 2409 appeared as code-only in group alerts. The fix involved adding it to `master_stock_registry.json` and triggering a sync.
