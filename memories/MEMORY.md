Deep Analysis SOP: Extract 5 params (Rev, GM, OPM, Net, EPS) + Explain + Struct .md to Obsidian Vault at `Finance/DeepAnalysis/[YEAR][Q]/` (Calendar Q). Current Year 2026. SYNA May 2026 report = 2026Q1.
§
User has a specific interest in AI research tools and knowledge management, currently focusing on Google NotebookLM workflows.
§
User has holdings (costs): MediaTek (2454) 3430, Kingboard (2368) 1410, Unimicron (3037) 514, ADATA (3260) 463.19, Universal Microelectronics (2413) 57.53. Verified against 'Portfolio' sheet in StockTracking_Daily.numbers. Email: kuen0902@gmail.com.
§
Primary stock monitoring scripts (stock_monitor.py, group_stock_monitor.py) are linked to the 'StockTracking_Daily.numbers' spreadsheet as the source of truth for the 22 core holdings and 39 monitored symbols.
§
User workflow: Provides screenshots of mobile trading apps (e.g., "Today's Trades") to trigger portfolio reconciliation. Agent is expected to parse the image, calculate realized P/L against cost basis in memory/JSON, and automate the removal of sold positions from the 'StockTracking_Daily.numbers' spreadsheet via AppleScript.
§
2026-05-15: Upgraded to Python 3.14.4 (venv_314) with PEP 695 support. Fixed 09:00 Cron failure where Swift scripts were misidentified as Python by wrapping the Orchestrator (f95f14b437ee) in run_taiex_orchestrator.sh. Future finance automation prioritized for native Swift.
§
TAIEX Monitor: Runs */10 9-12. Group ID: -1003744330314, Private ID: 6326497055. Swift binary at ~/.hermes/scripts/hermes_monitor. ADATA (3260) cost: 463.19. Confirmed price/qty required before transactions.
§
User has 1 lot (1000 shares) of ADATA (3260) with a cost basis of 463.19. (Note: Cost basis verified as 463.19 per user input 2026-05-13).
§
Portfolio management requires explicit confirmation of Stock Code, Price, and Quantity; never assume default values for transactions.
§
Profile Hierarchy: `.env` override > `config.yaml`. To silence bot in groups while reporting, remove chat ID from `allowed_channels` and ensure `.env` is restrictive. Direct API scripts bypass Gateway silence.