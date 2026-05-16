---
name: finance
description: Financial data automation — market queries, portfolio monitoring, earnings analysis, and TAIEX-specific workflows.
version: 1.2.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [finance, stocks, taiex, investigation, earnings, portfolio, telegram]
---

# Finance & Investment Automation

This skill governs automated financial tracking, market data retrieval, and corporate reporting analysis. To prevent context bloat, detailed SOPs have been extracted into the `references/` directory.

## 📚 References Directory (READ THESE FIRST)
- **Telegram Bot Triage**: `references/telegram_bot_triage.md` (401/403 errors, sync triage, shell formatting rules).
- **Numbers Automation**: `references/numbers_applescript.md` (Dynamic document discovery, row iteration, AppleScript safe operations).
- **MOPS & Earnings Guidelines**: `references/mops_guidelines.md` (Taiwan MOPS scraping rules, Bot detection traps, CDN fallbacks, Calendar dates).
- **The TAIEX Gatekeeper**: `references/taiex_gatekeeper_implementation.md` (Robust logic for market status checking).
- **Night Session Rules**: `references/night_session_rules.md` (Script hardening, 05:00 Archive settlement, Gatekeeper logic).
- **Script Hardening & Compatibility**: `references/script_hardening_automation.md` (Absolute paths, Python 3.11 vs 3.12 syntax, Cron PATH issues).
- **Historical Reference**: `references/deep_analysis_template.md` (Obsidian report structure).
- **Multi-Bot Routing**: `references/multi_bot_routing_map.md` (Bot Tokens, Chat IDs).

## 1. Market Data Retrieval (Yahoo Finance & TWSE API)

- **The Market Open Gatekeeper (TAIEX)**: ⚠️ Mandatory for cron jobs. Do not rely solely on simple chart dates.
  - **TSMC Quote Method (Preferred)**: Check `2330.TW` via `quoteResponse`. 
  - **Logic**: Proceed if `marketState` is `REGULAR`, `POST`, or `PRE`, or if `regularMarketTime` matches the local date.
  - **Fallback**: Default to "OPEN" during Mon-Fri (08:30-15:30) if the API is unreachable to prevent automation stalls.
- **The Hybrid Fallback Pattern**: Use TWSE API as primary. If a ticker returns `None`, trigger `yfinance` fallback.
- **The Resilient Bridge (Anti-429 Defense)**: When Yahoo Finance returns 429/Empty, navigate to Google Finance/HiStock, and cache results in `/Users/bookid/.hermes/data/market_prices_bridge.json`.

## 2. Portfolio Monitoring & Distribution

- **09:00 Opening Report (The Full Scan)**: Full table of all monitored lists.
- **Tiered Milestone Protocol (The Milestone Scan)**: (09:20 - 13:30). A ticker is reported when it crosses absolute thresholds: **[3.0%, 5.0%, 7.0%, 9.0%]**. Reports trigger on the *first* crossing of a tier.
- **Privacy Enforcement (Group Separation)**: The `group` profile MUST be patched to exclude `personal_data` (private holdings) from reports to prevent privacy leaks in public/shared Telegram channels. Only "Watchlist" or "Category" stocks are broadcasted to groups.
- **Persona Protocol**:
  - **@taiwangupiaoBot (Star Platinum)**: Group Monitor. Night Mode & Day Mode. MUST use Traditional Chinese. ORA ORA ORA style.
  - **@kuenmingBot (GER)**: Core Architect. 1-on-1 Dialogue. "無駄無駄無駄！" style.
- **Precision Reporting Rule**: All reports MUST include: **[Current Price] + [Spread (Current - Prev Close)] + [Delta %] + [Tier Triggered]**.

### Active Portfolio Management (The `/stock` command)
- **Menu Protocol**: When the user types `/stock`, reply with a menu: `1️⃣ 查詢`, `2️⃣ 更新持股`, `3️⃣ 觀測股管理`.
- **CRITICAL Rules**:
  - **No Guessing**: Never assume Code, Price, or QTY. Ask for clarification if missing.
  - **Environment**: Use `/Users/bookid/workspace/hermes-agent/venv_314/bin/python` for `portfolio_tool.py` calls.
- **Commands**:
  - **Check**: `python3 ~/.hermes/scripts/portfolio_tool.py --action check`
  - **Buy/Sell**: `python3 ~/.hermes/scripts/portfolio_tool.py --action buy/sell --code <Code> --qty <Qty> --price <Price>`
  - **Watchlist**: `python3 ~/.hermes/scripts/portfolio_tool.py --action watch_add/watch_rm --code <Code>`

## 3. Data Integrity & Quality Control

- **The "Silent Diagnosis" Gate**: NEVER deliver a report containing "ERROR". If a health check fails, perform background investigation, fix, and then deliver.
- **Unified Health Protocol (Reporting Consistency)**: When merging multiple sub-script outputs (e.g., Night Report), do NOT allow sub-scripts to print their own "Healthy" status. The orchestrator MUST perform a final verification. If any sub-script is "Degraded", the entire report is "Degraded". Only a clean pass on all components results in a final "✅ 狀態：Healthy" tag at the very bottom. (Ref: `references/night_report_unification.md`)
- **File Health Checks (Mandatory)**: Size > 1KB, NaN count < 5%.
- **Incident Escalation**: 3 consecutive failures = Escalate to @kuenmingBot via Telegram (`[故障類型] -> [調查診斷] -> [替代方案]`).
- **High-Precision Rendering**: Use `scripts/render_md_to_img.py` to render Markdown to images dynamically. Do not use `mdcat` for tables. Show via `MEDIA:`, do not permanently store unless instructed.

## 4. Analytical Deliverables (Obsidian Reports)

- When analyzing a PDF financial report, focus on Revenue, GM, OP, Non-Op, Net Profit, and EPS.
- **Chronology**: Use Calendar Quarters ONLY (e.g., 2026 Q1) regardless of Fiscal Year differences.
- **Output Path**: `~/Documents/Obsidian Vault/Finance/DeepAnalysis/[YEAR]Q[Quarter]/[Ticker]_[English_Name].md`.

## 5. Historical Data & AI Predictors

- **Incremental Sync**: Daily at 05:00. **Strict Environment**: Use the absolute venv python path (`/Users/bookid/workspace/hermes-agent/venv_314/bin/python`) to ensure `pandas` and other ML deps (Python 3.14) are available. (Ref: `references/script_hardening_automation.md`)
- **Fast-Sync Pattern (EOD Analyzer)**: For time-sensitive analysis (e.g., 14:30 Portfolio Analysis), use the `--fast` flag with `daily_historical_sync.py`. This skips the full market scan (1,900+ tickers) and updates ONLY the core symbols in the monitoring watchlist, preventing timeouts.
- **ML Signal Engine**: Focuses on Trend (SMA/EMA), Momentum (RSI/MACD), Volatility (ATR), and Volume Ratio. Targets 5-day forward return binary classification.
