import subprocess
import sys
import os
import time

SCRIPTS_DIR = "/Users/bookid/.hermes/scripts"

def run_script(name, *args):
    path = os.path.join(SCRIPTS_DIR, name)
    print(f"--- Executing {name} {' '.join(args)} ---")
    try:
        # DO NOT remove locks here. Let the scripts handle their own pacing.
        # The orchestrator is just a trigger.
        
        if name.endswith(".swift"):
            result = subprocess.run([path] + list(args), capture_output=True, text=True)
        else:
            result = subprocess.run([sys.executable, path] + list(args), capture_output=True, text=True)
        print(result.stdout)
        if result.stderr: print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Failed to run {name}: {e}")

def sync_numbers_filename():
    import datetime
    import shutil
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    target_file = f"/Users/bookid/Documents/StockTracking_{today_str}.numbers"
    link_path = "/Users/bookid/Documents/StockTracking_Daily.numbers"
    
    print(f"--- Syncing Numbers Filename for {today_str} ---")
    if not os.path.exists(target_file):
        import glob
        others = sorted(glob.glob("/Users/bookid/Documents/StockTracking_20*.numbers"), reverse=True)
        if others:
            print(f"Found latest: {others[0]}. Copying to {target_file} for today.")
            shutil.copy2(others[0], target_file)

    if os.path.exists(target_file):
        if os.path.islink(link_path):
            os.remove(link_path)
        elif os.path.exists(link_path):
            # If it's a real file, maybe back it up or just warn? 
            # But the requirement is to sync, so we'll replace.
            os.rename(link_path, link_path + ".bak")
        
        os.symlink(target_file, link_path)
        print(f"Synced: {link_path} -> {target_file}")
    else:
        print(f"Warning: Target file {target_file} not found. Skipping filename sync.")

def main():
    # 0. Sync Numbers Filename
    sync_numbers_filename()
    
    # 1. Sync Data (The Gatherer)
    run_script("hermes_sync.swift")
    
    # 2. Distribute (The Bots)
    # They will only send if they cross a tier threshold.
    run_script("hermes_monitor.swift", "--profile", "personal")
    run_script("hermes_monitor.swift", "--profile", "william")
    run_script("hermes_monitor.swift", "--profile", "group")

if __name__ == "__main__":
    main()
