import duckdb
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
from features_utils import prepare_daily_features

DATA_DIR = os.path.expanduser("~/.hermes/data")
DB_PATH = os.path.join(DATA_DIR, "potential_analysis.ddb")
BIAS_PATH = os.path.join(DATA_DIR, "ml_bias_matrix.json")

def fast_predict():
    conn = duckdb.connect(DB_PATH)
    target_codes = ['2330', '2454', '2317', '2382', '3231', '1513', '1519', '2603', '2609', '2408', '2409', '3481', '3037', '3035', '3661', '3443', '6669']
    results = []
    
    with open(BIAS_PATH, 'r') as bf:
        bias_data = json.load(bf)
        b1, b2, b3 = bias_data.get('bias_1w', 0), bias_data.get('bias_2w', 0), bias_data.get('bias_3w', 0)
        sys_bias = ( (b1 or 0) * 0.5 + (b2 or 0) * 0.3 + (b3 or 0) * 0.2)

    for code in target_codes:
        ticker = f"{code}.TW"
        # Adjusted date comparison with CAST
        df = conn.execute("""
            SELECT 
                d.date AS Date, d.open AS Open, d.high AS High, d.low AS Low, d.close AS Close, 
                d.volume AS Volume, d.foreign_net AS Foreign_Net, d.trust_net AS Trust_Net, d.dealer_net AS Dealer_Net,
                (SELECT r.revenue FROM monthly_revenue r WHERE r.code = d.code AND CAST(r.date AS DATE) <= d.date ORDER BY r.date DESC LIMIT 1) AS Monthly_Revenue,
                (SELECT r.yoy FROM monthly_revenue r WHERE r.code = d.code AND CAST(r.date AS DATE) <= d.date ORDER BY r.date DESC LIMIT 1) AS Revenue_YoY,
                (SELECT r.mom FROM monthly_revenue r WHERE r.code = d.code AND CAST(r.date AS DATE) <= d.date ORDER BY r.date DESC LIMIT 1) AS Revenue_MoM,
                (SELECT r.eps FROM financial_statements r WHERE r.code = d.code AND CAST(r.report_date AS DATE) <= d.date ORDER BY r.report_date DESC LIMIT 1) AS EPS,
                (SELECT r.gross_profit_margin FROM financial_statements r WHERE r.code = d.code AND CAST(r.report_date AS DATE) <= d.date ORDER BY r.report_date DESC LIMIT 1) AS Gross_Profit_Margin,
                (SELECT r.operating_profit_margin FROM financial_statements r WHERE r.code = d.code AND CAST(r.report_date AS DATE) <= d.date ORDER BY r.report_date DESC LIMIT 1) AS Operating_Profit_Margin,
                (SELECT r.net_profit_margin FROM financial_statements r WHERE r.code = d.code AND CAST(r.report_date AS DATE) <= d.date ORDER BY r.report_date DESC LIMIT 1) AS Net_Profit_Margin
            FROM daily_stock_data d WHERE d.code = ? ORDER BY d.date ASC
        """, (code,)).fetchdf()
        
        if len(df) < 80: continue
        processed = prepare_daily_features(df)
        if processed is None: continue
        last = processed.iloc[-1].copy()
        
        risk_penalty = 0.0
        if last['Max_DD_5'] < -0.10: risk_penalty += 0.05
        if last['Bull_Trap_Signal'] > 0.5: risk_penalty += 0.05
        
        raw_pred = last['Ret_20'] * 0.5 + 0.02 # Placeholder heuristic
        final_score = raw_pred - sys_bias - risk_penalty
        
        results.append({
            "ticker": ticker,
            "name": conn.execute("SELECT name FROM daily_stock_data WHERE code=? LIMIT 1", (code,)).fetchone()[0],
            "close": float(last['Close']),
            "score": float(final_score),
            "ret_5d": float(last['Ret_5']),
            "inst_flow": float(last['Inst_Flow_Ratio_5D'])
        })
        
    res_df = pd.DataFrame(results).sort_values(by='score', ascending=False)
    print("RANKING_START")
    print(res_df.to_string(index=False))
    print("RANKING_END")
    conn.close()

if __name__ == "__main__":
    fast_predict()
