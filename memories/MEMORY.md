Deep Analysis SOP: Extract 5 params (Rev, GM, OPM, Net, EPS) + Explain + Struct .md to Obsidian Vault at `Finance/DeepAnalysis/[YEAR][Q]/` (Calendar Q). Current Year 2026. SYNA May 2026 report = 2026Q1.
§
User has a specific interest in AI research tools and knowledge management, currently focusing on Google NotebookLM workflows.
§
User has a single lot (1000 shares) of MediaTek (2454) with a cost basis of 2655, and Unimicron (3037) with a cost basis of 514. Verified these against user's actual portfolio screenshots for 100% accuracy in calculations.
§
Monitoring Filter Rule: Use absolute percentage values for diff thresholds (e.g., |Price-PrevClose| > 3% or |Price-LastPrice| > 2%). Do not send reports with "Unhealthy" or "Error" tags; diagnose and verify health before delivery.
§
Primary stock monitoring scripts (stock_monitor.py, group_stock_monitor.py) are linked to the 'StockTracking_Daily.numbers' spreadsheet as the source of truth for the 22 core holdings and 39 monitored symbols.
§
User workflow: Provides screenshots of mobile trading apps (e.g., "Today's Trades") to trigger portfolio reconciliation. Agent is expected to parse the image, calculate realized P/L against cost basis in memory/JSON, and automate the removal of sold positions from the 'StockTracking_Daily.numbers' spreadsheet via AppleScript.
§
2026-05-13 10:16: 移除四項原本用於數據備份與補償的 Cron Jobs (9b78b006628c, fd2cf872b2f7, 642ad241f32e, a9edac269e3e)。
§
User prefers having significant system administrative changes (like cron job removals) logged into persistent memory for auditing.
§
System Architecture: All TAIEX monitoring is now centralized via `taiex_orchestrator.py` (Job `f95f14b437ee`). Legacy individual monitor cron jobs are paused to ensure data consistency and prevent API 429 errors. Monitoring is filtered to report only |Price-PrevClose| > 3% or |Price-LastPrice| > 2%.
§
User has 1 lot (1000 shares) of ADATA (3260) with a cost basis of 463.19. (Note: Cost basis verified as 463.19 per user input 2026-05-13).