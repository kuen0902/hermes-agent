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
    
    # Horizons in trading days: 1W=5, 2W=10, 3W=15, 4W=20, 5W=25
    horizons = {
        "5d": "actual_return_5d",
        "10d": "actual_return_10d",
        "15d": "actual_return_15d",
        "20d": "actual_return_20d",
        "25d": "actual_return_25d"
    }

    # 1. Fetch all predictions from the last 40 days that need auditing
    # We audit any record where the 5-week (25d) return is still missing
    pending_preds = conn.execute("""
        SELECT date, code, ticker, close AS pred_price, predicted_return_20d 
        FROM predictions 
        WHERE actual_return_25d IS NULL AND date >= current_date - interval '50 days'
    """).fetchdf()

    if pending_preds.empty:
        print("✓ No predictions found in the audit window.")
        conn.close()
        return

    print(f"Auditing {len(pending_preds)} historical predictions across 5 horizons...")

    stats = {"hits": 0, "failures": []}

    for idx, row in pending_preds.iterrows():
        pred_date = row['date']
        code = row['code']
        pred_price = float(row['pred_price'])
        
        # Get all future price actions for this stock
        future_data = conn.execute("""
            SELECT date, close FROM daily_stock_data 
            WHERE code = ? AND date > ? ORDER BY date ASC LIMIT 30
        """, (code, pred_date)).fetchdf()
        
        if future_data.empty or pred_price == 0:
            continue
            
        updates = {}
        for days, col in horizons.items():
            idx_offset = int(days.replace('d', '')) - 1
            if len(future_data) > idx_offset:
                actual_price = float(future_data.iloc[idx_offset]['close'])
                actual_ret = (actual_price / pred_price) - 1.0
                updates[col] = actual_ret
                
                # Performance Review: If it's a 20d prediction, we primarily check error at 20d
                if days == "20d":
                    error = float(row['predicted_return_20d']) - actual_ret
                    updates['prediction_error'] = error
                    if actual_ret < -0.10 and float(row['predicted_return_20d']) > 0.10:
                        stats['failures'].append({"ticker": row['ticker'], "date": str(pred_date), "error": error})

        if updates:
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            params = list(updates.values()) + [pred_date, code]
            conn.execute(f"UPDATE predictions SET {set_clause} WHERE date = ? AND code = ?", params)
            stats['hits'] += 1

    # 2. Generate the Learning Bias Matrix (Aggregate multi-week failures)
    # We look for consistency in error (e.g. is it always failing on 1W, 2W, etc?)
    bias_audit = conn.execute("""
        SELECT 
            AVG(predicted_return_20d - actual_return_5d) as bias_1w,
            AVG(predicted_return_20d - actual_return_10d) as bias_2w,
            AVG(predicted_return_20d - actual_return_15d) as bias_3w,
            AVG(predicted_return_20d - actual_return_20d) as bias_4w,
            AVG(predicted_return_20d - actual_return_25d) as bias_5w
        FROM predictions
        WHERE actual_return_5d IS NOT NULL
    """).fetchdf()

    bias_matrix = bias_audit.to_dict(orient='records')[0]
    bias_matrix['last_updated'] = datetime.now().isoformat()
    bias_matrix['failing_tickers'] = [f['ticker'] for f in stats['failures'][-20:]] # Latest 20 failures
    
    with open(BIAS_PATH, 'w') as f:
        json.dump(bias_matrix, f, indent=2)

    print(f"✓ Audit Complete. {stats['hits']} records updated.")
    print(f"✓ Week-by-Week Bias Logic Synced: {bias_matrix}")
    conn.close()

if __name__ == "__main__":
    audit_multi_period_performance()
