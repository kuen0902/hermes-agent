import os
import sys

# temporarily change threshold to 0.0 to trigger an alert immediately
with open("/Users/bookid/.hermes/scripts/night_session_threshold_monitor.py", "r") as f:
    content = f.read()

content = content.replace("THRESHOLDS = [1.5, 3.0, 5.0]", "THRESHOLDS = [0.001, 3.0, 5.0]")
content = content.replace('TARGET_CHATS = ["6326497055", "-1003744330314"]', 'TARGET_CHATS = ["6326497055"]')

with open("/Users/bookid/.hermes/scripts/night_session_threshold_monitor_test.py", "w") as f:
    f.write(content)

print("Test script generated.")
