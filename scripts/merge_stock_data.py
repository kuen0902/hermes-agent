import os
import pandas as pd
import glob
import time
import concurrent.futures

# Configuration
DIR_A = os.path.expanduser("~/Documents/StockData_History")       # 15 Months
DIR_B = os.path.expanduser("~/Documents/StockData_History_Full")  # 2010-2025
FINAL_DIR = os.path.expanduser("~/Documents/StockData_History_Final")

os.makedirs(FINAL_DIR, exist_ok=True)

def process_file(filename):
    file_a = os.path.join(DIR_A, filename)
    file_b = os.path.join(DIR_B, filename)
    
    dataframes = []
    
    if os.path.exists(file_a):
        try:
            df_a = pd.read_csv(file_a)
            dataframes.append(df_a)
        except Exception: pass
            
    if os.path.exists(file_b):
        try:
            df_b = pd.read_csv(file_b)
            dataframes.append(df_b)
        except Exception: pass

    if not dataframes:
        return False
        
    try:
        merged_df = pd.concat(dataframes, ignore_index=True)
        # Vectorized datetime parsing
        merged_df['Date'] = pd.to_datetime(merged_df['Date'])
        # Drop duplicates by Date and sort
        merged_df = merged_df.drop_duplicates(subset=['Date']).sort_values(by='Date')
        
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
    all_filenames = files_a.union(files_b)
    
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
