# Reality Verification Routine: Night Session

When verifying night session prices (2026+ Era), use the following check-list to prevent "Zero-Point Drift" (22k vs 42k errors):

1. **Verify TAIEX Era**: Ensure you are not pulling data from a source that defaults to 2024/2025 constants. 2026 baseline is ~42,000+. 
   - **Critical Failure Example**: Reporting 22,6xx when the market reality is 42,2xx. This indicates a 20,000-point "Reality Gap" that must be immediately bridged via `web_search`.
2. **Source Tie-Breakers**:
   - Primary: `mis.twse.com.tw` (Official API)
   - Secondary: `invest.cnyes.com` (Night Futures specific)
   - Tertiary: `wantgoo.com` (Best-of-5 bids/asks)
3. **Identifier Check**: Use `WTXP&` (Wantgoo) or `TXF` (CNYES) for the Night session specifically. Do NOT use `^TWII` which only reflects regular session close.
4. **Failure Logic**: If data is missing or obviously wrong, report `[REALITY ERROR] -> [Recalibrating...]` and use a secondary source immediately. Do NOT apologize; just return it to zero.
