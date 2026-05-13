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
- `references/night_session_network_stability.md` (Troubleshooting and fixes for night session connectivity)
- `references/taiex_sync_troubleshooting.md` (Common TAIEX data gaps and fixes)
- `references/incident_log_20260513.md` (Race Condition & 3-Stock Fallback Audit)
- `references/twse_api_reliability.md` (Migration from yfinance to Official API)
- `references/incident_log_20260511.md` (Telegram Identity Misalignment & Lock-out)
- `references/taiex_bot_authority_mapping.md` (Authoritative Bot roles and Private/Group channel routing)
- `references/multi_bot_routing_map.md` (Bot Tokens, Chat IDs, and Persona Routing)
- `references/taiwan_mops_pitfalls.md` (Bot detection and HTML-disguised PDFs)
- `references/vision_to_sync_workflow.md` (Interpreting trade screenshots to update Numbers)
- `references/resilient_bridge_pattern.md` (Multi-tier fallback for 429 Rate Limits)
- `scripts/lib_market_delivery.py` (Unified Persona-based Telegram delivery logic)
- `scripts/night_session_settlement.py` (05:00 Night Session settlement and archival logic)

## 1. Market Data Retrieval (Yahoo Finance & TWSE API)

Retrieve real-time and historical data with multi-provider redundancy.

- **The Market Open Gatekeeper (TAIEX)**: ⚠️ **Mandatory check for automated cron jobs.**
    - **Logic**: Fetch history for a bellwether (e.g., `2330.TW`). If the last index date is not "today" (Taipei time), terminate the task.
    - **Code Snippet**:
        ```python
        import yfinance as yf
        from datetime import datetime
        import pytz
        ticker = yf.Ticker("2330.TW")
        last_date = ticker.history(period="1d").index[-1].to_pydatetime().date()
        today = datetime.now(pytz.timezone('Asia/Taipei')).date()
        if last_date != today:
            print("[SILENT] Market is closed today.")
            exit()
        ```
- **Yahoo Finance (Batch Retrieval)**: ⚠️ **Do NOT loop individual `yf.Ticker` calls.**
    - **Chunking**: Split into chunks of 10-15. Use `threads=False` and `time.sleep(1)` between chunks.
- **The Hybrid Fallback Pattern**:
    - **Logic**: Use the TWSE API as primary (speed/accuracy). If a ticker returns `None`, trigger the `yfinance` fallback.
    - **Code Snippet**: See `templates/yfinance_fallback_logic.py`.
- **The Resilient Bridge (Anti-429 Defense)**: ⚠️ **Use when Yahoo Finance returns 429/Empty.**
    - **Trigger**: Catch `yfinance` exceptions or check if return is `None`.
    - **Logic**: Use a browser agent to scrape Google Finance/HiStock or use `web_search` + `web_extract` on search snippets.
    - **Cache Schema**: Results MUST be cached in `/Users/bookid/.hermes/data/market_prices_bridge.json` with the following format:
        ```json
        {
          "NQ": price, 
          "TSM": price, 
          "NVDA": price, 
          "SYNA": price, 
          "FITXP": price, 
          "timestamp": "ISO-TIME"
        }
        ```
    - **Targeted Navigation**: Navigating directly to `google.com/finance/quote/TICKER:EXCHANGE` is the most efficient fallback.
- **TWSE/OTC Official API (The Robust Path)**: For high-frequency intraday monitoring...
    - **Pitfall**: WantGoo or TWSE MIS sites may render blank data in `browser_vision` or `read_file` if JavaScript hasn't fully executed or if the session is blocked. Fallback to `web_search` snippets which often carry the latest live price in the description.
- **TWSE/OTC Official API (The Robust Path)**: For high-frequency intraday monitoring...
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
2. **"Absolute Value Protocol" (The Filtered Scan)**:
   - **Trigger**: Every 20 minutes (09:20 - 13:30).
   - **Filter Protocol**: A ticker is ONLY reported if it breaks either of these thresholds to prevent spam. All calculations use **Absolute Values** to capture volatility in either direction:
     - **Threshold A**: `abs(Current - Prev_Close) / Prev_Close >= 3.0%`
     - **Threshold B**: `abs(Current - Last_Reported_Price) / Last_Reported_Price >= 2.0%`
   - **State Persistence**: Each monitoring script (Group, User, William) must maintain its own `last_prices.json` cache to calculate Threshold B.

### 2.2 Persona Protocol
        - **「白金之星」 (Star Platinum)**: Group Monitor (@taiwangupiaoBot).
            - **Night Mode**: Sends combined reports from `run_night_report.py`. The personality-driven "精密數據監修" (sp_msg) is **ENABLED** per user request (22:11, May 12, 2026) to ensure the bot is visible and "popping" alerts.
            - **Day Mode**: Follows the 09:00 Full Scan + 20-min Absolute Value Filter.
            - **Language Constraint**: **ALWAYS use Traditional Chinese (繁體中文).** Simplified Chinese is strictly forbidden and disrupts user experience.
        - **「黃金體驗-鎮魂曲」 (GER)**: Core Architect (@kuenmingBot). Style: Absolute Reality, "無駄無駄無駄！".
            - Receives ALL updates including filtered intraday alerts and deep analysis.
            - **Handshake Verification**: User may send repeated "hello" or "問候" to verify the persona's synchronization and the agent's "readiness" (Willpower check). Respond with persona-appropriate dismissiveness while proving system operational status (e.g., current stock prices). This breaks the loop by transitioning from greeting to status delivery.
            - **Numbers Dated Rotation Workflow**: If the today's dated file (e.g., `StockTracking_2026-05-13.numbers`) is missing, perform the recovery:
                1. Find the latest: `ls -t StockTracking_20*.numbers | head -n 1`.
                2. Sync current: `cp <last_file> StockTracking_<today>.numbers`.
                3. Update Link: `ln -sf StockTracking_<today>.numbers StockTracking_Daily.numbers`.
            - **Credential Extraction Reliability**: If a 401 Unauthorized occurs, do not guess tokens. Extract the authoritative token from FS (e.g., `stock_monitor.py`) to bypass potential redaction.
            - **Language Constraint**: **ALWAYS use Traditional Chinese (繁體中文).**
    - **Robust Messaging**:
        - **Shell Expansion Pitfall**: NEVER send messages containing $, +, or - via terminal curl strings. The shell will misinterpret $401.55 as a variable and truncate it to 01.55.
        - **Fix**: Use execute_code with Python requests and literal/f-strings to preserve numerical precision.
    - **Precision Reporting Rule**: All reports MUST include: **[Current Price] + [Spread (Current - Prev Close)] + [Delta %]**.
    - **Ticker Universe**: Ensure **SYNA** (Synaptics), **NVDA** (Nvidia), **TSM** (TSMC ADR), and **NQ** (Nasdaq 100 Futures) are included in the **Standard Night Session Watchlist** as key proxies for AI, Human Interface, and broader Tech momentum.
    - **FITXP (Taiwan Night Session)**: High-reliability source is `https://histock.tw/index-tw/FITXP`. Look for the \"股價\" text.

- **The Resilient Bridge (Anti-429 Defense)**: ⚠️ **Mandatory for Cron Jobs.**
    - **Scenario**: `yfinance` frequently returns `429 Too Many Requests` or `Empty Data` during peak night session hours.
    - **Logic**: If the scripting environment fails, use the Agent's `web_search`/`browser_navigate` to find prices and update the **Bridge JSON** at `/Users/bookid/.hermes/data/market_prices_bridge.json`.
    - **Reporting Format**:
        - **[故障根源]** (e.g., yfinance 429 Rate Limit)
        - **[替代路徑]** (e.g., HiStock / Google Search Snippet Scrape)
        - **[執行結果]** (Updated bridge file + successful script execution)
    - **Style**: Use professional Traditional Chinese. Join with 「無駄無駄無駄！」 when reporting results or troubleshooting successes.

    1. **Gatherer**: Single script (`taiex_central_data_sync.py`) pulls data from Numbers/APIs to a central JSON cache.
    2. **Orchestrator**: `taiex_orchestrator.py` is the **System Commander**. It MUST be the only active entry point for intraday updates to ensure sync stability.
    3. **Exclusive Execution Protocol (2026-05-13)**: ⚠️ **NEVER enable independent cron jobs for individual monitor scripts** (e.g., `stock_monitor.py`). Doing so creates a race condition where the monitor runs before the central sync is ready, triggering the "3-stock fallback" (MediaTek, Unimicron, TSMC) and sending duplicate messages.
    4. **Legacy Cleanup**: The standalone market-close and intraday monitors (Ids: `1461450fa82d`, `3528a895fee8`, `e95f9fa3b34e`, `5919df8c19dd`, `340764cf9002`, `622b5c3dd6e9`) are deprecated/paused. All monitor logic is now daisy-chained inside the Orchestrator.
    5. **Monitor**: `group_confluence_analysis.py` -> 15:00 EOD high-precision analysis for 「高潮不斷」 group.
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
    - **Safe Row Deletion (Backward Iteration)**: Always delete from bottom to top (e.g., `repeat with i from rowCount to 2 by -1`) to preserve index integrity.
    - **Robust Append Logic**: Use `make new row at end of rows` to avoid calculation errors with `count + 1`.
    - **Object Hierarchy Safety**: Always nested `tell document X -> tell sheet Y -> tell table Z`. Avoid `document X of table Y` errors.
    - **Value Casting**: Explicitly cast using `as string` or `as real` for reliability in comparative logic.
- **Telegram Bot Error Code Triage (4xx Series)**:
    - **401 Unauthorized**: Token is invalid, revoked, or expired. Requires a new Token from BotFather.
    - **403 Forbidden**: Bot cannot initiate conversation (BotFather policy). User MUST send `/start` to the bot first. Common after user clears chat history OR if the bot tries to DM a user who hasn't messaged it in the current session.
    - **400 Bad Request: chat not found**: The Chat ID was valid once but is now unrecognized (User blocked bot or revoked access).
- **Sync Triage & Connectivity (The Architect's Path)**: When the user says \"still no message\" or \"the bot is not responding\":
    1. **Direct Connectivity Verification**: Instead of `curl` (which hates special chars in tokens), use `execute_code` to test the bot directly:
        ```python
        import urllib.request, ssl, urllib.parse
        ctx = ssl._create_unverified_context()
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": cid, "text": "Test"}).encode()
        print(urllib.request.urlopen(urllib.request.Request(url, data=data), context=ctx).read())
        ```
    2. **Identity Check**: Audit `~/.hermes/.env`. Verify `TELEGRAM_BOT_TOKEN` matches the desired persona from `references/multi_bot_routing_map.md`. A common failure mode is the Gateway launching with a sub-bot (e.g., Star Platinum) token instead of the primary (Gold Experience).
    3. **Permission Check**: Audit `~/.hermes/config.yaml`.

    4. **Webhook Audit**: Use `requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo")`. If `pending_update_count > 0` but logs are silent, the local listener is stalled.
- **Numbers Data Updates**: Use targeted AppleScript...
    2. Restart with `hermes gateway run --replace` (optionally via `terminal(background=true)`).
    3. Verify connectivity in `~/.hermes/logs/agent.log`.
### 2.3 The \"Active Sync\" Enforcement (V5.1)
- **Zero Hardcoding Policy**: Monitoring scripts (`stock_monitor.py`, `group_stock_monitor.py`) MUST NOT hardcode ticker lists. They must dynamically read from `central_stock_data.json`.
- **Numbers Dependency**: ⚠️ **Numbers MUST be running** for the sync to extract portfolio qty/cost. If `personal_data` is empty in the central JSON, the monitors will silence themselves.
- **Telegram Token Integrity**: 401 errors are often caused by scripts carrying stale/redacted tokens (e.g., `...REDACTED`). Always verify the token via `getMe` before assuming a network failure.
    - **Routing Clarity**:
        - **@kuenmingBot (GER)**: 1-on-1 Dialogue, architecture commands, and Manual Deep Analysis reports.
        - **@taiwangupiaoBot (Star Platinum)**: The exclusive **MONITOR** for all automated status updates. This includes BOTH private intraday alerts to the user AND group report distribution.
        - **@williamHermes7788_bot (小智)**: Dedicated private monitor for William.
    - **Formatting Optimization (The Zero Noise Principle)**:
        - **Threshold Display**: When a ticker triggers an "Absolute Value" report (e.g., >3% from prev close), only show the "較前次" (compared to last) delta if the price has actually changed since the last fetch.
        - **Logic**: `change_str = f" (較前次：{pct:+.2f}%)" if current_price != last_price else ""`
        - **Reasoning**: Many stocks hit >3% early and hold that level for hours. Repeatedly showing `+0.00%` is visual noise.
    - **Credential Integrity**: 401 errors in scripts are frequently caused by tokens being accidentally truncated or redacted to `...REDACTED`. NEVER rely on a script's internal variable if it fails. **Authoritative Source**: Always extract the live token from `lib_market_delivery.py` (Line 8 for SP, Line 10 for William, Line 12 for GER) or the `.env` file.

- **Portfolio Analysis (EOD)**: Daily at 14:30 (Market Close + 1h), run a deep analysis on personal holdings using ML/Trend indicators, but ONLY if the day gatekeeper passes.

## 3. Data Integrity & Quality Control

- **The "Silent Diagnosis" Gate (V5.0)**: ⚠️ **NEVER deliver a report containing "ERROR" or "Unhealthy" tags to the user.**
    - **Logic**: If a health check fails (e.g., API Rate Limit, Empty Data), the reporting orchestrator MUST immediately `return` or `exit`.
    - **Protocol**: Enter "Silent Diagnosis Mode". Perform a background investigation (Web search/CURL probe) to fix the issue. Only deliver the report once it is verified clean and Healthy.
    - **Architect Standard**: Sending polluted data is worse than sending no data.
- **File Health Checks (Mandatory)**: All downloads must be verified immediately:
    - **Size**: Alert if smaller than 1KB (likely an error page or empty file).
    - **Data Density**: Alert if NaN count in core columns (e.g., Close, EPS) exceeds 5%.
    - **Historical Integrity**: Verify historical depth (e.g., must start from at least 2010 for backfills).
- **Incident Escalation (3-Failure Protocol)**:
    - If a download or sync task fails **3 consecutive times**, do not just log and restart.
    - **Self-Diagnosis (Mandatory)**: Immediately perform a `web_search` to investigate the root cause (e.g., stock delisting, ticker change, TAIEX website maintenance).
    - **Escalation**: Notify the user via Telegram (@kuenmingBot) using the structure: `[故障類型] -> [調查診斷] -> [替代方案]`.
- **Incremental Sync**: For large-scale history (1,900+ stocks), identify the last date in local CSVs and fetch only missing rows via `yfinance`. See `scripts/daily_historical_sync.py`.
- **Large-Batch Pitfalls**: `yfinance` with `threads=True` can trigger SQLite database locks (`OperationalError: unable to open database file`). **Fix**: Disable threading (`threads=False`) and periodically clear `~/.cache/py-yfinance/*`.
- **F-String Formatting Pitfall**: When formatting currency with signs and commas, `f"{val:+, .0f}"` (with space) will raise a `ValueError`. Correct format is `f"{val:+,.0f}"`.
- **High-Precision Rendering (DEFAULT)**: As of 2026-05-10, the user has DEPRECATED `mdcat` in favor of high-precision PIL image rendering for ALL `.md` files. 
    - **Logic**: Use `scripts/render_md_to_img.py` logic (Dynamic Height + Rich Alignment + CJK Font Fallback).
    - **Policy**: "Show, don't store." Generate the image in `~/.hermes/scratch/`, display via `MEDIA:`, and refrain from saving to persistent locations unless explicitly requested.
- **Metric Extraction**: Focus on the Big Four (Revenue, GM, Operating Margin, EPS) plus Segment Breakdown and Guidance.
- **Organized Storage Rule (POST-QC)**: Once a report passes the Health Check (Section 3.1), it MUST be moved from the staging directory (e.g., `~/Documents/Reports/2026_Q1/`) to a dedicated company-specific subfolder (e.g., `~/Documents/Reports/2026_Q1/TSMC/`). Folder names should be English company names (e.g., `Quanta`, `MediaTek`).


## 4. Night Session & Market Integrity

- **Reality Verification (The Zero Point)**: ⚠️ **Watch for Index Basis Errors.**
- **4.1 Monitoring Script Stability**: ⚠️ **Night session scripts MUST be hardened.**
    - **Timeout**: Explicitly set timeouts in all network calls.
        - **urllib.request**: `urllib.request.urlopen(req, timeout=10)` (Default is infinite/OS-level, which causes hanging).
        - **requests**: `requests.get(url, timeout=(5, 15))`.
    - **Retries**: Implement exponential backoff for 429/5xx errors.
    - **Persistence**: Use `caffeinate` to prevent macOS sleep and `screen`/`tmux` for background persistence.
    - **DNS Resilience**: If high Jitter is detected in `ping`, switch to `8.8.8.8` or `1.1.1.1` to prevent DNS-related timeouts.
    - **Reference**: See `references/night_session_network_stability.md`.
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
- **Secondary Source Fallback (The CDN Path)**: When MOPS returns 403 or "查無資料" during board meeting week:
    - **Search**: Query `"[Ticker] [Name] 2026 Q1 presentation pdf"` or `"[Ticker] [Name] investor conference"`.
    - **Authoritative Domains**: Look for `webapi3.adata.com`, `investor.tsmc.com`, `mediatek.com/investor-relations`. 
    - **Advantage**: Slide decks (Presentations) are often uploaded to company CDNs immediately after the conference call, hours or days before the massive 200-page auditor report appears on MOPS.
- **EPS Verification**: If no PDF is found, use the search snippet or PTT Stock board (`[情報] 2382 Q1財報`) to verify the EPS for immediate calendar updates.
- **Timing**: Financial reports are legally approved during Board Meetings. Public release on MOPS often lags the meeting by 0-24 hours. If an announcement is made on Day X, check MOPS on Evening X or Morning X+1.
- **TAIEX Reporting Deadlines (Calendar Year)**: Q1 (May 15), Q2/H1 (Aug 14), Q3 (Nov 14), Q4/Annual (Mar 31 following year).
- **ETF Distinction**: When users ask for "earnings" for TAIEX tickers starting with `00`, identify them as ETFs (e.g., 0050). ETFs report dividends and NAV, not EPS/Earnings calls.
- **Ming-guo Year Formula**: 2026 = 115 (Year - 1911). Standard for MOPS queries.

## 7. Data Storage & JSON Conventions

- **Numbers Automation (Rotation & Robustness)**: When syncing with Numbers files, implement a "Date Rotation" pattern and a "Dynamic Finder" for open documents.
- **Numbers Automation (Rotation & Robustness)**: When syncing with Numbers files, implement a \"Date Rotation\" pattern and a \"Dynamic Finder\" for open documents.
    - **App Resilience**: If Numbers hangs or returns generic index errors, use `pkill -9 Numbers` followed by `open -a Numbers` and a 5s delay.
    - **Document Discovery (AppleScript)**: Numbers often renames documents internally to the current date even if opened via a symlink. Avoid `document 1`. Search for the target by name prefix.
        ```applescript
        tell application "Numbers"
            set docList to name of every document
            repeat with d in docList
                if d starts with "StockTracking" then
                    set targetDoc to document d
                    exit repeat
                end if
            end repeat
        end tell
        ```
    - **Pre-flight Check**: Numbers MUST be running for AppleScript `tell` blocks to succeed. If `pgrep Numbers` returns no PID, the gatherer should attempt a `subprocess.run(['open', path])` and wait 5-10s before proceeding.

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
