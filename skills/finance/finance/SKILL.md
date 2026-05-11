---
name: finance
description: Financial data automation — market queries, portfolio monitoring, earnings analysis, and TAIEX-specific workflows.
version: 1.1.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [finance, stocks, taiex, investigation, earnings, portfolio, telegram]
---

# Finance & Investment Automation

This skill governs automated financial tracking, market data retrieval, and corporate reporting analysis.

## References
- `references/deep_analysis_template.md` (Standard structure for Obsidian financial reports)
- `references/taiex_sync_troubleshooting.md` (Common TAIEX data gaps and fixes)
- `references/twse_api_reliability.md` (Migration from yfinance to Official API)
- `references/incident_log_20260511.md` (Telegram Identity Misalignment & Lock-out)
- `references/multi_bot_routing_map.md` (Bot Tokens, Chat IDs, and Persona Routing)
- `references/taiwan_mops_pitfalls.md` (Bot detection and HTML-disguised PDFs)
- `scripts/lib_market_delivery.py` (Unified Persona-based Telegram delivery logic)
- `scripts/night_session_settlement.py` (05:00 Night Session settlement and archival logic)

## 1. Market Data Retrieval (Yahoo Finance & TWSE API)

Retrieve real-time and historical data with multi-provider redundancy.

- **Yahoo Finance (Batch Retrieval)**: ⚠️ **Do NOT loop individual `yf.Ticker` calls.**
    - **Chunking**: Split into chunks of 10-15. Use `threads=False` and `time.sleep(1)` between chunks.
- **TWSE/OTC Official API (The Robust Path)**: For high-frequency intraday monitoring, bypass Yahoo and query `mis.twse.com.tw` directly to avoid 429 Rate Limits.
    - **Endpoint**: `https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=[QUERY]&json=1&delay=0`
    - **Query Format**: `tse_<CODE>.tw`, `otc_<CODE>.tw`, or `eb_<CODE>.tw` (Emerging/興櫃). Multiple symbols are joined by `|`.
    - **SSL Pitfall**: This endpoint frequently fails with `SSLCertVerificationError` (Missing Subject Key Identifier). 
    - **Fix**: Use `requests.get(url, verify=False)` and `urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)`.
    - **Note**: This is the preferred method for the `taiex_central_data_sync.py` gatherer as of May 2026.

## 2. Portfolio Monitoring & Distribution

### 2.1 Intraday Reporting Schedule & Logic (V4.2)
To maximize signal-to-noise ratio, intraday reports follow a two-state hierarchy:

1. **09:00 Opening Report (The Full Scan)**:
   - **Trigger**: 09:00 - 09:10 Taipei Time.
   - **Content**: Full table of all monitored lists.
   - **Metrics**: `[Open Price]`, `[Prev Close]`, `[Current Price]`, and `[Delta %]`.
2. **Periodic Differential Reporting (The Filtered Scan)**:
   - **Trigger**: Every 20 minutes (09:20 - 13:30).
   - **Filter Protocol (Absolute Value)**: A ticker is ONLY reported if it breaks either of these thresholds to prevent spam:
     - **Threshold A**: `|Current - Prev_Close| / Prev_Close >= 3.0%`
     - **Threshold B**: `|Current - Last_Reported_Price| / Last_Reported_Price >= 2.0%`
   - **State Persistence**: Each monitoring script (Group, User, William) must maintain its own `last_prices.json` cache to calculate Threshold B.

### 2.2 Persona Protocol
        - **「白金之星」 (Star Platinum)**: The primary monitor for the 「高潮不斷」 group (-1003744330314). Use @taiwangupiaoBot. Style: Precision, Force, "ORA ORA ORA!".
        - **「黃金體驗-鎮魂曲」 (GER)**: The core architect for private dialogue (6326497055). Use @kuenmingBot. Style: Absolute Reality, "無駄無駄無駄！".
    - **Robust Messaging**:
        - **Shell Expansion Pitfall**: NEVER send messages containing $, +, or - via terminal curl strings. The shell will misinterpret $401.55 as a variable and truncate it to 01.55.
        - **Fix**: Use execute_code with Python requests and literal/f-strings to preserve numerical precision.
    - **Precision Reporting Rule**: All reports MUST include: **[Current Price] + [Spread (Current - Prev Close)] + [Delta %]**.
    - **Ticker Universe**: Ensure **SYNA** (Synaptics) is included in Night Session monitors as a key proxy for Human Interface and AI momentum.

- **The Gatherer-Reporter Architecture**:

    1. **Gatherer**: Single script (`taiex_central_data_sync.py`) pulls data from Numbers/APIs to a central JSON cache.
    2. **Monitor**: `group_confluence_analysis.py` -> 15:00 EOD high-precision analysis for 「高潮不斷」 group.
- **AI Architect EOD Analysis (15:00)**:
    - **Title**: `AI Architect: 台股收盤綜合分析報告`
    - **Pillars**: 
        1. **盤中觀察 (Micro)**: Volume surges/Price position (Low/Mid/High) from intraday logs.
        2. **歷史趨勢 (Macro)**: SMA/EMA signals & ATR volatility context.
        3. **信心指標 (ML)**: Probabilistic buy/sell signals from pretrained ML models.
    - **Target**: 「高潮不斷」 (Chat ID: -1003744330314).
- **Other Monitors**: `stock_monitor.py` (Personal), `william_stock_monitor.py` (William).
- **Deduplication**: 8-minute locks on all messaging to avoid spam.
- **Group Categorization Context**: Use `references/taiex_group_categories.md` for person-specific watchlists (Kim哥, 順風老師, etc.).
- **Timing Goal**: Market Close + 30m (15:00) is the standard for final "Architect" reports to capture T-0 sentiment accurately.
- **Numbers Data Updates**: Use targeted AppleScript to update or read financial values.
    - **Quick Extraction (Bulk)**: For smaller tables (e.g., Portfolio), retrieving all values at once is faster and less prone to indexing errors.
        ```applescript
        tell application "Numbers"
            open "/Users/bookid/Documents/StockTracking_Daily.numbers"
            tell document 1 to tell sheet "Portfolio" to tell table 1
                return value of every cell
            end tell
        end tell
        ```
    - **Row Iteration (Precision)**: Use when filtering or updating specific tickers. Search 'cell 1' for ticker -> Update 'cell X' in the same row.
- **Telegram Bot Error Code Triage (4xx Series)**:
    - **401 Unauthorized**: Token is invalid, revoked, or expired. Requires a new Token from BotFather.
    - **403 Forbidden**: Bot cannot initiate conversation (BotFather policy). User MUST send `/start` to the bot first. Common after user clears chat history OR if the bot tries to DM a user who hasn't messaged it in the current session.
    - **400 Bad Request: chat not found**: The Chat ID was valid once but is now unrecognized (User blocked bot or revoked access).
- **Sync Triage & Connectivity (The Architect's Path)**: When the user says "still no message" or "the bot is not responding":
    1. **Identity Check**: Audit `~/.hermes/.env`. Verify `TELEGRAM_BOT_TOKEN` matches the desired persona from `references/multi_bot_routing_map.md`. A common failure mode is the Gateway launching with a sub-bot (e.g., Star Platinum) token instead of the primary (Gold Experience).
    2. **Permission Check**: Audit `~/.hermes/config.yaml`. If `telegram.allowed_channels` is populated, the bot **silently ignores** all DMs from IDs not in that list. To fix: set to `[]` or `""` for open access.
    3. **Zombie Purge**: Run `ps aux | grep hermes`. Conflict between multiple polling instances causes message drops. Solution: `pkill -9 hermes` followed by a clean `hermes gateway run --replace`.
    4. **Webhook Audit**: Use `requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo")`. If `pending_update_count > 0` but logs are silent, the local listener is stalled.
- **Numbers Data Updates**: Use targeted AppleScript...
    2. Restart with `hermes gateway run --replace` (optionally via `terminal(background=true)`).
    3. Verify connectivity in `~/.hermes/logs/agent.log`.
- **Gatekeeper Pattern**: Before running energy-intensive tasks (ML, Data Sync, PDF Scans), execute a lightweight gatekeeper script (`scripts/market_gatekeeper.py` for Night or `scripts/day_market_gatekeeper.py` for Day) to exit immediately if the market is closed.
- **Frequency Decoupling**: Sync data frequently (e.g., every 10 mins) to maintain high-resolution intraday logs (`~/.hermes/data/intraday_data_log.csv`), but report to the user less frequently (e.g., every 20 mins) via reporting locks (18-minute dedupe) to minimize message spam. 
- **Volume & Intraday Momentum**: Always capture `Volume` during syncs. Aggregate intraday price/volume updates into a local CSV to serve as context for EOD (End of Day) analysis scripts.
- **Portfolio Analysis (EOD)**: Daily at 14:30 (Market Close + 1h), run a deep analysis on personal holdings using ML/Trend indicators, but ONLY if the day gatekeeper passes.

## 3. Data Integrity & Quality Control

- **File Health Checks (Mandatory)**: All downloads must be verified immediately:
    - **Size**: Alert if smaller than 1KB (likely an error page or empty file).
    - **Data Density**: Alert if NaN count in core columns (e.g., Close, EPS) exceeds 5%.
    - **Historical Integrity**: Verify historical depth (e.g., must start from at least 2010 for backfills).
- **Incident Escalation (3-Failure Protocol)**:
    - If a download or sync task fails **3 consecutive times**, do not just log and restart.
    - **Self-Diagnosis**: Immediately perform a `web_search` to investigate the root cause (e.g., ticker change, delisting, TAIEX maintenance).
    - **Escalation**: Notify the user via Telegram (@kuenmingBot) using the structure: `[故障類型] -> [調查診斷] -> [替代方案]`.
- **Incremental Sync**: For large-scale history (1,900+ stocks), identify the last date in local CSVs and fetch only missing rows via `yfinance`. See `scripts/daily_historical_sync.py`.
- **Large-Batch Pitfalls**: `yfinance` with `threads=True` can trigger SQLite database locks (`OperationalError: unable to open database file`). **Fix**: Disable threading (`threads=False`) and periodically clear `~/.cache/py-yfinance/*`.
- **High-Precision Rendering (DEFAULT)**: As of 2026-05-10, the user has DEPRECATED `mdcat` in favor of high-precision PIL image rendering for ALL `.md` files. 
    - **Logic**: Use `scripts/render_md_to_img.py` logic (Dynamic Height + Rich Alignment + CJK Font Fallback).
    - **Policy**: "Show, don't store." Generate the image in `~/.hermes/scratch/`, display via `MEDIA:`, and refrain from saving to persistent locations unless explicitly requested.
- **Metric Extraction**: Focus on the Big Four (Revenue, GM, Operating Margin, EPS) plus Segment Breakdown and Guidance.
- **Organized Storage Rule (POST-QC)**: Once a report passes the Health Check (Section 3.1), it MUST be moved from the staging directory (e.g., `~/Documents/Reports/2026_Q1/`) to a dedicated company-specific subfolder (e.g., `~/Documents/Reports/2026_Q1/TSMC/`). Folder names should be English company names (e.g., `Quanta`, `MediaTek`).


## 4. Night Session & Market Integrity

- **Reality Verification (The Zero Point)**: ⚠️ **Watch for Index Basis Errors.**
- **Night Session Gatekeeper (Schedule-Based)**: ⚠️ **Do NOT rely on Yahoo Market Status for Gatekeeping.**
    - **Active Session Logic**:
        - **Mon-Fri**: 15:00 - 23:59 (Today's Trade)
        - **Tue-Sat**: 00:00 - 05:00 (Yesterday's Trade)
    - **Logic Implementation**: Check local time vs. weekday schedule (Mon=0, Sat=5). Mon 15:00 to Sat 05:00 is the full operational window for Night Reporting.
    - **Weekend Silence**: Saturday 06:00 to Monday 15:00 (Taipei Time).
- **Reality Verification (The Zero Point)**: ⚠️ **Watch for Index Basis Errors.**

## 5. Historical Data & AI Predictors

- **Incremental Sync**: Daily at 05:00, update all local CSVs with the latest 10 days of data to bridge gaps without full re-downloads.
    - Use `scripts/daily_historical_sync.py`. Ensure date deduplication (`drop_duplicates`) and sorting.
- **ML Signal Engine**: 
    - **Features**: Trend (SMA/EMA), Momentum (RSI/MACD), Volatility (ATR), and Volume Ratio.
    - **Target**: 5-day forward return binary classification (>3% or <-3%).
    - **Training**: Periodically retrain on bellwethers (Top 10 cap) to maintain signal edge.
    - **Portfolio Analysis**: Prioritize ML inference on the user's active holdings (`personal_data`) before scanning the broad market.

## 6. Platform Specifics (Taiwan MOPS)

- **Navigation**: Use MOPS (mops.twse.com.tw) -> 財務報告書 -> 單一公司.
- **Minguo Calendar**: MOPS queries use ROC Years. Formula: `Year - 1911` (e.g., 2026 = 115).
- **Bot Detection & Fake PDFs**: Watch for 13-15KB files. Some companies (e.g., 2382 Quanta) upload HTML files disguised with a `.pdf` extension. 
    - **Verification**: Check file type via `file <path>` or check if content starts with `<!DOCTYPE html>`.
- **Extraction Fallback**: If `pdftotext` is missing, use Python's `PyPDF2` or `pdfplumber` via `execute_code`.
- **Timing**: Financial reports are legally approved during Board Meetings. Public release on MOPS often lags the meeting by 0-24 hours. If an announcement is made on Day X, check MOPS on Evening X or Morning X+1.
- **TAIEX Reporting Deadlines (Calendar Year)**: Q1 (May 15), Q2/H1 (Aug 14), Q3 (Nov 14), Q4/Annual (Mar 31 following year).
- **ETF Distinction**: When users ask for "earnings" for TAIEX tickers starting with `00`, identify them as ETFs (e.g., 0050). ETFs report dividends and NAV, not EPS/Earnings calls.
- **Ming-guo Year Formula**: 2026 = 115 (Year - 1911). Standard for MOPS queries.

## 7. Data Storage & JSON Conventions

- **Numbers Automation (Rotation & Robustness)**: When syncing with Numbers files, implement a "Date Rotation" pattern and a "Dynamic Finder" for open documents.
    - **Rotation Workflow**: `mv StockTracking_Daily.numbers StockTracking_$DATE.numbers && ln -s StockTracking_$DATE.numbers StockTracking_Daily.numbers`.
    - **Dynamic Finder (AppleScript)**: Handle cases where Numbers opens the dated file instead of the symlink.
        ```applescript
        tell application "Numbers"
            set targetDoc to missing value
            set allDocs to name of every document
            repeat with d in allDocs
                if d starts with "StockTracking" then
                    set targetDoc to d
                    exit repeat
                end if
            end repeat
            -- Use 'document targetDoc' for further queries
        end tell
        ```
    - **Cell Protection**: Always use `try-catch` blocks in AppleScript when reading cells (e.g., `qty`, `avg cost`) to handle `missing value` or non-numeric strings gracefully.

- **Update Logic**: When merging new stocks, always verify if the target is a list or dict. Prefer `dict.update()` for ticker-based storage.

### 8. Detailed PDF Analysis SOP (Deep Analysis)
When the user requests to "Read and analyze a PDF financial report", adhere to the following strict protocol:
1. **Extraction**: Identify key parameters: **Revenue, Gross Margin, Operating Profit, Non-Operating Items, Net Profit (Pre/Post tax), and EPS**.
2. **Contextual Analysis**: Beyond numbers, explain *why* metrics moved (e.g., policy tailwinds, segment shifts, order backlog).
3. **Artifact Creation**: Generate a high-quality Obsidian-compatible `.md` report.
   - **Chronology (Absolute Requirement)**: ⚠️ **Calendar Quarters ONLY.** Even if a company reports "Fiscal Q3" (e.g., SYNA in May 2026), it MUST be analyzed and archived as **Calendar 2026 Q1**.
    - **Reasoning**: To maintain a consistent time-series across the entire portfolio. Confusing Fiscal vs. Calendar quarters is a critical architectural failure.
   - **Path Template**: `~/Documents/Obsidian Vault/Finance/DeepAnalysis/[YEAR]Q[Quarter]/[Ticker]_[English_Name].md` (e.g., `.../2026Q1/SYNA.md`).
   - **Structure**:
     - # [Company Name] [Year] [Quarter] Deep Analysis
     - ## 📊 Core Metrics (Table)
     - ## 🔍 Detailed Parameter Breakdown (Bullet points with deep dives)
     - ## 🚀 Strategic Outlook & Forward Guidance
     - ## 🧠 Architect's Summary (Root Cause -> Path -> Result)
4. **Validation**: Ensure data consistency with `StockTracking_Daily.numbers` and other local records.

### 9. Night Session Settlement (05:00 Archive)
Every trading day at **05:00 Taipei Time**, the system performs a final settlement of the Night Session data.
- **Workflow**:
    1. **Final Summary**: Execute `tw_night_monitor_adri.py` and `tw_night_session_hourly.py` one last time to capture the session close.
    2. **Archival**: Copy all 10-minute intraday batch logs from `~/Documents/Reports/Analysis_Logs/Daily_Intraday_Batches` to a dated archive in `~/Documents/Reports/NightSession/[YYYY-MM-DD]/`.
    3. **Obsidian Sync**: Push a settlement summary report (`Settlement_Report.md`) to the Obsidian vault at `~/Documents/Obsidian Vault/Finance/DailyReports/` for asynchronous review.
- **Script**: `scripts/night_session_settlement.py`.
- **Board vs. Report**: The next_report_date in calendars is often the Board Meeting date. If searching ON that day, the report may not be uploaded until after market close.
- **HTML-PDF Trap**: Don't count on `read_file` or `pdftext` alone. If a file fails to parse as PDF, check if it is raw HTML/text first.
- **JSON List vs. Dict**: `earnings_calendar.json` is frequently used; ensure your code matches the existing schema (Dict-keyed by ticker) before writing.
- **Weekend Stale Data Spam**: Automated night reports may send static Friday data on weekends. Use "Weekend Silence" logic (Saturday 06:00 to Monday 08:00 Taipei Time) to avoid redundancy.
- **Path Divergence**: Avoid `/home/user/` hardcoding. Use `~/` or `os.path.expanduser` to accommodate macOS/Linux differences.

## See Also
- `apple`: For extracting portfolio data from Numbers via AppleScript.
- `data-ops`: For orchestration and debouncing patterns used in the sync pipeline.
