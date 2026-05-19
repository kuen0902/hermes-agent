#!/Users/bookid/.hermes/.venv/bin/python
import os
import shutil
import json

base_dir = "/Users/bookid/.hermes/scripts"
cron_file = "/Users/bookid/.hermes/cron/jobs.json"

dirs = ["bin", "ml", "fetchers"]
for d in dirs:
    os.makedirs(os.path.join(base_dir, d), exist_ok=True)

moves = {
    # Binaries
    "hermes_monitor": "bin",
    "hermes_orchestrator": "bin",
    "hermes_orchestrator_test": "bin",
    "hermes_sync": "bin",
    "swift_notifier_exe": "bin",
    # ML
    "intraday_ml_pipeline.py": "ml",
    "intraday_model_trainer.py": "ml",
    "ml_backtest_engine.py": "ml",
    "ml_feedback_loop.py": "ml",
    "ml_signal_inference.py": "ml",
    "ml_signal_reporter.py": "ml",
    "ml_trainer.py": "ml",
    "portfolio_ml_analysis.py": "ml",
    # Fetchers
    "fetch_institutional_data.py": "fetchers",
    "fetch_market_prices.py": "fetchers",
    "fetch_tw_historical_all.py": "fetchers",
    "fetch_tw_historical_custom.py": "fetchers",
    "update_market_prices.py": "fetchers"
}

print("Moving files...")
for file_name, target_dir in moves.items():
    src = os.path.join(base_dir, file_name)
    dst = os.path.join(base_dir, target_dir, file_name)
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"Moved {file_name} to {target_dir}/")

print("Updating cron jobs...")
if os.path.exists(cron_file):
    with open(cron_file, 'r') as f:
        jobs_data = json.load(f)
        
    updated = False
    for job in jobs_data.get("jobs", []):
        script = job.get("script")
        if script:
            for file_name, target_dir in moves.items():
                if file_name in script and target_dir not in script:
                    job["script"] = script.replace(file_name, f"{target_dir}/{file_name}")
                    updated = True
                    print(f"Updated job {job['name']} script path.")
                    
    if updated:
        with open(cron_file, 'w') as f:
            json.dump(jobs_data, f, indent=2, ensure_ascii=False)
        print("cron jobs updated successfully.")
    else:
        print("No cron jobs needed updating.")
        
print("Refactoring complete.")
