# Vision-to-Sync: Portfolio Update Workflow

This document defines the standard procedure for interpreting Taiwan trading app screenshots and updating the `StockTracking_Daily.numbers` portfolio.

## 1. UI Interpretation (Taiwan Apps)
- **當日成交 (Today's Trades)**: Shows executed orders for the current session.
- **交易別 (Transaction Type)**:
    - **現買(普)**: Spot Buy (Regular). This adds to the portfolio.
    - **現賣(普)**: Spot Sell (Regular). This removes from or reduces the portfolio.
- **成交均價 (Average Price)**: The weighted average price of the execution.
- **成交股數 (Volume)**:
    - 1,000 shares = 1 "張" (Lot).
    - 1-999 shares = Odd lot (零股).

## 2. Extraction Protocol
When the user sends a screenshot of a trade:
1. **Identify Ticker**: Look for the 4-digit code (e.g., `2330`, `2454`).
2. **Identify Action**: Determine if it's a Buy or Sell.
3. **Check Qty**: If "1張", qty is 1.0 (or 1000 depending on spreadsheet convention). The user's `StockTracking_Daily.numbers` uses `1.0` for 1 lot.
4. **Fetch Cost**: Extract the "成交均價".

## 3. Spreadsheet Operations
- **For Sells (Profit Taking)**:
    - Cross-reference the current portfolio in Numbers.
    - Use **Backward Iteration** in AppleScript to delete the row matching the ticker.
    - Calculate finalized P/L: `(Sell Price - Buy Cost) * Qty * 1000`.
- **For Buys**:
    - Use the **Robust Append Logic** (`make new row at end of rows`).
    - Col 1: Ticker, Col 2: Name, Col 3: Qty, Col 4: Cost.

## 4. Verification & Sync
After updating the spreadsheet:
1. **Force Sync**: Manually run `python3 taiex_central_data_sync.py` to update the central JSON cache.
2. **Persona Report**: Report results using the GER persona. Include the [Price] + [Spread] + [Delta %] and total P/L.
3. **Verify Star Platinum**: Ensure the next automated sync will pick up the new holding.
