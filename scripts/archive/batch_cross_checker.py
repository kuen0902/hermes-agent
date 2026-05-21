import os
import pandas as pd
import json
from datetime import datetime

DATA_DIR = os.path.expanduser("~/Documents/StockData_History_Final")
QUEUE_FILE = os.path.expanduser("~/.hermes/data/backfill_queue.json")
REPORT_FILE = os.path.expanduser("~/.hermes/data/cross_check_report.json")

def cross_check():
    print("--- Starting Batch Cross-Check ---")
    if not os.path.exists(QUEUE_FILE):
        print("Queue file not found. Skipping.")
        return

    with open(QUEUE_FILE, 'r') as f:
        queue = json.load(f)

    # Check the latest 'completed' items. Since we process 200 at a time, 
    # we'll look at the last 200 in the completed list.
    recent_batch = queue.get("completed", [])[-200:]
    if not recent_batch:
        print("No recently completed stocks found to check.")
        return

    results = {
        "timestamp": datetime.now().isoformat(),
        "total_checked": len(recent_batch),
        "passed": [],
        "failed": [],
        "errors": {}
    }

    pending_redo = []

    for ticker in recent_batch:
        matching_files = [f for f in os.listdir(DATA_DIR) if f.startswith(ticker)]
        if not matching_files:
            results["failed"].append(ticker)
            results["errors"][ticker] = "File missing"
            pending_redo.append(ticker)
            continue
        
        file_path = os.path.join(DATA_DIR, matching_files[0])
        try:
            df = pd.read_csv(file_path)
            
            # Check 1: Row count (15 years ~ 3500+ trading days)
            if len(df) < 3000:
                raise ValueError(f"Insufficient historical depth: {len(df)} rows")

            # Check 2: Date Coverage
            df['Date'] = pd.to_datetime(df['Date'])
            min_date = df['Date'].min()
            if min_date.year > 2011: # Broad tolerance
                raise ValueError(f"Start date too late: {min_date.strftime('%Y-%m-%d')}")

            # Check 3: NaN threshold
            nan_count = df.isnull().sum().sum()
            if nan_count > (len(df) * 0.05): # Max 5% total NaNs
                raise ValueError(f"Too many NaNs detected: {nan_count}")

            results["passed"].append(ticker)
            
        except Exception as e:
            results["failed"].append(ticker)
            results["errors"][ticker] = str(e)
            pending_redo.append(ticker)

    # If any failed, move them back to pending
    if pending_redo:
        print(f"Moving {len(pending_redo)} failed stocks back to pending queue.")
        # Remove from completed
        queue["completed"] = [t for t in queue["completed"] if t not in pending_redo]
        # Add to the FRONT of pending for immediate retry next time
        queue["pending"] = pending_redo + queue["pending"]
        
        with open(QUEUE_FILE, 'w') as f:
            json.dump(queue, f)

    # Save Cross-Check Report
    with open(REPORT_FILE, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Cross-Check Summary: {len(results['passed'])} PASSED, {len(results['failed'])} FAILED.")
    if results["failed"]:
        print(f"Failures: {', '.join(results['failed'][:10])}...")

if __name__ == "__main__":
    cross_check()
