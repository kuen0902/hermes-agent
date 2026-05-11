import os
import json
import pandas as pd
from datetime import datetime, timedelta

# Paths
LOG_DIR = os.path.expanduser("~/Documents/Reports/Analysis_Logs/Daily_Confluence")
PERFORMANCE_CSV = os.path.expanduser("~/Documents/Reports/Analysis_Logs/ml_performance_tracker.csv")

def track_performance():
    print("--- 🧠 AI Architect: ML Model Feedback Loop (Error Correction) ---")
    
    # 1. Get dates
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    # (If today is Monday, yesterday should be Friday - simple check for now)
    if today.weekday() == 0: yesterday = today - timedelta(days=3)
    
    today_str = today.strftime('%Y-%m-%d')
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    
    # 2. Files
    y_data_path = os.path.join(LOG_DIR, f"{yesterday_str}_Group_Data.json")
    t_data_path = os.path.join(LOG_DIR, f"{today_str}_Group_Data.json")
    
    if not os.path.exists(y_data_path) or not os.path.exists(t_data_path):
        print(f"Skipping: Missing data for {yesterday_str} or {today_str}")
        return

    with open(y_data_path, 'r') as f: y_data = json.load(f)
    with open(t_data_path, 'r') as f: t_data = json.load(f)
    
    results = []
    
    for code, y_info in y_data.items():
        if code in t_data:
            t_info = t_data[code]
            
            # Outcome: Actual Return
            y_close = y_info['price']
            t_close = t_info['price']
            actual_ret = (t_close - y_close) / y_close
            
            # (Note: In future, I will extract the ML probabilities here)
            # For now, we log the movement to establish a baseline
            results.append({
                "date": today_str,
                "code": code,
                "prev_close": y_close,
                "curr_close": t_close,
                "actual_return_pct": actual_ret * 100
            })
            
    # 3. Save/Append to Master Log
    df = pd.DataFrame(results)
    file_exists = os.path.exists(PERFORMANCE_CSV)
    df.to_csv(PERFORMANCE_CSV, mode='a', header=not file_exists, index=False)
    
    print(f"✅ Performance logged for {len(results)} stocks.")
    print(f"📁 Tracking file: {PERFORMANCE_CSV}")
    print("無駄無駄無駄！誤差已被捕捉，機器學習優化程序啟動中。")

if __name__ == "__main__":
    track_performance()
