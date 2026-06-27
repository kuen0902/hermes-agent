# Case Study: 6806 (Senwei Energy) Liquidity Failure Audit

## Incident Summary
In June 2026, the ML system (XGBoost Regressor) generated a 98.65% 20D predicted return for 6806.TW. The stock was actually in a delisting spiral due to negative net value.

## The "Oversold" Mirage
The model saw 6806 as high-reward because:
1. It relied on Technical RSI and SMA which showed extreme oversold status.
2. It lacked "capital flow synergy" verification—it didn't care IF people were buying, just that the price was low relative to the model's past training.

## The Liquidity Reality (5-Week Retrospective)
| Week | Flow Reality | Result |
|---|---|---|
| Week 1 | Flow Alignment | Tiny buy volume, no support. |
| Week 2 | HEAVY DISTRIBUTION | Large volume on the down-side. Institutional Exit. |
| Week 3 | HEAVY DISTRIBUTION | Continued dumping. |
| Week 4 | FLOW DIVERGENCE | Volume dying, bid-ask spread widening. |
| Week 5 | FLOW DIVERGENCE | Dead asset. |

## The Lesson (The "Flow Confidence" Filter)
To prevent "Mathematical Phantoms" like this:
1. **Never delete the stock manualy**. Instead, update the **Bias Matrix**.
2. Calculate the **Flow Confidence Factor**: `(Institutional Net Buy / Total Volume)`.
3. If Flow Confidence is 0 (Net Institutional Selling), the realized target is capped at the current price ($9.27 in the 6806 case).

This case proved that **Liquidity must confirm the Model**. If they diverge, the Model is always wrong.
