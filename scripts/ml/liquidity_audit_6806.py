import duckdb
import pandas as pd
import numpy as np
import os
import json

DATA_DIR = os.path.expanduser("~/.hermes/data")
DB_PATH = os.path.join(DATA_DIR, "potential_analysis.ddb")

def analyze_6806_liquidity_gap():
    print("--- Deep Analysis: 6806 Liquidity & Capital Flow Audit ---")
    conn = duckdb.connect(DB_PATH)
    
    # 1. Get prediction from 20 trading days ago
    # Using approx date logic
    pred_row = conn.execute("""
        SELECT date, close, predicted_return_20d 
        FROM predictions 
        WHERE code = '6806' AND date BETWEEN '2026-05-20' AND '2026-05-25'
        ORDER BY date ASC LIMIT 1
    """).fetchdf()
    
    if pred_row.empty:
        print("No prediction found for target window.")
        return
        
    p_date = pred_row.iloc[0]['date']
    p_close = float(pred_row.iloc[0]['close'])
    p_ret = float(pred_row.iloc[0]['predicted_return_20d'])
    target_price = p_close * (1 + p_ret)
    
    print(f"Prediction Date: {p_date} | Start Price: {p_close} | ML Target: {target_price:.2f} ({p_ret:+.2%})")
    
    # 2. Analyze Volume & Institutional Flow for 5 weeks
    history = conn.execute("""
        SELECT date, close, volume, (foreign_net + trust_net) as net_inst
        FROM daily_stock_data 
        WHERE code = '6806' AND date >= ?
        ORDER BY date ASC
    """, (p_date,)).fetchdf()
    
    history['week'] = (pd.to_datetime(history['date']).dt.isocalendar().week)
    start_week = history['week'].iloc[0]
    history['relative_week'] = history['week'] - start_week + 1

    print("\n--- Weekly Reality Audit ---")
    print(f"{'Week':<5} | {'Avg Price':<10} | {'Total Vol':<12} | {'Net Inst (Buy)':<15} | {'Result'}")
    print("-" * 65)
    
    for w in range(1, 6):
        w_data = history[history['relative_week'] == w]
        if w_data.empty: continue
        avg_p = w_data['close'].mean()
        tot_v = w_data['volume'].sum()
        net_i = w_data['net_inst'].sum()
        
        # Logic: If predicted UP but Net Inst is negative, it is a LIQUIDITY FAIL
        status = "✅ Flow Alignment" if (p_ret > 0 and net_i > 0) else "❌ FLOW DIVERGENCE (Selling)"
        if net_i < -100: status = "🚨 HEAVY DISTRIBUTION (FLEEING)"
        
        print(f"Week {w:<2} | {avg_p:<10.2f} | {tot_v:<12,.0f} | {net_i:<15.1f} | {status}")

    # 3. Liquidity-Corrected Target (Back-calculation)
    # If net flow is negative, the "Realized Probability" of the target should be scaled by flow ratio
    total_net = history['net_inst'].sum()
    total_vol = history['volume'].sum()
    flow_confidence = max(0, (total_net * 1000) / total_vol) if total_net > 0 else 0
    
    revised_target = p_close * (1 + (p_ret * flow_confidence))
    print(f"\n--- Architect's Final Revision ---")
    print(f"Flow Confidence Factor: {flow_confidence:.4f}")
    print(f"Volume-Adjusted Target: {revised_target:.2f}")
    
    if revised_target < p_close:
        print("RESULT: Based on actual 5-week capital flow, 6806 is a 'STRONG VOID'.")
        print("It would NEVER be #1 if capital flow synergy were required.")
    else:
        print("RESULT: Revision confirms predicted growth was physically impossible without massive buying.")

    conn.close()

if __name__ == "__main__":
    analyze_6806_liquidity_gap()
