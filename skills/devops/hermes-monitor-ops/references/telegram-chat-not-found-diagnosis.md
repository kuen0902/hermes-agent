# Telegram Communication Failure Diagnosis (2026-05-19)

## Symptom
User reports "No AI alerts received" for both core holdings and group stocks.

## Investigation Path
1. **Gateway Logs**: Found `telegram.error.BadRequest: Chat not found` for the group ID (`-1003744330314`) and `622b5c3dd6e9` cronjob.
2. **Bot Token Test**: Attempted to verify token `8737129549...`. Received `HTTP Error 404: Not Found` from `getMe`.
3. **Misleading Conclusion**: Assumed Star Platinum was dead and switched everything to GER (@kuenmingBot).
4. **Correction**: User provided a screenshot showing Star Platinum was ACTIVE and sending messages (2408.TW, 2313.TW) in the group at the time I claimed it was dead.

## Lessons Learned
- **Diagnosis Pitfall**: The `404` was a result of an incorrect test script (likely a string extraction error or malformed URL) rather than actual token revocation.
- **Chat Not Found Interpretation**: In a multi-bot setup, `Chat not found` usually means the specific bot being used by the script (or Gateway) is not a member of that chat. 
- **User Preference**: The user prefers all stock-related updates to come from **Star Platinum**, even for personal holdings. GER should remain the "control center" but not the "delivery person".

## Fix Procedure
- Ensure `intraday_risk_monitor.py` PROFILES use the `STAR_PLATINUM_TOKEN`.
- Ensure `hermes_monitor.swift` config uses the correct Star Platinum token for ALL profiles.
- **CRITICAL**: Recompile swift binaries after any source code change.
