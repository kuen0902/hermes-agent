# Taiwan Earnings Report Workflow

## Data Schemas
### `~/.hermes/data/earnings_calendar.json`
```json
{
    "2330.TW": {
        "name": "台積電 TSMC",
        "next_report_date": "2026-04-16",
        "last_downloaded_quarter": "2026 Q1",
        "downloaded": true,
        "downloaded_q1": true,
        "files": ["2330_TSMC_Q1_2026.pdf"]
    }
}
```

## Logic Patterns
- **Filter Date**: Use `next_report_date <= today` and check the `downloaded_q1` flag.
- **Quanta (2382.TW) Edge Case**: Dates in automated calendars often point to the *estimated* date or the *Board Meeting* date. The actual financial report PDF might only appear on MOPS *after* the board meeting resolution (14:00+ on the announcement day).
- **Silent Mode**: If no stocks meet the criteria (announced <= yesterday AND not downloaded), return `[SILENT]` to avoid empty cron notifications.

## Tools & Commands
- **Path Resolution**: Always use absolute paths via `os.path.expanduser('~/.hermes/data/...')`.
- **Health Check**:
    - Minimum size: >100KB for consolidated reports.
    - Content Probe: `strings [file.pdf] | head -n 5` should show `%PDF-`.
    - Failures: 13-15KB files are likely HTML "Access Denied" or "Robot Verification" pages from MOPS.

## MOPS Retrieval
Fetch via MOPS Search: `https://mops.twse.com.tw/mops/web/t57sb01_q1` (Manual check if automation fails).
