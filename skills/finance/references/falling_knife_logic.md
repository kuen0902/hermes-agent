# Falling Knife Detection Logic

To avoid "Value Traps" and "Delisting Spirals", the ML engine must calculate and weight the following features:

## 1. Price Momentum Acceleration
- **Formula**: `Ret_Accelerate_5 = (Close[t]/Close[t-1]-1) - (Close[t-5]/Close[t-6]-1)`
- **Interpretation**: If a stock is dropping and the rate of drop is increasing (negative acceleration), it is a structural crash, not a pullback.

## 2. Panic Selling Signal
- **Detection**: `Return < -3%` AND `Volume > 1.5x Average SMA(20)`.
- **Classification**: High-volume selling at low prices indicates institutional distribution (exit). ML should penalize this regardless of "oversold" RSI levels.

## 3. Structural Low Distance
- **Threshold**: `(Current Close / 240-day Low) - 1.0 < 0.03`
- **Penalty**: If a stock is within 3% of its yearly low, it assumes "Zombie State" or "Bankruptcy Risk", applying a heavy bias penalty to the 20D predicted return.

## 4. Capital Flow Synergy (Liquidity Audit)
- **Concept**: A predicted price increase must be supported by actual capital inflow.
- **Verification**: `Synergy = (Net Institutional Buy * 1000) / Total Volume`. 
- **Action**: Check weekly capital flow from W1 to W5. If the model predicts growth but the Capital Flow is negative, it is a **Liquidity Divergence**. Scale the target price back to the current price (Confidence Factor = 0).
