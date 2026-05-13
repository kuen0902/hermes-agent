import monitor_engine
import sys

if __name__ == "__main__":
    capture_only = "--report-only" in sys.argv
    monitor_engine.run("group", capture_only)
