import subprocess
import os
import sys

def run_workflow():
    scripts = [
        "/Users/bookid/.hermes/scripts/fetch_tw_historical_custom.py",
        "/Users/bookid/.hermes/scripts/merge_stock_data.py"
    ]
    
    for script in scripts:
        print(f"==> Executing: {os.path.basename(script)}")
        result = subprocess.run(["python3", script], capture_output=True, text=True)
        print(result.stdout)
        if result.returncode != 0:
            print(f"Error executing {script}:")
            print(result.stderr)
            # We continue if one fail? For historical fetch, we might want to merge what we have.
            # But for this critical task, let's stop and report.
            sys.exit(1)

    print("✅ Historical Data Workflow (Fetch + Merge) Completed Successfully.")

if __name__ == "__main__":
    run_workflow()
