import duckdb
import pandas as pd
import os
import json
from datetime import datetime, timedelta

DATA_DIR = os.path.expanduser("~/.hermes/data")
DB_PATH = os.path.join(DATA_DIR, "potential_analysis.ddb")
BIAS_PATH = os.path.join(DATA_DIR, "ml_bias_matrix.json")

def audit_multi_period_performance():
    print("--- ML Multi-Period Architect Auditor: 1W to 5W Deep Review ---")
    conn = duckdb.connect(DB_PATH)
    horizons = {"5d": "actual_return_5d", "10d": "actual_return_10d", "15d": "actual_return_15d", "20d": "actual_return_20d", "25d": "actual_return_25d"}

    pending_preds = conn.execute("""
        SELECT date, code, ticker, close AS pred_price, predicted_return_20d 
        FROM predictions 
        WHERE actual_return_25d IS NULL AND date >= current_date - interval '50 days'
    """).fetchdf()

    if pending_preds.empty:
        conn.close()
        return

    stats = {"hits": 0, "failures": []}
    for idx, row in pending_preds.iterrows():
        pred_date, code, pred_price = row['date'], row['code'], float(row['pred_price'])
        future_data = conn.execute("SELECT date, close FROM daily_stock_data WHERE code = ? AND date > ? ORDER BY date ASC LIMIT 30", (code, pred_date)).fetchdf()
        
        if future_data.empty or pred_price == 0: continue
            
        updates = {}
        for days, col in horizons.items():
            idx_offset = int(days.replace('d', '')) - 1
            if len(future_data) > idx_offset:
                actual_price = float(future_data.iloc[idx_offset]['close'])
                actual_ret = (actual_price / pred_price) - 1.0
                updates[col] = actual_ret
                if days == "20d":
                    updates['prediction_error'] = float(row['predicted_return_20d']) - actual_ret
                    if actual_ret < -0.10 and float(row['predicted_return_20d']) > 0.10:
                        stats['failures'].append(code)

        if updates:
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            conn.execute(f"UPDATE predictions SET {set_clause} WHERE date = ? AND code = ?", list(updates.values()) + [pred_date, code])
            stats['hits'] += 1

    bias_audit = conn.execute("""
        SELECT AVG(predicted_return_20d - actual_return_5d) as b1, AVG(predicted_return_20d - actual_return_10d) as b2, 
               AVG(predicted_return_20d - actual_return_15d) as b3, AVG(predicted_return_20d - actual_return_20d) as b4,
               AVG(predicted_return_20d - actual_return_25d) as b5 FROM predictions WHERE actual_return_5d IS NOT NULL
    """).fetchdf()

    bias_matrix = bias_audit.to_dict(orient='records')[0]
    bias_matrix['last_updated'] = datetime.now().isoformat()
    bias_matrix['failing_codes'] = list(set(stats['failures']))
    
    with open(BIAS_PATH, 'w') as f: json.dump(bias_matrix, f, indent=2)
    conn.close()

if __name__ == "__main__":
    audit_multi_period_performance()
