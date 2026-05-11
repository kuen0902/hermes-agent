import subprocess
import os
import time
import datetime

SCRIPTS_DIR = "/Users/bookid/.hermes/scripts"

def run_script(name):
    path = os.path.join(SCRIPTS_DIR, name)
    print(f"--- Executing {name} ---")
    try:
        # DO NOT remove locks here. Let the scripts handle their own pacing.
        # The orchestrator is just a trigger.
        
        result = subprocess.run(["python3", path], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr: print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Failed to run {name}: {e}")

def sync_numbers_filename():
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    target_file = f"/Users/bookid/Documents/StockTracking_{today_str}.numbers"
    link_path = "/Users/bookid/Documents/StockTracking_Daily.numbers"
    
    print(f"--- Syncing Numbers Filename for {today_str} ---")
    if os.path.exists(target_file):
        if os.path.islink(link_path):
            os.remove(link_path)
        elif os.path.exists(link_path):
            os.rename(link_path, link_path + ".bak")
        
        os.symlink(target_file, link_path)
        print(f"Synced: {link_path} -> {target_file}")
    else:
        print(f"Warning: Target file {target_file} not found. Skipping filename sync.")

def main():
    # 0. Sync Numbers Filename
    sync_numbers_filename()

    # 1. Sync Data (The Gatherer)
    run_script("taiex_central_data_sync.py")
    
    # 2. Distribute (The Bots)
    # They will only send if they haven't sent in the last 8 minutes.
    run_script("stock_monitor.py")
    run_script("william_stock_monitor.py")
    run_script("group_stock_monitor.py")

if __name__ == "__main__":
    main()
