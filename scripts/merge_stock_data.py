import os
import pandas as pd
import glob
import time
import concurrent.futures

# Configuration
DIR_A = os.path.expanduser("~/Documents/StockData_History")       # 15 Months (Recent, ~311 days)
DIR_B = os.path.expanduser("~/Documents/StockData_History_5Y")    # 5 Years (1,771 stocks)
DIR_C = os.path.expanduser("~/Documents/StockData_History_Full")  # 2010-2025 (Old 15-year, 418 stocks)
FINAL_DIR = os.path.expanduser("~/Documents/StockData_History_Final")

os.makedirs(FINAL_DIR, exist_ok=True)

def process_file(filename):
    dataframes = []
    standard_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
    
    for directory in [DIR_A, DIR_B, DIR_C]:
        path = os.path.join(directory, filename)
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                if df.empty:
                    continue
                # Normalize column matching (case-insensitive and strip spaces)
                cols_map = {c.lower().replace(' ', ''): c for c in df.columns}
                select_cols = []
                rename_map = {}
                for scol in standard_cols:
                    scol_key = scol.lower().replace(' ', '')
                    if scol_key in cols_map:
                        select_cols.append(cols_map[scol_key])
                        rename_map[cols_map[scol_key]] = scol
                
                # Check if we found at least the Date and Close columns
                if 'Date' in rename_map.values() and 'Close' in rename_map.values():
                    df_clean = df[select_cols].copy()
                    df_clean.columns = [rename_map[c] for c in df_clean.columns]
                    dataframes.append(df_clean)
            except Exception:
                pass

    if not dataframes:
        return False
        
    try:
        merged_df = pd.concat(dataframes, ignore_index=True)
        if not isinstance(merged_df, pd.DataFrame):
            return False
        # Vectorized datetime parsing and serialization format normalization
        merged_df['Date'] = pd.to_datetime(merged_df['Date'])
        # Drop duplicates by Date and sort
        merged_df = merged_df.drop_duplicates(subset=['Date']).sort_values(by='Date')
        
        # Format Date back to string format
        merged_df['Date'] = merged_df['Date'].dt.strftime('%Y-%m-%d')
        
        output_path = os.path.join(FINAL_DIR, filename)
        merged_df.to_csv(output_path, index=False)
        return True
    except Exception as e:
        print(f"Failed to process {filename}: {e}")
        return False

def merge_all():
    print(f"Starting highly optimized vector merge process...")
    start_time = time.time()
    
    files_a = set(os.path.basename(f) for f in glob.glob(os.path.join(DIR_A, "*.csv")))
    files_b = set(os.path.basename(f) for f in glob.glob(os.path.join(DIR_B, "*.csv")))
    files_c = set(os.path.basename(f) for f in glob.glob(os.path.join(DIR_C, "*.csv")))
    all_filenames = files_a.union(files_b).union(files_c)
    
    print(f"Total unique stock files identified: {len(all_filenames)}")

    count = 0
    # Process Pool for massive IO/CPU parallelization
    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = executor.map(process_file, all_filenames)
        for success in results:
            if success:
                count += 1
                if count % 200 == 0:
                    print(f"Merged {count} files...")

    duration = time.time() - start_time
    print(f"Merge complete in {duration:.2f} seconds. Total saved: {count}")
    print(f"Final data location: {FINAL_DIR}")

if __name__ == "__main__":
    merge_all()
