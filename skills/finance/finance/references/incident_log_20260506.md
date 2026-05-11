# Multi-tenant Troubleshooting Log (2026-05-06)

## Incident: William Stock Monitor Failure
- **Error**: `Telegram Error: HTTP Error 401: Unauthorized`
- **Context**: Orchestrator triggering multiple monitors. Personal and Group bots worked fine; William bot failed.
- **Root Cause**: Invalid/Expired `WILLIAM_BOT_TOKEN`.
- **Diagnosis Steps**:
    1. Check `last_sync` in `central_stock_data.json` to confirm fetcher worked.
    2. Review `result.stderr` from the orchestrator subprocess.
    3. Verify network status (Python `urllib` usually works with `ssl._create_unverified_context()` on this system).
    4. Isolate the bot token and test via `curl "https://api.telegram.org/bot<TOKEN>/getMe"`.
- **Outcome**: Token confirmed invalid. User needs to regenerate key from @BotFather.

---

## Technical Note: Suffix Hunting Resilience
During the sync phase, tickers `4966`, `3260`, `7815` etc. initially failed with `.TW`. 
The `taiex_central_data_sync.py` logic successfully caught these and re-tried with `.TWO`, maintaining a "Healthy" system status even with high-variance TAIEX/OTC listings.
