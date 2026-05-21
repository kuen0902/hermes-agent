import os
import pandas as pd
from datetime import datetime, timedelta

# Target directory
DATA_DIR = os.path.expanduser("~/Documents/StockData_History_Final")

def check_health():
    print(f"--- Data Health Check: {DATA_DIR} ---")
    
    if not os.path.exists(DATA_DIR):
        print(f"ERROR: Directory {DATA_DIR} does not exist.")
        return

    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    total_files = len(files)
    print(f"Total CSV files found: {total_files}")

    if total_files == 0:
        print("ERROR: No CSV files found.")
        return

    # Sampling 10% or max 20 files for a quick but detailed check
    sample_size = min(total_files, 20)
    import random
    sample_files = random.sample(files, sample_size)
    
    errors = []
    warnings = []
    
    today = datetime.now()
    threshold_date = today - timedelta(days=7) # Expect data within last 7 days

    for filename in sample_files:
        path = os.path.join(DATA_DIR, filename)
        try:
            # 1. Size check
            if os.path.getsize(path) < 1024:
                errors.append(f"{filename}: File size too small ({os.path.getsize(path)} bytes)")
                continue

            # 2. Load check
            df = pd.read_csv(path)
            if df.empty:
                errors.append(f"{filename}: CSV is empty")
                continue

            # 3. Schema check
            required_cols = {'Date', 'Open', 'Close', 'Highlight', 'Low'} # Adjusted based on typical yfinance
            # Note: yfinance often has 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'
            actual_cols = set(df.columns)
            if 'Date' not in actual_cols:
                errors.append(f"{filename}: Missing 'Date' column")
            
            # 4. Date Continuity check
            df['Date'] = pd.to_datetime(df['Date'])
            max_date = df['Date'].max()
            
            if max_date < threshold_date:
                warnings.append(f"{filename}: Latency detected. Last date: {max_date.strftime('%Y-%m-%d')}")

        except Exception as e:
            errors.append(f"{filename}: Load failed - {e}")

    # Summary
    print("\n--- Summary ---")
    print(f"Sampled Files: {sample_size}")
    if not errors and not warnings:
        print("✅ Data looks healthy (Sample check passed).")
    else:
        if errors:
            print(f"❌ Critical Errors ({len(errors)}):")
            for err in errors: print(f"  - {err}")
        if warnings:
            print(f"⚠️ Warnings ({len(warnings)}):")
            for warn in warnings: print(f"  - {warn}")

if __name__ == "__main__":
    check_health()
