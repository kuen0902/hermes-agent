Deep Analysis SOP: Extract 5 params (Rev, GM, OPM, Net, EPS) + Explain + Struct .md to Obsidian Vault at `Finance/DeepAnalysis/[YEAR][Q]/` (Calendar Q). Current Year 2026. SYNA May 2026 report = 2026Q1.
§
User has a specific interest in AI research tools and knowledge management, currently focusing on Google NotebookLM workflows.
§
Holdings verified in 'Portfolio' numbers sheet (Costs): 2454 (3430), 2368 (1410), 3037 (514), ADATA 3260 (463.19, 1 lot), 2413 (57.53). Explicit confirmation of Code/Price/Qty is mandatory for all transactions. Email: kuen0902@gmail.com.
§
Star Platinum Bot (8737129549) handles all stock alerts (Personal, Group, William). GER (@kuenmingBot) is C&C. Avoid built-in send_message tool due to token conflicts; use Swift/Python scripts with hardcoded SP token. Verify 43 tickers daily. ML Guardrails: 6806, 1591, 3349 blacklisted (~/.hermes/data/removed_trash_stocks.json); engine filters price < 5.0 and blacklist inclusion.
§
User workflow: Provides screenshots of mobile trading apps (e.g., "Today's Trades") to trigger portfolio reconciliation. Agent is expected to parse the image, calculate realized P/L against cost basis in memory/JSON, and automate the removal of sold positions from the 'StockTracking_Daily.numbers' spreadsheet via AppleScript.
§
Intraday ML Risk and Tiered Milestone alerts (via hermes_monitor and intraday_risk_monitor.py) are partitioned into Personal (DM), Group (Shared), and William bubbles, but are all delivered via the Star Platinum bot (8737129549). Verify 43 tickers (including 2409 mapping) sync daily.
§
TAIEX Monitor: Runs */10 9-12. Group ID: -1003744330314, Private ID: 6326497055. Swift binary at ~/.hermes/scripts/hermes_monitor. ADATA (3260) cost: 463.19. Confirmed price/qty required before transactions.