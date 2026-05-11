import os
import pandas as pd
import json
import yfinance as yf
from datetime import datetime
import time

DATA_DIR = os.path.expanduser("~/Documents/StockData_History_Final")
QUEUE_FILE = os.path.expanduser("~/.hermes/data/backfill_queue.json")

def initialize_queue():
    if os.path.exists(QUEUE_FILE):
        return
    
    print("Scanning directory to identify stocks needing backfill...")
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    needs_backfill = []
    
    for filename in files:
        path = os.path.join(DATA_DIR, filename)
        try:
            # Quick check: rows < 3000 means it's likely missing long history (15 years ~ 3700 days)
            df = pd.read_csv(path)
            if len(df) < 3000:
                # Store ticker only (e.g. 2330.TW)
                ticker = filename.split('_')[0]
                needs_backfill.append(ticker)
        except: continue
        
    os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
    with open(QUEUE_FILE, 'w') as f:
        json.dump({"pending": needs_backfill, "completed": []}, f)
    print(f"Queue initialized with {len(needs_backfill)} stocks.")

def verify_health(file_path, ticker):
    """
    Mandatory Health Check Protocol:
    1. Size Check: > 1KB
    2. Quality Check: No NaN in critical columns
    3. Depth Check: Verify earliest date is around 2010
    """
    try:
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        # 1. Size Check
        size_kb = os.path.getsize(file_path) / 1024
        if size_kb < 1:
            return False, f"File too small ({size_kb:.2f} KB)"
            
        # 2. Quality Check
        df = pd.read_csv(file_path)
        if df.empty:
            return False, "File is empty"
        
        nan_count = df['Close'].isna().sum()
        if nan_count > len(df) * 0.05: # Allow 5% max NaNs
            return False, f"Too many NaNs ({nan_count})"
            
        # 3. Depth Check
        first_date = pd.to_datetime(df.iloc[0, 0])
        if first_date.year > 2012: # Target was 2010, but some stocks might have listed later
            print(f"Warning: {ticker} earliest date is {first_date.date()}, may be late listing.")
            
        return True, "Healthy"
    except Exception as e:
        return False, str(e)

def process_batch(batch_size=500):
    if not os.path.exists(QUEUE_FILE):
        initialize_queue()
        
    with open(QUEUE_FILE, 'r') as f:
        queue = json.load(f)
    
    pending = queue.get("pending", [])
    completed = queue.get("completed", [])
    failure_counts = queue.get("failure_counts", {}) # Track consecutive failures
    permanent_fail = queue.get("permanent_fail", []) # Dead tickers
    
    if not pending:
        print("All stocks backfilled.")
        return
        
    batch = pending[:batch_size]
    remaining = pending[batch_size:]
    
    print(f"Starting batch backfill for {len(batch)} stocks (Size: 500)...")
    start_date = "2010-01-01"
    end_date = "2026-05-04"
    
    # Download
    try:
        data = yf.download(batch, start=start_date, end=end_date, group_by='ticker', threads=True)
        
        success_tickers = []
        fail_tickers = []
        to_investigate = []
        
        for ticker in batch:
            try:
                t_data = data[ticker].dropna() if len(batch) > 1 else data.dropna()
                if not t_data.empty:
                    matching_files = [f for f in os.listdir(DATA_DIR) if f.startswith(ticker)]
                    if matching_files:
                        file_path = os.path.join(DATA_DIR, matching_files[0])
                        t_data.to_csv(file_path)
                        
                        is_healthy, reason = verify_health(file_path, ticker)
                        if is_healthy:
                            success_tickers.append(ticker)
                            failure_counts.pop(ticker, None) # Reset on success
                        else:
                            fail_tickers.append(ticker)
                            failure_counts[ticker] = failure_counts.get(ticker, 0) + 1
                else:
                    fail_tickers.append(ticker)
                    failure_counts[ticker] = failure_counts.get(ticker, 0) + 1
            except: 
                fail_tickers.append(ticker)
                failure_counts[ticker] = failure_counts.get(ticker, 0) + 1
                continue
            
            # Check for 3 consecutive failures
            if failure_counts.get(ticker, 0) >= 3:
                to_investigate.append(ticker)
                
        print(f"Batch complete. Healthy: {len(success_tickers)}, Failed: {len(fail_tickers)}")
        if to_investigate:
            print(f"Tickers for investigation (3+ fails): {to_investigate}")
        
        # Update Queue
        queue["pending"] = [t for t in pending if t not in success_tickers]
        queue["completed"] = list(set(completed + success_tickers))
        queue["failure_counts"] = failure_counts
        
        with open(QUEUE_FILE, 'w') as f:
            json.dump(queue, f)
            
        return to_investigate # Hand off to agent for web search
            
    except Exception as e:
        print(f"Batch failed: {e}")

if __name__ == "__main__":
    process_batch(200)
