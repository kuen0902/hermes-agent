#!/Users/bookid/.hermes/.venv/bin/python
import os
import pandas as pd
import numpy as np
import duckdb
from datetime import datetime

# Configuration
DATA_DIR = os.path.expanduser("~/.hermes/data")
DB_PATH = os.path.join(DATA_DIR, "potential_analysis.ddb")

def calibrate_predictions():
    print("=========================================================================")
    print("  🧠 AI QUANT ARCHITECT: ML FORECAST CALIBRATION SYSTEM (FEEDBACK LOOP)")
    print("=========================================================================")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: DuckDB database not found at {DB_PATH}.")
        return
        
    print(f"Connecting to DuckDB database: {DB_PATH}")
    conn = duckdb.connect(DB_PATH)
    
    # 1. Verify and Dynamically Alter predictions Table Schema
    try:
        cols_df = conn.execute("PRAGMA table_info(predictions)").fetchdf()
        col_names = cols_df['name'].tolist()
        
        if 'actual_return_20d' not in col_names:
            print("🔹 Altering 'predictions' table: Adding column 'actual_return_20d'...")
            conn.execute("ALTER TABLE predictions ADD COLUMN actual_return_20d DOUBLE")
            
        if 'prediction_error' not in col_names:
            print("🔹 Altering 'predictions' table: Adding column 'prediction_error'...")
            conn.execute("ALTER TABLE predictions ADD COLUMN prediction_error DOUBLE")
            
    except Exception as e:
        print(f"❌ Error verifying/altering database schema: {e}")
        conn.close()
        return

    # 2. Fetch Uncalibrated Predictions (where actual_return_20d is NULL)
    try:
        uncalibrated = conn.execute("""
            SELECT date, code, ticker, name, predicted_return_20d, close
            FROM predictions 
            WHERE actual_return_20d IS NULL
            ORDER BY date ASC
        """).fetchdf()
    except Exception as e:
        print(f"❌ Error fetching uncalibrated predictions: {e}")
        conn.close()
        return
        
    print(f"Total uncalibrated prediction records found: {len(uncalibrated)}")
    if uncalibrated.empty:
        print("✓ All historical predictions are fully calibrated. Nothing to process.")
        conn.close()
        return
        
    calibrated_count = 0
    errors_list = []
    
    # 3. Perform Calibration Loop per Record
    for idx, row in uncalibrated.iterrows():
        pred_date = row['date']
        code = row['code']
        ticker = row['ticker']
        name = row['name']
        predicted_ret = row['predicted_return_20d']
        pred_close = row['close']
        
        try:
            # Query dates and closes starting from pred_date
            history = conn.execute("""
                SELECT date, close 
                FROM daily_stock_data 
                WHERE ticker = ? AND date >= ? 
                ORDER BY date ASC
            """, (ticker, pred_date)).fetchdf()
            
            if history.empty:
                continue
                
            # 🎯 CRITICAL RULE: execute dropna strictly on this individual stock's read out DataFrame
            history = history.dropna(subset=['close']).reset_index(drop=True)
            
            # The prediction day itself is index 0. The 20th trading day later is index 20.
            # We need at least 21 records to have index 20.
            if len(history) >= 21:
                target_row = history.iloc[20]
                target_date = target_row['date']
                close_20d = target_row['close']
                
                # Check for invalid prices
                if pd.isna(close_20d) or pd.isna(pred_close) or pred_close == 0:
                    continue
                    
                # Calculate actual return and prediction error (predicted - actual)
                actual_ret = (close_20d / pred_close) - 1.0
                pred_error = predicted_ret - actual_ret
                
                # Update row in predictions table
                conn.execute("""
                    UPDATE predictions 
                    SET actual_return_20d = ?, prediction_error = ? 
                    WHERE date = ? AND code = ?
                """, (float(actual_ret), float(pred_error), pred_date, code))
                
                calibrated_count += 1
                errors_list.append(abs(pred_error))
                
                print(f"  ✓ Calibrated {ticker} ({name}) predicted on {pred_date}:")
                print(f"    - Base Price: {pred_close:.2f} -> 20D Close: {close_20d:.2f} (on {target_date})")
                print(f"    - Forecast: {predicted_ret*100:+.2f}% | Actual: {actual_ret*100:+.2f}% | Error: {pred_error*100:+.2f}%")
                
        except Exception as err:
            print(f"  ⚠️ Error calibrating {ticker} on {pred_date}: {err}")
            
    # 4. Generate Performance Summary
    if calibrated_count > 0:
        mean_absolute_error = np.mean(errors_list)
        print("-------------------------------------------------------------------------")
        print(f"🎉 Calibration Step Complete! Successfully calibrated {calibrated_count} prediction records.")
        print(f"📊 Calibration MAE (Mean Absolute Error): {mean_absolute_error*100:.2f}%")
        print("-------------------------------------------------------------------------")
    else:
        print("-------------------------------------------------------------------------")
        print("ℹ️ No records met the 20-trading-day limit yet (data is too recent).")
        print("-------------------------------------------------------------------------")
        
    conn.close()

if __name__ == "__main__":
    calibrate_predictions()
