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
- **Night Session Rules**: `references/night_session_rules.md` (Script hardening, 05:00 Archive settlement, Gatekeeper logic).
- **Historical Reference**: `references/deep_analysis_template.md` (Obsidian report structure).
- **Multi-Bot Routing**: `references/multi_bot_routing_map.md` (Bot Tokens, Chat IDs).

## 1. Market Data Retrieval (Yahoo Finance & TWSE API)

- **The Market Open Gatekeeper (TAIEX)**: ⚠️ Mandatory for cron jobs. If `2330.TW` last index date != today (Taipei time), exit immediately.
- **The Hybrid Fallback Pattern**: Use TWSE API as primary. If a ticker returns `None`, trigger `yfinance` fallback.
- **The Resilient Bridge (Anti-429 Defense)**: When Yahoo Finance returns 429/Empty, navigate to Google Finance/HiStock, and cache results in `/Users/bookid/.hermes/data/market_prices_bridge.json`.

## 2. Portfolio Monitoring & Distribution

- **09:00 Opening Report (The Full Scan)**: Full table of all monitored lists.
- **"Absolute Value Protocol" (The Filtered Scan)**: (09:20 - 13:30). A ticker is ONLY reported if `abs(Delta)` >= 3.0% from Prev Close, OR `abs(Delta)` >= 2.0% from Last Reported Price.
- **Persona Protocol**:
  - **@taiwangupiaoBot (Star Platinum)**: Group Monitor. Night Mode & Day Mode. MUST use Traditional Chinese.
  - **@kuenmingBot (GER)**: Core Architect. 1-on-1 Dialogue. "無駄無駄無駄！" style.
- **Precision Reporting Rule**: All reports MUST include: **[Current Price] + [Spread (Current - Prev Close)] + [Delta %]**.

## 3. Data Integrity & Quality Control

- **The "Silent Diagnosis" Gate**: NEVER deliver a report containing "ERROR". If a health check fails, perform background investigation, fix, and then deliver.
- **File Health Checks (Mandatory)**: Size > 1KB, NaN count < 5%.
- **Incident Escalation**: 3 consecutive failures = Escalate to @kuenmingBot via Telegram (`[故障類型] -> [調查診斷] -> [替代方案]`).
- **High-Precision Rendering**: Use `scripts/render_md_to_img.py` to render Markdown to images dynamically. Do not use `mdcat` for tables. Show via `MEDIA:`, do not permanently store unless instructed.

## 4. Analytical Deliverables (Obsidian Reports)

- When analyzing a PDF financial report, focus on Revenue, GM, OP, Non-Op, Net Profit, and EPS.
- **Chronology**: Use Calendar Quarters ONLY (e.g., 2026 Q1) regardless of Fiscal Year differences.
- **Output Path**: `~/Documents/Obsidian Vault/Finance/DeepAnalysis/[YEAR]Q[Quarter]/[Ticker]_[English_Name].md`.

## 5. Historical Data & AI Predictors

- **Incremental Sync**: Daily at 05:00, update all local CSVs with the latest 10 days of data using `scripts/daily_historical_sync.py`.
- **ML Signal Engine**: Focuses on Trend (SMA/EMA), Momentum (RSI/MACD), Volatility (ATR), and Volume Ratio. Targets 5-day forward return binary classification.
