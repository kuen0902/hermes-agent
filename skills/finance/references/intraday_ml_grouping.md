# Intraday ML Analysis & Risk Monitoring Grouping

To reduce noise and ensure privacy, the `intraday_risk_monitor.py` script follows a **Multi-Profile Distribution Pattern**.

## 1. Logic: Category-to-Profile Mapping
Alerts are partitioned based on their presence in the `personal_data`, `group_codes`, and `william_codes` arrays found in `central_stock_data.json`.

| Category | Profile | Target Destination | Title Header |
| :--- | :--- | :--- | :--- |
| **Core** | `personal` | Private Chat (GER) | 💎 **核心持股 AI 風險監控** |
| **Group** | `group` | Public/Shared Group (Star Platinum) | 👩‍👩‍👧‍👦 **群組關注檔 AI 風險監控** |
| **William** | `william` | Dedicated Bot/Thread | 👨‍💻 **William 監控清單警報** |

## 2. Implementation: The `intraday_risk_monitor.py` Pattern
The script loads the `PROFILES` dictionary and `grouped_alerts` containers:
```python
PROFILES = {
    "personal": {"token": "...", "chat_id": "...", "title": "個人核心"},
    "group": {"token": "...", "chat_id": "...", "title": "高潮不斷群組"},
    "william": {"token": "...", "chat_id": "...", "title": "小智/William"}
}

# Distribute alerts to each profile's container
if code in personal_codes:
    profile_alerts["personal"].append(alert_msg)
if code in group_codes:
    profile_alerts["group"].append(alert_msg)
# ...
```

## 3. Pitfalls: Shared Destination
- **Token Overlap**: Ensure `Star Platinum`'s token is used for both `personal` and `group` if that's the intended persona, but with different `chat_id`.
- **Duplicate Prevention**: The `alert_log` (`ml_alerted_today.json`) is shared across profiles. Once a code is alerted in *any* profile, it is suppressed for the rest of the day to prevent across-profile spam.
