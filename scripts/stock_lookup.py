#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

DATA_DIR = "/Users/bookid/.hermes/data"
TODAY_MAP_PATH = os.path.join(DATA_DIR, "stock_map_today.json")
LOG_PATH = os.path.join(DATA_DIR, "stock_mapping_calibration_log.json")

def send_telegram_alert(message):
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
            requests.post(url, json=payload, timeout=10)
        except:
            pass

def fetch_live_online_stocks():
    # Crawl live lists from TWSE & TPEx (using cp950)
    valid_categories = {"股票", "特別股", "創新板", "ETF", "臺灣存託憑證(TDR)", "受益證券-不動產投資信託"}
    stocks = {}
    for mode in [2, 4]:
        url = f"https://isin.twse.com.tw/isin/C_public.jsp?strMode={mode}"
        try:
            resp = requests.get(url, timeout=15)
            resp.encoding = 'cp950'
            soup = BeautifulSoup(resp.text, 'html.parser')
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
                        parts = text.split('\u3000')
                        if len(parts) == 2:
                            code, name = parts[0].strip(), parts[1].strip()
                            if 4 <= len(code) <= 6:
                                stocks[code] = name
        except Exception as e:
            print(f"Live fetch error: {e}", file=sys.stderr)
    return stocks

def log_lookup_error(query, matched_code, matched_name):
    # Log this missing stock to calibration log under "history"
    error_msg = f"查詢 '{query}' 本地未命中，但經確認在線：股號 {matched_code} 股名 {matched_name}"
    print(f"⚠️ {error_msg}", file=sys.stderr)
    
    # Send TG Alert
    alert_msg = f"🚨 *Hermes 查詢未命中校準警報* 🚨\n\n"
    alert_msg += f"用戶查詢 `{query}`，本地對照表無此資料。\n"
    alert_msg += f"隨後經線上即時檢驗確認該股在線：\n"
    alert_msg += f"• 股號：`{matched_code}`\n"
    alert_msg += f"• 股名：`{matched_name}`\n\n"
    alert_msg += f"👉 系統已自動將其計入今日 Calibration Error 並排入校正清單。"
    send_telegram_alert(alert_msg)
    
    # Write to log
    history = []
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                log_data = json.load(f)
                history = log_data.get("history", [])
        except Exception as e:
            print(f"Error loading log history: {e}", file=sys.stderr)
            
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Find if there is an existing entry for today
    today_entry = None
    for entry in history:
        if entry.get("date") == today_str:
            today_entry = entry
            break
            
    if today_entry is None:
        today_entry = {
            "date": today_str,
            "timestamp": datetime.now().isoformat(),
            "total_stocks": 2350,
            "error_count": 0,
            "errors": [],
            "mismatches": [],
            "disappeared": []
        }
        history.append(today_entry)
        
    # Append error if not already in the list
    if error_msg not in today_entry["errors"]:
        today_entry["errors"].append(error_msg)
        
    today_entry["error_count"] = len(today_entry["errors"])
    today_entry["timestamp"] = datetime.now().isoformat()
    
    try:
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            json.dump({"history": history}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving log history: {e}", file=sys.stderr)

def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "error",
            "message": "使用方法: python stock_lookup.py <股名或股號> [--json]",
            "formatted_text": "❌ *使用方法錯誤*\n\n請輸入 `python stock_lookup.py <股名或股號>`"
        }, ensure_ascii=False))
        sys.exit(1)
        
    query = sys.argv[1].strip()
    if not query:
        print(json.dumps({
            "status": "error",
            "message": "❌ 查詢欄位不能為空。",
            "formatted_text": "❌ *查詢欄位不能為空。*"
        }, ensure_ascii=False))
        sys.exit(1)
        
    output_only_json = "--json" in sys.argv
    
    # Load today map
    today_map = {}
    if os.path.exists(TODAY_MAP_PATH):
        try:
            with open(TODAY_MAP_PATH, "r", encoding="utf-8") as f:
                today_map = json.load(f)
        except Exception as e:
            print(f"Error loading stock_map_today.json: {e}", file=sys.stderr)
            
    # Search locally
    local_matches = []
    
    # 1. Exact code match
    if query in today_map:
        local_matches.append({"code": query, "name": today_map[query]})
    else:
        # 2. Exact name match (case-insensitive)
        for code, name in today_map.items():
            if name.lower() == query.lower():
                local_matches.append({"code": code, "name": name})
                
        # 3. Partial match (if no exact name match)
        if not local_matches:
            for code, name in today_map.items():
                if query.lower() in name.lower() or name.lower() in query.lower() or query in code:
                    local_matches.append({"code": code, "name": name})

    # If found locally
    if local_matches:
        if len(local_matches) == 1:
            code = local_matches[0]["code"]
            name = local_matches[0]["name"]
            fmt_text = f"📈 *Hermes 股票查詢成功 (本地對照表)*\n\n• *股票代號*：`{code}`\n• *股票名稱*：`{name}`"
            res = {
                "status": "success",
                "source": "local",
                "code": code,
                "name": name,
                "matches": local_matches,
                "formatted_text": fmt_text
            }
        else:
            # Multiple matches
            fmt_text = f"🔍 *Hermes 股票模糊搜尋結果 (共 {len(local_matches)} 筆)*\n\n為您找到符合「{query}」的股票清單：\n"
            for i, match in enumerate(local_matches[:15], 1):
                fmt_text += f"{i}. `{match['code']}` - *{match['name']}*\n"
            if len(local_matches) > 15:
                fmt_text += f"\n_...以及其他 {len(local_matches) - 15} 個搜尋結果。_\n"
            fmt_text += "\n💡 _提示：您可以使用更精確的股名或股號進行查詢。_"
            
            res = {
                "status": "success",
                "source": "local",
                "matches": local_matches,
                "formatted_text": fmt_text
            }
            
        if output_only_json:
            print(json.dumps(res, ensure_ascii=False))
        else:
            print(fmt_text)
        sys.exit(0)
        
    # Not found in local list. Perform live online confirmation.
    print(f"🔍 本地對照表未命中 '{query}'，正啟動線上即時確認...", file=sys.stderr)
    live_stocks = fetch_live_online_stocks()
    
    live_matches = []
    
    # 1. Exact code in live
    if query in live_stocks:
        live_matches.append({"code": query, "name": live_stocks[query]})
    else:
        # 2. Exact name in live
        for code, name in live_stocks.items():
            if name.lower() == query.lower():
                live_matches.append({"code": code, "name": name})
                
        # 3. Partial name in live
        if not live_matches:
            for code, name in live_stocks.items():
                if query.lower() in name.lower() or name.lower() in query.lower() or query in code:
                    live_matches.append({"code": code, "name": name})
                    
    if live_matches:
        # Confirmed online! Log as error for each match.
        for match in live_matches:
            log_lookup_error(query, match["code"], match["name"])
            
        if len(live_matches) == 1:
            code = live_matches[0]["code"]
            name = live_matches[0]["name"]
            fmt_text = f"🚨 *Hermes 股票線上確認 (已列入校準誤差)*\n\n本地對照表未命中「{query}」，但經線上即時檢驗確認該股在線：\n• *股票代號*：`{code}`\n• *股票名稱*：`{name}`\n\n👉 _系統已自動將此資料計入今日 Calibration Error 並發送警報。_"
            res = {
                "status": "success",
                "source": "live_calibrated",
                "code": code,
                "name": name,
                "matches": live_matches,
                "warning": "本地未命中但線上確認在線，已自動列入 Calibration Error。",
                "formatted_text": fmt_text
            }
        else:
            # Multiple matches confirmed online
            fmt_text = f"🚨 *Hermes 股票線上確認 (已列入校準誤差)*\n\n本地對照表未命中「{query}」，但經線上即時檢驗確認以下 {len(live_matches)} 檔股票在線：\n"
            for i, match in enumerate(live_matches[:15], 1):
                fmt_text += f"{i}. `{match['code']}` - *{match['name']}*\n"
            if len(live_matches) > 15:
                fmt_text += f"\n_...以及其他 {len(live_matches) - 15} 個搜尋結果。_\n"
            fmt_text += "\n👉 _系統已自動將上述資料計入今日 Calibration Error 並發送警報。_"
            
            res = {
                "status": "success",
                "source": "live_calibrated",
                "matches": live_matches,
                "warning": "本地未命中但線上確認在線，已自動列入 Calibration Error。",
                "formatted_text": fmt_text
            }
            
        if output_only_json:
            print(json.dumps(res, ensure_ascii=False))
        else:
            print(fmt_text)
        sys.exit(0)
    else:
        # Confirmed offline
        fmt_text = f"❌ *Hermes 查詢失敗*\n\n在本地對照表與線上手冊中，皆找不到「{query}」的股票或 ETF。\n請確認輸入是否正確（如：確認是否已下市或輸入錯誤）。"
        res = {
            "status": "failed",
            "message": f"在本地與線上皆找不到 '{query}' 的股票或 ETF。",
            "formatted_text": fmt_text
        }
        if output_only_json:
            print(json.dumps(res, ensure_ascii=False))
        else:
            print(fmt_text)
        sys.exit(1)

if __name__ == "__main__":
    main()
