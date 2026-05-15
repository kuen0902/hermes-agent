import json
import uuid
import os
from datetime import datetime
import sys

# Ensure we have pytz
try:
    import pytz
except ImportError:
    print("pytz missing. Auto-installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytz"])
    import pytz

jobs_file = os.path.expanduser("~/.hermes/cron/jobs.json")

try:
    with open(jobs_file, "r") as f:
        data = json.load(f)
except Exception as e:
    print(f"Error loading jobs.json: {e}")
    sys.exit(1)

# Check if already installed
for job in data.get("jobs", []):
    if job.get("name") == "Night Session Tiered Monitor":
        print("Cron job already exists in jobs.json!")
        sys.exit(0)

new_job = {
  "id": str(uuid.uuid4())[:12],
  "name": "Night Session Tiered Monitor",
  "prompt": None,
  "skills": [],
  "skill": None,
  "model": None,
  "provider": None,
  "base_url": None,
  "script": "/Users/bookid/.hermes/scripts/night_session_threshold_monitor.py",
  "no_agent": True,
  "context_from": None,
  "schedule": {
    "kind": "cron",
    "expr": "*/5 15-23,0-5 * * *",
    "display": "*/5 15-23,0-5 * * *"
  },
  "schedule_display": "*/5 15-23,0-5 * * *",
  "repeat": {
    "times": None,
    "completed": 0
  },
  "enabled": True,
  "state": "scheduled",
  "paused_at": None,
  "paused_reason": None,
  "created_at": datetime.now(pytz.timezone("Asia/Taipei")).isoformat(),
  "next_run_at": None,
  "last_run_at": None,
  "last_status": None,
  "last_error": None,
  "last_delivery_error": None,
  "deliver": "local",
  "origin": {
    "platform": "telegram",
    "chat_id": "6326497055",
    "chat_name": "Jojo",
    "thread_id": None
  },
  "enabled_toolsets": [],
  "workdir": None
}

data.setdefault("jobs", []).append(new_job)

with open(jobs_file, "w") as f:
    json.dump(data, f, indent=2)

print("✅ Successfully added 'Night Session Tiered Monitor' to jobs.json (runs every 5 mins).")
