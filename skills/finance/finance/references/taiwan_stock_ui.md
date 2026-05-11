# Taiwan Stock UI & Convention Standards

Standard formatting and behavior for Taiwan-focused financial agents.

## 1. Visual Cues
- **Rising (漲)**: 🔴 (Red) and ▲.
- **Falling (跌)**: 🟢 (Green) and ▼.
- **Neutral (平)**: ⚪ and •.
- **Header Pattern**: Always include the user-specific "歐拉" (Ora) prefix (e.g., `歐拉歐拉歐拉歐拉歐拉`) for personal portfolio reports.
- **Profit/Loss Emojis**: 💰 for profit, 💸 for loss.
- **Top/Bottom Ranking**: Sort by daily % change. Highlight Top 3 and Bottom 3 in summaries.

## 2. Quantitative Basics
- **Lot Size**: Always **1,000 shares per Lot (張)**.
- **Investment (投入)**: `(Purchase Price * Lots * 1000) + Transaction Fees`.
- **Market Value (市值)**: `Current Price * Lots * 1000`.
- **Profit/Loss (損益)**: `Market Value - Investment`.
- **Break-even Price (損益兩平價)**: Includes buy fee + estimated sell fee + transaction tax (usually ~0.45% combined total overhead).

## 3. Compact Layout 2.0 (System Architect Style)

High-density formatting for frequent (10-20 min) monitoring updates to reduce vertical scrolling.

### A. Number Formatting
- **Price >= 1,000**: Round to integer with thousands-comma. Example: `2,245`.
- **Price < 1,000**: 2 decimal places. Example: `94.35`.
- **Percentage/Change**: Always include `+`/`-` sign and 2 decimal places.

### B. Inline Trend Metrics (10M)
- Trend metrics (e.g., 10 Minutes ago) belong on the **same line** as the price.
- Format: `▸ **Price** (Total %) | 10M: [Color Emoji][Arrow][Percentage]`
- Use the **current price trend color** for the 10M emoji to maintain visual consistency.

### C. Example Output
🟢 **台積電** (`2330.TW`)
   ▸ **2,245** (-0.22%) | 10M: 🟢▼-0.44%
🔴 **欣興** (`3037.TW`)
   ▸ **914.00** (+1.67%) | 10M: 🔴▲+1.90%

## 4. Reporting Header
...

## 4. Time Management
- **Market Hours**: 09:00 - 13:30 (Taipei Time, UTC+8).
- **Closing Update**: Usually sent at 13:30 to capture the final settlement price.
- **Deduplication**: Use file-locking to prevent double-sending messages within a 120s window.
