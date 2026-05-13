#!/usr/bin/env python3
import os
import sys
import subprocess
import glob
import shutil
from pathlib import Path

HERMES_DIR = Path.home() / ".hermes"
SKILLS_DIR = HERMES_DIR / "skills"

HERMES_AGENT_DIR = Path.home() / "workspace" / "hermes-agent"

def print_header(title):
    print(f"\n\033[1;36m=== {title} ===\033[0m")

def print_result(name, ok, msg):
    status = "\033[1;32m✅\033[0m" if ok else "\033[1;31m❌\033[0m"
    print(f"  {status} {name}: {msg}")

def check_apple_permission(app_name, test_script):
    try:
        result = subprocess.run(["osascript", "-e", test_script], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return True, "\033[32mOK (Authorized)\033[0m"
        elif "Not authorized" in result.stderr:
            return False, f"\033[31mPermission Denied\033[0m (Check System Settings -> Privacy & Security -> Automation)"
        else:
            return False, f"Error: {result.stderr.strip()}"
    except Exception as e:
        return False, str(e)

def check_python_module(module_name):
    # Try using the hermes-agent venv python if available
    venv_python = HERMES_AGENT_DIR / "venv" / "bin" / "python"
    py_exec = str(venv_python) if venv_python.exists() else sys.executable
    try:
        subprocess.run([py_exec, "-c", f"import {module_name}"], check=True, capture_output=True)
        return True, "\033[32mInstalled\033[0m"
    except subprocess.CalledProcessError:
        return False, "\033[31mMissing\033[0m (run: ~/workspace/hermes-agent/venv/bin/pip install " + module_name + ")"

def check_file_exists(file_path):
    path = Path(os.path.expanduser(file_path))
    if path.exists():
        return True, f"\033[32mFound\033[0m ({path})"
    return False, f"\033[31mNot Found\033[0m ({path})"

def check_env_var(var_name):
    env_paths = [HERMES_DIR / ".env", HERMES_AGENT_DIR / ".env"]
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path, "r") as f:
                if f"{var_name}=" in f.read():
                    return True, f"\033[32mConfigured in {env_path.name}\033[0m"
    if var_name in os.environ:
        return True, "\033[32mConfigured in ENV\033[0m"
    return False, "\033[31mMissing\033[0m"

def check_command_exists(cmd):
    if shutil.which(cmd):
        return True, "\033[32mFound in PATH\033[0m"
    return False, f"\033[31mCommand '{cmd}' not found\033[0m"

def main():
    print("\n\033[1;35m🚀 Hermes Skill Health & Permission Inspector 🚀\033[0m")
    
    print_header("Core Permissions (Apple Automation)")
    ok, msg = check_apple_permission("Calendar", 'tell application "Calendar" to get name of first calendar')
    print_result("Apple Calendar", ok, msg)
    
    ok, msg = check_apple_permission("Mail", 'tell application "Mail" to get account 1')
    print_result("Apple Mail", ok, msg)
    
    ok, msg = check_apple_permission("Numbers", 'tell application "Numbers" to get name of document 1')
    print_result("Apple Numbers", ok, msg)

    print_header("Finance Skill Resources")
    ok, msg = check_python_module("yfinance")
    print_result("yfinance package", ok, msg)
    
    ok, msg = check_python_module("pandas")
    print_result("pandas package", ok, msg)
    
    ok, msg = check_file_exists("~/Documents/StockTracking_Daily.numbers")
    print_result("Daily Numbers Tracking", ok, msg)

    print_header("API & Gateway Connectivity")
    ok, msg = check_env_var("OPENAI_API_KEY")
    print_result("OpenAI API Key", ok, msg)
    
    ok, msg = check_env_var("ANTHROPIC_API_KEY")
    print_result("Anthropic API Key", ok, msg)
    
    ok, msg = check_env_var("TELEGRAM_BOT_TOKEN")
    print_result("Telegram Bot Token", ok, msg)

    print_header("System Resources & Dependencies")
    ok, msg = check_command_exists("git")
    print_result("Git Version Control", ok, msg)
    
    ok, msg = check_command_exists("python3")
    print_result("Python Runtime", ok, msg)
    
    # Check all installed skills count
    skill_files = glob.glob(str(SKILLS_DIR / "**" / "SKILL.md"), recursive=True)
    print(f"\n\033[1;34m[ℹ] Total Installed Skills Detected: {len(skill_files)}\033[0m")
    
    print("\n\033[1;30mTip: If any Apple Automation shows 'Permission Denied', go to:\033[0m")
    print("\033[1;30mSystem Settings -> Privacy & Security -> Automation\033[0m")
    print("\033[1;30mand ensure your Terminal/iTerm/Python is checked for the respective app.\033[0m\n")

if __name__ == '__main__':
    main()
