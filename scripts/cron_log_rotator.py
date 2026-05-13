#!/usr/bin/env python3
import os
import time
from pathlib import Path

# Delete logs older than 21 days
DAYS = 21
RETENTION_SECONDS = DAYS * 86400

hermes_dir = Path.home() / ".hermes" / "cron" / "output"
if not hermes_dir.exists():
    print("Cron output directory does not exist. Exiting.")
    exit(0)

now = time.time()
deleted_count = 0
deleted_size = 0

for root, _, files in os.walk(hermes_dir):
    for file in files:
        if file.endswith(".md"):
            file_path = Path(root) / file
            # Check modification time
            if now - file_path.stat().st_mtime > RETENTION_SECONDS:
                deleted_size += file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1

print(f"Log Rotation Complete:")
print(f"- Target: Older than {DAYS} days")
print(f"- Deleted Files: {deleted_count}")
print(f"- Reclaimed Space: {deleted_size / 1024:.2f} KB")
