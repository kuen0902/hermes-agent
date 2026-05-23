# Incident Log: 2026-05-13

## 1. Race Condition Analysis (09:00 Fallback)
**Symptom**: User received a 09:00 report containing only 3 stocks (2454, 3037, 2330) instead of the full 22-stock portfolio.
**Root Cause**: 
- Independent cron jobs for `stock_monitor.py` were enabled alongside the `taiex_orchestrator.py`.
- The independent monitor triggered at exactly 09:00:00, before the Orchestrator's `central_data_sync.py` had finished populating the cache.
- The monitor script found an empty/incomplete cache and fell back to its internal "Hardcoded Legacy List".
**Resolution**:
- Paused independent cron jobs `5919df8c19dd`, `340764cf9002`, and `622b5c3dd6e9`.
- Enforcement: ALL monitor triggers must go through the Orchestrator to ensure the Sync-before-Distribute sequence is preserved.

## 2. Telegram 401 Unauthorized (Group Bot)
**Symptom**: 10:40 update sent to personal channel but failed for 「高潮不斷」 group.
**Investigation**:
- `group_stock_monitor.py` returned `HTTP Error 401: Unauthorized`.
- Inspection revealed the `GROUP_BOT_TOKEN` variable was truncated to ~14 characters (likely a manual edit error or redaction artifact).
**Resolution**:
- Extracted the authoritative token from `stock_monitor.py` (which was working).
- Substituted the correct token into `group_stock_monitor.py`.
**Lesson**: When a 401 occurs in one script but not another, treat the working script as the source of truth and sync credentials immediately.
