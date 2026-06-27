# Top 30 Potential Engine: Proposer-Auditor Architecture

The "Top 30" Individual Model system differentiates itself from standard ML screening by employing a two-stage filter.

## 1. Components
- **Data Source**: `~/.hermes/data/potential_analysis.ddb` (DuckDB).
- **Inference Script**: `~/.hermes/scripts/ml/find_top_30_potentials.py`.
- **Feature Engineering**: `~/.hermes/scripts/ml/features_utils.py` (calculates 36 features including RSI, Moving Averages, and institutional flow).

## 2. Logic Flow
1. **Sync**: `daily_historical_sync.py` updates the DuckDB with latest EOD data.
2. **Feature Calc**: Scripts compute the terminal state features for each ticker.
3. **Double-Blind Inference**:
   - The **Proposer** (XGBRegressor) outputs a continuous value (Predict 20D Return).
   - The **Auditor** (XGBClassifier) outputs a probability 0.0-1.0 (Stop-Loss Risk).
4. **Ranking**:
   - Candidates are ranked by Predicted Return DESC.
   - Any candidate with Auditor Risk > 50% is instantly discarded (The Veto).
   - The top 30 remaining candidates are written to `top_30_potentials_individual.json`.

## 3. Reporting
The report is delivered via a specialized Telegram message with:
- **基準日期**: The date of the last data row in DuckDB.
- **審查風險**: The percentage risk from the Auditor.
- **外資/投信**: The latest net buy/sell values in lots (張).
