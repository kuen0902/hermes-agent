#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime

JOBS_FILE = os.path.expanduser("~/.hermes/cron/jobs.json")

def review_jobs():
    if not os.path.exists(JOBS_FILE):
        print(f"Error: jobs.json not found at {JOBS_FILE}")
        return

    with open(JOBS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    jobs = data.get("jobs", [])
    print("==========================================================================================")
    print(" 🛠️ HERMES CRON ENGINE: CURRENT ENABLED JOBS & RECENT EXECUTION REVIEW")
    print("==========================================================================================")
    
    header = f"{'Job Name':<45} | {'Expression':<12} | {'Last Run (Local)':<25} | {'Status':<8} | {'Error Details / Logs'}"
    print(header)
    print("-" * 125)

    for j in jobs:
        if not j.get("enabled", False):
            continue
        
        name = j.get("name") or j.get("id")
        expr = j.get("schedule", {}).get("expr") or "N/A"
        last_run = j.get("last_run_at") or "never"
        status = j.get("last_status") or "N/A"
        error = j.get("last_error") or ""
        
        # Format the last run time to be more human readable if it exists
        if last_run != "never":
            try:
                # e.g., 2026-05-26T15:02:33.278639+08:00
                dt = datetime.fromisoformat(last_run)
                last_run_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                last_run_str = last_run
        else:
            last_run_str = "never"
            
        # Truncate error for nice formatting
        if error:
            error_clean = error.replace("\n", " ").strip()
            if len(error_clean) > 45:
                error_clean = error_clean[:42] + "..."
        else:
            error_clean = "None"
            
        print(f"{name[:45]:<45} | {expr:<12} | {last_run_str:<25} | {status:<8} | {error_clean}")
    
    print("==========================================================================================")

if __name__ == "__main__":
    review_jobs()
