Deep Analysis SOP: Extract 5 params (Rev, GM, OPM, Net, EPS) + Explain + Struct .md to Obsidian Vault at `Finance/DeepAnalysis/[YEAR][Q]/` (Calendar Q). Current Year 2026. SYNA May 2026 report = 2026Q1.
§
User has a specific interest in AI research tools and knowledge management, currently focusing on Google NotebookLM workflows.
§
User has holdings: MediaTek (2454) cost 3430, Kingboard (2368) cost 1410 (Purchased 05-12), Unimicron (3037) cost 514, ADATA (3260) cost 463.19. Sold: Advantech (2395) @ 474 (05-11), MTK old lot (2655) on 05-12. Verified against 'Portfolio' sheet. Email: kuen0902@gmail.com.
§
Primary stock monitoring scripts (stock_monitor.py, group_stock_monitor.py) are linked to the 'StockTracking_Daily.numbers' spreadsheet as the source of truth for the 22 core holdings and 39 monitored symbols.
§
User workflow: Provides screenshots of mobile trading apps (e.g., "Today's Trades") to trigger portfolio reconciliation. Agent is expected to parse the image, calculate realized P/L against cost basis in memory/JSON, and automate the removal of sold positions from the 'StockTracking_Daily.numbers' spreadsheet via AppleScript.
§
2026-05-15: System environment upgraded to Python 3.14.4. Primary venv is now /Users/bookid/workspace/hermes-agent/venv_314. All finance-related Cron jobs patched to use this path. Syntax compatibility now supports PEP 695 'type'.
§
User prefers having significant system administrative changes (like cron job removals) logged into persistent memory for auditing.
§
Sys Arch: TAIEX monitoring via `taiex_orchestrator.py` (Job f95f14b437ee). Tiers: [3,5,7,9]. No personal data in group reports. Venv: `/Users/bookid/workspace/hermes-agent/venv_314/bin/python`. Hermes: `/Users/bookid/.local/bin/hermes`. Environment: Python 3.14.4.
§
User has 1 lot (1000 shares) of ADATA (3260) with a cost basis of 463.19. (Note: Cost basis verified as 463.19 per user input 2026-05-13).
§
2026-05-15 (System Update): Successfully upgraded system environment to Python 3.14.4 (`venv_314`). Re-enabled PEP 695 type hints. All cron jobs are successfully running on the new environment. 
Strategic Directive: Future architecture and new feature development will primarily focus on native Swift implementation to maximize performance and concurrency.