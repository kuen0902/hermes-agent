#!/usr/bin/env python3
import subprocess

def read_mail_batch(start, end):
    """
    Reads a specific range of emails from the default Inbox.
    Example: read_mail_batch(1, 5)
    """
    apple_script = f"""
    tell application "Mail"
        set output to ""
        set theMessages to messages of inbox
        set totalMessages to count of theMessages
        if totalMessages < {start} then
            return "Error: Only " + (totalMessages as string) + " messages available."
        end if
        set actualEnd to {end}
        if totalMessages < {end} then set actualEnd to totalMessages
        repeat with i from {start} to actualEnd
            set msg to item i of theMessages
            set output to output & i & ". [" & (subject of msg) & "] From: " & (sender of msg) & "\\n"
        end repeat
        return output
    end tell
    """
    process = subprocess.run(['osascript', '-e', apple_script], capture_output=True, text=True, check=True)
    return process.stdout

if __name__ == "__main__":
    # Update these numbers as needed
    print(read_mail_batch(1, 5))
