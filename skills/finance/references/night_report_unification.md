# Night Report Unification (Consistency Protocol)

## Problem: Contradictory Status Reports
In the TAIEX Night Session monitor, two scripts run sequentially and their outputs are concatenated:
1. `tw_night_monitor_adri.py` (ADRs)
2. `tw_night_session_hourly.py` (NQ Futures)

If (1) failed but (2) succeeded, the message ended with:
> 🛡️ 健康檢查：Degraded (EWT 數據獲取失敗)
> ...
> ✅ 狀態：Healthy

This confuses the user and indicates a lack of coordination in the automation stack.

## Solution: Centralized Status Management
1. **Strip Internal Status**: Individual monitoring scripts should only report errors/degradation in a standard format (e.g., "🛡️ 健康檢查：Degraded...") or remain silent on success. They must NOT print a final "Healthy" status locally.
2. **Orchestrator Responsibility**: The top-level script (`run_night_report.py`) is responsible for the "Executive Summary" status.
3. **Logic Flow**:
   - Run sub-scripts and capture output.
   - Scan combined output for the keyword "健康檢查" or "Degraded".
   - If found, maintain that specific error message.
   - If NO error keywords are found AND at least one script returned content, append `✅ 狀態：Healthy` at the very end of the message.

## Implementation (2026-05-14)
- Patched `tw_night_monitor_adri.py` to only append status line IF `health != "Healthy"`.
- Patched `tw_night_session_hourly.py` to remove the hardcoded success line.
- Updated `run_night_report.py` to perform the final check.
