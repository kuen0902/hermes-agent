#!/Users/bookid/.hermes/.venv/bin/python
# -*- coding: utf-8 -*-


import os
import re
import json
import requests
import sqlite3
import random
import time
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Any

# Define file paths within the workspace limits
DATA_DIR = "/Users/bookid/.hermes/data"
TODAY_MAP_PATH = os.path.join(DATA_DIR, "stock_map_today.json")
YESTERDAY_MAP_PATH = os.path.join(DATA_DIR, "stock_map_yesterday.json")
LOG_PATH = os.path.join(DATA_DIR, "stock_mapping_calibration_log.json")
ORIGINAL_MAPPING_PATH = os.path.join(DATA_DIR, "stock_mapping.json")

def fetch_all_active_stocks():
    """
    Fetch all active stocks and ETFs from TWSE and TPEx, excluding warrants, ETNs, etc.
    """
    valid_categories = {"股票", "特別股", "創新板", "ETF", "臺灣存託憑證(TDR)", "受益證券-不動產投資信託"}
    stocks = {}
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
    ]
    
    for mode in [2, 4]:
        url = f"https://isin.twse.com.tw/isin/C_public.jsp?strMode={mode}"
        max_retries = 3
        resp_text = ""
        
        for attempt in range(max_retries):
            try:
                headers = {'User-Agent': random.choice(user_agents)}
                print(f"Fetching active stocks from: {url} (Attempt {attempt+1})")
                resp = requests.get(url, headers=headers, timeout=20)
                if resp.status_code == 200:
                    resp.encoding = 'cp950'
                    resp_text = resp.text
                    break
            except Exception as e:
                print(f"Attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2.0)
                    
        if not resp_text:
            print(f"❌ 無法獲取 active stocks (mode={mode})，已達最大重試次數。")
            continue
            
        try:
            soup = BeautifulSoup(resp_text, 'html.parser')
            rows = soup.find_all('tr')
            
            current_category = None
            for r in rows:
                cols = r.find_all('td')
                if len(cols) == 1:
                    current_category = cols[0].get_text().strip()
                    continue
                
                if current_category in valid_categories:
                    if len(cols) > 0:
                        text = cols[0].get_text().strip()
                        # Formats can be "1101\u3000台泥"
                        parts = text.split('\u3000')
                        if len(parts) == 2:
                            code, name = parts[0].strip(), parts[1].strip()
                            if 4 <= len(code) <= 6:
                                stocks[code] = name
        except Exception as e:
            print(f"Error parsing active stocks (mode={mode}): {e}")
            
    return stocks

def load_yesterday_mapping():
    """
    Load yesterday's mapping. If not exists, fallback to flip the original stock_mapping.json.
    """
    if os.path.exists(YESTERDAY_MAP_PATH):
        try:
            with open(YESTERDAY_MAP_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading yesterday map: {e}")
            
    # Fallback to reverse stock_mapping.json (which is {"Name": "Code"})
    if os.path.exists(ORIGINAL_MAPPING_PATH):
        try:
            with open(ORIGINAL_MAPPING_PATH, "r", encoding="utf-8") as f:
                orig = json.load(f)
                reversed_map = {str(code).strip(): str(name).strip() for name, code in orig.items()}
                print(f"Fallback: Reversed {len(reversed_map)} stocks from stock_mapping.json as initial yesterday map.")
                return reversed_map
        except Exception as e:
            print(f"Error reading stock_mapping.json fallback: {e}")
            
    return {}

def send_telegram_alert(message):
    """
    Send a Telegram Markdown alert message to the user.
    """
    env_path = "/Users/bookid/.hermes/.env"
    token = None
    chat_id = None
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    token = line.split("=", 1)[1]
                elif line.startswith("TELEGRAM_HOME_CHANNEL="):
                    chat_id = line.split("=", 1)[1]
                    
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                print("Telegram notification sent successfully.")
            else:
                print(f"Failed to send Telegram alert: {resp.text}")
        except Exception as e:
            print(f"Error sending Telegram alert: {e}")
    else:
        print("Telegram token or channel ID not found in .env. Skipping Telegram alert.")

def load_portfolio_and_watchlist_codes():
    """載入持股與自選名單代碼，用於高優先級比對"""
    db_path = "/Users/bookid/.hermes/data/portfolio.db"
    core_codes = set()
    if not os.path.exists(db_path):
        return core_codes
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # 讀取持股
        cursor.execute("SELECT code FROM current_holdings")
        for row in cursor.fetchall():
            code = str(row[0]).replace(".TWO", "").replace(".TW", "").strip()
            core_codes.add(code)
        # 讀取自選名單
        cursor.execute("SELECT code FROM watchlist")
        for row in cursor.fetchall():
            code = str(row[0]).replace(".TWO", "").replace(".TW", "").strip()
            core_codes.add(code)
        conn.close()
    except Exception as e:
        print(f"無法讀取資料庫以提取核心股號: {e}")
    return core_codes

def calibrate_and_log():
    # Make sure directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # 1. Fetch current live stocks
    today_map = fetch_all_active_stocks()
    if not today_map:
        print("Error: Fetched 0 active stocks today. Calibration aborted to prevent false alerts.")
        return
        
    print(f"Successfully fetched {len(today_map)} active stocks today.")
    
    # 載入用戶個人持股與自選名單代碼
    core_user_codes = load_portfolio_and_watchlist_codes()
    print(f"載入用戶核心關聯商品（持股與自選）：{len(core_user_codes)} 檔。")
    
    # 2. Load yesterday's map for comparison
    yesterday_map = load_yesterday_mapping()
    
    # 3. Perform calibration & error calculation
    errors = []
    
    # Check for name mismatches (Error Category 1)
    mismatches = []
    for code, name in today_map.items():
        if code in yesterday_map:
            prev_name = yesterday_map[code]
            if name != prev_name:
                is_core = code in core_user_codes
                prefix = "🔥 [CRITICAL-持股/自選更名] " if is_core else ""
                mismatches.append({
                    "code": code,
                    "prev_name": prev_name,
                    "curr_name": name,
                    "reason": "Name mismatch (mismatch)"
                })
                errors.append(f"{prefix}股號 {code} 股名不一致: '{prev_name}' -> '{name}'")
                
    # Check for disappeared stock codes (Error Category 2)
    disappeared = []
    # Only report as error if the drop is not massive (which would be a fetch error)
    if len(today_map) >= len(yesterday_map) * 0.9:
        for code, name in yesterday_map.items():
            if code not in today_map:
                is_core = code in core_user_codes
                prefix = "🚨 [CRITICAL-持股/自選下市或停牌] " if is_core else ""
                disappeared.append({
                    "code": code,
                    "name": name,
                    "reason": "Disappeared from active list"
                })
                errors.append(f"{prefix}股號 {code} ({name}) 從在線名單中消失")
    else:
        # If total count dropped by more than 10%, it's a Fetch Drop Error
        errors.append(f"今日抓取股票數量異常暴跌！昨日 {len(yesterday_map)} 檔 -> 今日 {len(today_map)} 檔。")
        
    error_count = len(errors)
    
    # 4. Read history logs to compare errors
    history = []
    prev_error_count = 0
    today_str = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                log_data = json.load(f)
                history = log_data.get("history", [])
                
                # Find previous error count (latest entry strictly before today)
                for entry in reversed(history):
                    if entry.get("date") != today_str:
                        prev_error_count = entry.get("error_count", 0)
                        break
        except Exception as e:
            print(f"Error loading calibration log history: {e}")
            
    print(f"Comparison finished. Previous Error Count: {prev_error_count}, New Calibration Errors: {len(errors)}")
    
    # 5. Save/Merge current logs into history
    # Find if there is already an entry for today
    today_entry: Any = None
    for entry in history:
        if entry.get("date") == today_str:
            today_entry = entry
            break
            
    if today_entry is None:
        today_entry = {
            "date": today_str,
            "timestamp": datetime.now().isoformat(),
            "total_stocks": len(today_map),
            "error_count": 0,
            "errors": [],
            "mismatches": [],
            "disappeared": []
        }
        history.append(today_entry)
    else:
        # Update existing entry properties
        today_entry["total_stocks"] = len(today_map)
        today_entry["timestamp"] = datetime.now().isoformat()
        
    # Merge new errors (avoid duplicates)
    for err in errors:
        if err not in today_entry["errors"]:
            today_entry["errors"].append(err)
            
    # Merge mismatches
    for m in mismatches:
        if m not in today_entry["mismatches"]:
            today_entry["mismatches"].append(m)
            
    # Merge disappeared
    for d in disappeared:
        if d not in today_entry["disappeared"]:
            today_entry["disappeared"].append(d)
            
    today_entry["error_count"] = len(today_entry["errors"])
    error_count = today_entry["error_count"]
    
    # Keep only the last 90 days of logs to save space
    if len(history) > 90:
        history = history[-90:]
        
    try:
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            json.dump({"history": history}, f, ensure_ascii=False, indent=2)
        print(f"Saved calibration history to: {LOG_PATH}")
    except Exception as e:
        print(f"Error saving calibration log: {e}")
        
    # 6. Determine if we need to report (total error count increased)
    if error_count > prev_error_count:
        print("Alert! Error count increased. Sending Telegram alert.")
        alert_msg = f"🚨 *Hermes 股號股名對照校準警報* 🚨\n\n"
        alert_msg += f"系統偵測到股號股名對照誤差數有所增長！\n"
        alert_msg += f"• 前一日誤差數: `{prev_error_count}`\n"
        alert_msg += f"• 今日誤差數: `{error_count}` (增加 了 `{error_count - prev_error_count}`)\n"
        alert_msg += f"• 今日在線總檔數: `{len(today_map)}` 檔\n\n"
        alert_msg += f"*最近偵測到的誤差變動：*\n"
        
        # Display top 10 errors to keep Telegram message concise
        for err in today_entry["errors"][:10]:
            alert_msg += f"• {err}\n"
        if len(today_entry["errors"]) > 10:
            alert_msg += f"• _...以及其他 {len(today_entry['errors']) - 10} 個錯誤_\n"
            
        alert_msg += f"\n👉 請管理員立即確認是否為正常下市、更名，或網站格式異動！"
        send_telegram_alert(alert_msg)
        
    # 7. Update active mappings
    try:
        with open(TODAY_MAP_PATH, "w", encoding="utf-8") as f:
            json.dump(today_map, f, ensure_ascii=False, indent=2)
        with open(YESTERDAY_MAP_PATH, "w", encoding="utf-8") as f:
            json.dump(today_map, f, ensure_ascii=False, indent=2)
        print("Updated stock_map_today.json and stock_map_yesterday.json successfully.")
        
        # Sync stock names in DuckDB potential_analysis.ddb
        update_duckdb_stock_names(today_map)
        
        # Regenerate ML report and send to Telegram
        regenerate_potential_report()
        
    except Exception as e:
        print(f"Error saving mapping JSONs: {e}")

def update_duckdb_stock_names(today_map):
    """
    Update historical name fields in DuckDB potential_analysis.ddb
    to replace numeric codes/old names with proper names from today_map.
    """
    db_path = "/Users/bookid/.hermes/data/potential_analysis.ddb"
    if not os.path.exists(db_path):
        print(f"DuckDB database not found at {db_path}. Skipping DB names update.")
        return
        
    try:
        import duckdb
        print(f"Connecting to DuckDB to update stock names from calibration map...")
        conn = duckdb.connect(db_path)
        
        # Build maps of code -> set of current names in db to avoid redundant UPDATE queries
        conn.execute("BEGIN TRANSACTION;")
        
        updated_daily_count = 0
        updated_pred_count = 0
        
        daily_names = conn.execute("SELECT DISTINCT code, name FROM daily_stock_data").fetchall()
        pred_names = conn.execute("SELECT DISTINCT code, name FROM predictions").fetchall()
        
        daily_db_map = {}
        for code, name in daily_names:
            daily_db_map.setdefault(code, set()).add(name)
            
        pred_db_map = {}
        for code, name in pred_names:
            pred_db_map.setdefault(code, set()).add(name)
            
        # Update daily_stock_data
        for code, correct_name in today_map.items():
            if code in daily_db_map:
                existing_names = daily_db_map[code]
                if len(existing_names) > 1 or correct_name not in existing_names or any(name.isdigit() for name in existing_names):
                    conn.execute(
                        "UPDATE daily_stock_data SET name = ? WHERE code = ? AND (name = ? OR regexp_matches(name, '^[0-9]+$'))",
                        (correct_name, code, code)
                    )
                    updated_daily_count += 1
                    
        # Update predictions
        for code, correct_name in today_map.items():
            if code in pred_db_map:
                existing_names = pred_db_map[code]
                if len(existing_names) > 1 or correct_name not in existing_names or any(name.isdigit() for name in existing_names):
                    conn.execute(
                        "UPDATE predictions SET name = ? WHERE code = ? AND (name = ? OR regexp_matches(name, '^[0-9]+$'))",
                        (correct_name, code, code)
                    )
                    updated_pred_count += 1
                    
        conn.execute("COMMIT;")
        print(f"✓ DuckDB stock names update completed. Updated daily_stock_data for {updated_daily_count} codes, predictions for {updated_pred_count} codes.")
        conn.close()
    except Exception as e:
        print(f"❌ Failed to update DuckDB stock names: {e}")

def regenerate_potential_report():
    """
    Regenerate potential stocks report using the updated database names
    and send the updated report/chart to Telegram.
    """
    import subprocess
    print("--- Triggering ML Potential Stocks Report Regeneration ---")
    
    engine_script = "/Users/bookid/.hermes/scripts/ml/potential_stocks_engine.py"
    report_script = "/Users/bookid/.hermes/scripts/ml/generate_potential_report.py"
    venv_python = "/Users/bookid/.hermes/.venv/bin/python"
    
    if os.path.exists(engine_script) and os.path.exists(report_script):
        try:
            print("Running potential_stocks_engine.py...")
            res_eng = subprocess.run([venv_python, engine_script, "--inference-only"], capture_output=True, text=True, check=True)
            print("potential_stocks_engine.py output:")
            print(res_eng.stdout)
            
            print("Running generate_potential_report.py...")
            res_rep = subprocess.run([venv_python, report_script, "--send-telegram"], capture_output=True, text=True, check=True)
            print("generate_potential_report.py output:")
            print(res_rep.stdout)
            
            print("✓ Successfully regenerated and sent updated potential stocks report to Jojo!")
        except Exception as e:
            print(f"❌ Error regenerating potential stocks report: {e}")
            if hasattr(e, 'stdout') and e.stdout:
                print("Stdout:", e.stdout)
            if hasattr(e, 'stderr') and e.stderr:
                print("Stderr:", e.stderr)
    else:
        print("ML engine or report scripts not found. Skipping report regeneration.")

if __name__ == "__main__":
    calibrate_and_log()
