import os

# Read the threshold monitor script
with open("/Users/bookid/.hermes/scripts/night_session_threshold_monitor.py", "r") as f:
    content = f.read()

# Highly aggressive thresholds for testing
content = content.replace("THRESHOLDS = [1.5, 3.0, 5.0]", "THRESHOLDS = [0.001, 3.0, 5.0]")
# Silence group in testing too
content = content.replace('TARGET_CHATS = ["6326497055", "-1003744330314"]', 'TARGET_CHATS = ["6326497055"]')

with open("/Users/bookid/.hermes/scripts/night_session_threshold_monitor_test.py", "w") as f:
    f.write(content)
