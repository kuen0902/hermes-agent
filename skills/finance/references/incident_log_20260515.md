# Incident Log: 2026-05-15 (Environment Upgrade & Swift Integration Recovery)

## 1. Description
Systematic failure of multiple finance-related Cron jobs and the TAIEX Master Orchestrator. The issue occurred in two phases: initially following a Python upgrade, and subsequently due to interpreter misidentification.

## 2. Root Cause Analysis (Phase 1: Environment Sync)
- **Problem**: Jobs were running in the system `python3` (3.11.2) which lacked `pandas` and other financial libraries.
- **Problem**: Several monitoring scripts used Python 3.12+ `type` syntax while the execution environment was 3.11.2.
- **Fix**: Created `/Users/bookid/workspace/hermes-agent/venv_314` (Python 3.14.4) and patched all `.sh` wrappers with absolute paths.

## 3. Root Cause Analysis (Phase 2: Swift/Python Identity Crisis)
- **Problem**: The **TAIEX Master Orchestrator** (Job `f95f14b437ee`) failed at 09:00 with `SyntaxError: invalid decimal literal`.
- **Diagnosis**: The Hermes cron executor (under the new 3.14 env) misidentified the `.swift` script as a Python script and attempted to run it with the Python interpreter. The Swift-specific `$0` syntax caused the error.
- **Inter-Script failure**: `hermes_orchestrator.swift` was using `python3` to spawn child scripts. In the cron environment, this pointed to the system Python 3.11 instead of `venv_314`, causing `ModuleNotFoundError`.

## 4. Corrective Actions (The "Gold Experience" Restoration)
- **Swift Wrapping**: Created `run_taiex_orchestrator.sh` to explicitly call `/usr/bin/swift`.
- **Absolute Runtime Path**: Updated `hermes_orchestrator.swift` to use the absolute venv path (`/Users/bookid/workspace/hermes-agent/venv_314/bin/python`) when spawning tasks.
- **Gatekeeper Hardening**: Replaced `day_market_gatekeeper.py` logic with a more robust TSMC-based quote check (`marketState`) to prevent false-negative "CLOSED" results during the volatile 08:30-09:00 window.

## 5. Verification
- `run_taiex_orchestrator.sh` executed successfully at 09:13.
- `central_stock_data.json` confirmed updated with 40 core stocks.
- Telegram reports for Personal/William/Group confirmed dispatched.
- **Status: Healthy.**
