import os
import pandas as pd
import json
import yfinance as yf
from datetime import datetime

DATA_DIR = os.path.expanduser("~/Documents/StockData_History_Final")
QUEUE_FILE = os.path.expanduser("~/.hermes/data/backfill_queue.json")

def verify_health(file_path, ticker):
    try:
        if not os.path.exists(file_path): return False, "Missing"
        if os.path.getsize(file_path) / 1024 < 1: return False, "Size < 1KB"
        df = pd.read_csv(file_path)
        if df.empty: return False, "Empty"
        if df['Close'].isna().sum() > len(df) * 0.05: return False, "NaNs > 5%"
        return True, "Healthy"
    except Exception as e: return False, str(e)

def process_batch(batch_size=500):
    with open(QUEUE_FILE, 'r') as f:
        queue = json.load(f)
    
    pending = queue.get("pending", [])
    failure_counts = queue.get("failure_counts", {})
    to_investigate = []
    
    batch = pending[:batch_size]
    data = yf.download(batch, start="2010-01-01", group_by='ticker', threads=True)
    
    success_tickers = []
    for ticker in batch:
        try:
            t_data = data[ticker].dropna() if len(batch) > 1 else data.dropna()
            if not t_data.empty:
                # Save and Verify
                matching_files = [f for f in os.listdir(DATA_DIR) if f.startswith(ticker)]
                if matching_files:
                    path = os.path.join(DATA_DIR, matching_files[0])
                    t_data.to_csv(path)
                    is_h, _ = verify_health(path, ticker)
                    if is_h: 
                        success_tickers.append(ticker)
                        failure_counts.pop(ticker, None)
                        continue
            
            # Logic for failure
            failure_counts[ticker] = failure_counts.get(ticker, 0) + 1
            if failure_counts[ticker] >= 3: to_investigate.append(ticker)
        except:
             failure_counts[ticker] = failure_counts.get(ticker, 0) + 1
             
    # Update queue and save
    queue["pending"] = [t for t in pending if t not in success_tickers]
    queue["completed"] = list(set(queue.get("completed", []) + success_tickers))
    queue["failure_counts"] = failure_counts
    with open(QUEUE_FILE, 'w') as f: json.dump(queue, f)
    return to_investigate
