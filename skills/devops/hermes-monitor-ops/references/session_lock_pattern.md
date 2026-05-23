# Python Lock Pattern for Deduplication

Simple file-based lock mechanism to prevent duplicate execution of scripts within a short time window. Use this for automated Telegram bots or data crawlers.

```python
import os
import time
import sys

LOCK_FILE = os.path.expanduser("~/.hermes/data/my_script.lock")
THRESHOLD_SECONDS = 120 # 2 minutes

def check_lock():
    """Returns True if the script should proceed, False if it's a duplicate."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'r') as f:
                last_run = float(f.read().strip())
                # prevent duplicate execution within threshold
                if time.time() - last_run < THRESHOLD_SECONDS:
                    return False
        except (ValueError, OSError):
            pass # corrupted lock file, ignore and overwrite
    
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    with open(LOCK_FILE, 'w') as f:
        f.write(str(time.time()))
    return True

def main():
    if not check_lock():
        if "--verbose" in sys.argv:
            print("[SILENT] Duplicate execution detected. Exiting.")
        return
    
    # ... logic here ...
    print("Action performed.")

if __name__ == "__main__":
    main()
```

## Considerations
1. **Scope**: Use unique lock file names per script.
2. **Threshold**: 120 seconds is usually sufficient for cron overlaps or agent retries.
3. **Permissions**: Ensure the script has write access to the lock file directory.
