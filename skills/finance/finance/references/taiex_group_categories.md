# TAIEX Group Categorization (「高潮不斷」)

As of May 2026, the 「高潮不斷」 Telegram group uses the following person-based categorizations for monitoring reports. When updating monitoring scripts or generating reports, preserve these group names and members.

| Category Name | Member Tickers / Companies |
| :--- | :--- |
| **Kim哥推薦組** | 1513 (中興電), 2049 (上銀), 5347 (世界), 6147 (頎邦), 3709 (鑫聯大) |
| **正體鍾文字組** | 2408 (南亞科), 2382 (廣達), 2327 (國巨), 2409 (友達) |
| **順風老師組** | 2313 (華通), 6285 (啟碁), 5289 (宜鼎), 2303 (聯電) |

## 🛠 Operation: Multi-Bubble Isolation
When generating AI Intraday Risk Alerts (via `intraday_risk_monitor.py`), the system must strictly separate reports into different Telegram message bubbles:
1. **[Core]**: Personal holdings from `portfolio.db`.
2. **[William]**: Monitoring codes from `william_codes`.
3. **[Other]**: Master registry codes not in the above.

Mixing categories in one bubble is a **System architecture failure** and must be corrected immediately.

## Related Scripts

## Related Scripts
- `scripts/group_confluence_analysis.py` (Primary reporter)
- `scripts/taiex_central_data_sync.py` (Data source)
