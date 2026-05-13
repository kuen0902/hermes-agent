# Night Session & Market Integrity

## Script Stability (Hardening)
Night session scripts MUST be hardened to survive network unreliability.
- **Timeout**: Explicitly set timeouts in all network calls.
  - **urllib.request**: `urllib.request.urlopen(req, timeout=10)` (Default is infinite/OS-level, which causes hanging).
  - **requests**: `requests.get(url, timeout=(5, 15))`.
- **Retries**: Implement exponential backoff for 429/5xx errors.
- **Persistence**: Use `caffeinate` to prevent macOS sleep and `screen`/`tmux` for background persistence.
- **DNS Resilience**: If high Jitter is detected in `ping`, switch to `8.8.8.8` or `1.1.1.1` to prevent DNS-related timeouts.

## Night Session Gatekeeper (Schedule-Based)
⚠️ **Do NOT rely on Yahoo Market Status for Gatekeeping.**
- **Active Session Logic**:
  - **Mon-Fri**: 15:00 - 23:59 (Today's Trade)
  - **Tue-Sat**: 00:00 - 05:00 (Yesterday's Trade)
- **Logic Implementation**: Check local time vs. weekday schedule (Mon=0, Sat=5). Mon 15:00 to Sat 05:00 is the full operational window for Night Reporting.
- **Weekend Silence**: Saturday 06:00 to Monday 15:00 (Taipei Time). Avoid sending stale Friday data on weekends.

## Night Session Settlement (05:00 Archive)
Every trading day at **05:00 Taipei Time**, the system performs a final settlement of the Night Session data.
- **Workflow**:
  1. **Final Summary**: Execute `tw_night_monitor_adri.py` and `tw_night_session_hourly.py` one last time to capture the session close.
  2. **Archival**: Copy all 10-minute intraday batch logs from `~/Documents/Reports/Analysis_Logs/Daily_Intraday_Batches` to a dated archive in `~/Documents/Reports/NightSession/[YYYY-MM-DD]/`.
  3. **Obsidian Sync**: Push a settlement summary report (`Settlement_Report.md`) to the Obsidian vault at `~/Documents/Obsidian Vault/Finance/DailyReports/` for asynchronous review.
