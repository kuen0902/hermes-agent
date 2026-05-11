import os
import pandas as pd
from datetime import datetime
import pytz
import shutil
import subprocess

# Paths
REPORTS_ROOT = os.path.expanduser("~/Documents/Reports")
NIGHT_ARCHIVE_DIR = os.path.join(REPORTS_ROOT, "NightSession")
INTRADAY_BATCHES = os.path.expanduser("~/Documents/Reports/Analysis_Logs/Daily_Intraday_Batches")
OBSIDIAN_VAULT = os.path.expanduser("~/Documents/Obsidian Vault/Finance/DailyReports")

def run_report_scripts():
    """Runs the reporting scripts and captures output."""
    scripts = [
        "/Users/bookid/.hermes/scripts/tw_night_monitor_adri.py",
        "/Users/bookid/.hermes/scripts/tw_night_session_hourly.py"
    ]
    report_parts = []
    for s in scripts:
        try:
            res = subprocess.run(["python3", s], capture_output=True, text=True)
            if res.returncode == 0:
                report_parts.append(res.stdout.strip())
        except Exception as e:
            report_parts.append(f"Error running {s}: {e}")
    return "\n\n---\n\n".join(report_parts)

def archive_settlement():
    taipei_tz = pytz.timezone('Asia/Taipei')
    today_str = datetime.now(taipei_tz).strftime("%Y-%m-%d")
    archive_path = os.path.join(NIGHT_ARCHIVE_DIR, today_str)
    os.makedirs(archive_path, exist_ok=True)
    
    # 1. Generate Final Report Markdown
    report_content = run_report_scripts()
    report_file = os.path.join(archive_path, "Settlement_Report.md")
    with open(report_file, "w") as f:
        f.write(f"# Night Session Settlement Report - {today_str}\n\n")
        f.write(report_content)
    
    # 2. Copy to Obsidian for easy viewing
    obsidian_dest = os.path.join(OBSIDIAN_VAULT, f"{today_str}_NightSettlement.md")
    os.makedirs(os.path.dirname(obsidian_dest), exist_ok=True)
    shutil.copy2(report_file, obsidian_dest)
    
    # 3. Archive Intraday Batches
    batch_dest = os.path.join(archive_path, "Intraday_Batches")
    if os.path.exists(INTRADAY_BATCHES):
        shutil.copytree(INTRADAY_BATCHES, batch_dest, dirs_exist_ok=True)
        print(f"Archived intraday batches to {batch_dest}")
    
    print(f"Settlement complete. Report saved to {report_file} and Obsidian.")

if __name__ == "__main__":
    archive_settlement()
