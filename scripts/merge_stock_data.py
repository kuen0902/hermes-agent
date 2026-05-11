import os
import pandas as pd
import glob

# Configuration
DIR_A = os.path.expanduser("~/Documents/StockData_History")       # 15 Months
DIR_B = os.path.expanduser("~/Documents/StockData_History_Full")  # 2010-2025
FINAL_DIR = os.path.expanduser("~/Documents/StockData_History_Final")

os.makedirs(FINAL_DIR, exist_ok=True)

def merge_all():
    print(f"Starting merge process...")
    print(f"Source 1: {DIR_A}")
    print(f"Source 2: {DIR_B}")
    print(f"Destination: {FINAL_DIR}")

    # Get all unique filenames from both directories
    files_a = {os.path.basename(f): f for f in glob.glob(os.path.join(DIR_A, "*.csv"))}
    files_b = {os.path.basename(f): f for f in glob.glob(os.path.join(DIR_B, "*.csv"))}
    
    all_filenames = set(files_a.keys()).union(set(files_b.keys()))
    print(f"Total unique stock files identified: {len(all_filenames)}")

    count = 0
    for filename in all_filenames:
        dataframes = []
        
        # Try to load from both sources
        if filename in files_a:
            try:
                df_a = pd.read_csv(files_a[filename])
                dataframes.append(df_a)
            except Exception as e:
                print(f"Error reading {filename} from Source 1: {e}")
                
        if filename in files_b:
            try:
                df_b = pd.read_csv(files_b[filename])
                dataframes.append(df_b)
            except Exception as e:
                print(f"Error reading {filename} from Source 2: {e}")

        if not dataframes:
            continue

        try:
            # Merge
            merged_df = pd.concat(dataframes, ignore_index=True)
            
            # Ensure 'Date' is datetime for correct sorting
            merged_df['Date'] = pd.to_datetime(merged_df['Date'])
            
            # Deduplicate by Date (keep the first occurrence - usually identical)
            merged_df = merged_df.drop_duplicates(subset=['Date']).sort_values(by='Date')
            
            # Save to final directory
            output_path = os.path.join(FINAL_DIR, filename)
            merged_df.to_csv(output_path, index=False)
            count += 1
            
            if count % 100 == 0:
                print(f"Merged {count} files...")
                
        except Exception as e:
            print(f"Failed to merge {filename}: {e}")

    print(f"Merge complete. Total merged files saved: {count}")
    print(f"Final data location: {FINAL_DIR}")

if __name__ == "__main__":
    merge_all()
