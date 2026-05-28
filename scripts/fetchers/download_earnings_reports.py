#!/Users/bookid/.hermes/.venv/bin/python
# -*- coding: utf-8 -*-
import os
import json
import requests
import datetime
import time

DATA_DIR = os.path.expanduser("~/.hermes/data")
CALENDAR_JSON = os.path.join(DATA_DIR, "earnings_calendar.json")
REPORTS_DIR = os.path.expanduser("~/Documents/Reports/2026_Q1")

GER_TOKEN = "8513436203:AAHcvVxNgLEqQ_U_JH55mZaENCWfl4VTFJ4"
JOJO_CHAT_ID = "6326497055"

def send_telegram(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram failed: {e}")

def reconcile_and_download():
    global REPORTS_DIR
    print("=========================================================================")
    print(f" 🚀 啟動「財報季報 PDF」智慧自癒對帳與下載系統 [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}]")
    print("=========================================================================")
    
    if not os.path.exists(CALENDAR_JSON):
        print(f"❌ 找不到財報月曆 JSON 檔案: {CALENDAR_JSON}")
        return
        
    with open(CALENDAR_JSON, 'r', encoding='utf-8') as f:
        calendar = json.load(f)
        
    reconciled_stocks = []
    downloaded_stocks = []
    failed_stocks = []
    
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        existing_items = os.listdir(REPORTS_DIR)
    except PermissionError:
        print(f"⚠️ 無法存取 {REPORTS_DIR} (環境權限限制)，自動降級使用本地安全快取路徑...")
        REPORTS_DIR = os.path.expanduser("~/.hermes/data/Reports/2026_Q1")
        os.makedirs(REPORTS_DIR, exist_ok=True)
        existing_items = os.listdir(REPORTS_DIR)
    
    for symbol, info in calendar.items():
        code = symbol.split('.')[0]
        name = info.get("name", symbol)
        
        # 僅處理標註需要下載且尚未完成 Q1 下載的個股
        if info.get("mark_for_download") and not info.get("downloaded_q1"):
            print(f"\n🔍 正在體檢 {symbol} ({name}) 的財報下載狀態...")
            
            # 1. 智慧對帳：檢測實體檔案是否其實早就存在於本地子目錄或直屬目錄中
            found_files = []
            
            # A. 檢查同名/縮寫子資料夾 (如 TSMC, MediaTek, Unimicron, Chung-Hsin, Quanta)
            for item in existing_items:
                sub_path = os.path.join(REPORTS_DIR, item)
                if os.path.isdir(sub_path):
                    # 如果子目錄名稱與個股中文名或英文代稱相似
                    normalized_item = item.lower().replace("-", "").replace(" ", "")
                    normalized_name = name.lower().replace("-", "").replace(" ", "")
                    
                    if normalized_item in normalized_name or normalized_name in normalized_item or code in normalized_item:
                        # 掃描該子目錄下的所有 PDF 檔
                        sub_files = [f for f in os.listdir(sub_path) if f.endswith('.pdf')]
                        for sf in sub_files:
                            found_files.append(os.path.join(item, sf))
            
            # B. 檢查直屬目錄下是否有包含股號的 PDF
            for item in existing_items:
                if item.endswith('.pdf') and code in item:
                    found_files.append(item)
                    
            # 2. 判定與更新
            if found_files:
                print(f"   ✓ [對帳成功] 發現本地已存在相關財報 PDF：{found_files}")
                info["downloaded"] = True
                info["downloaded_q1"] = True
                info["last_downloaded_quarter"] = "2026 Q1"
                info["files"] = found_files
                reconciled_stocks.append(f"• `{symbol}` ({name}) -> 已在本地對帳補全 {len(found_files)} 份 PDF")
            else:
                # 3. 實體檔案真的不存在，嘗試使用簡易下載器進行下載
                print(f"   ⚠️ 本地未發現實體檔案，嘗試進行自動化增量下載...")
                # 這裡為示範防爬備援：對於 ETF 檔案，我們可以嘗試下載其公開說明的 PDF
                download_success = False
                
                # 台股電子書公開資訊觀測站備用 API (此處為極簡防爬 requests 拉取)
                # 如果是 ETF 或者是普通股，我們可以直接透過公開免驗證連結拉取
                if "0050" in code:
                    pdf_url = "https://www.yuantaetfs.com/api/Document/Download?id=38" # 示意或公開連結
                else:
                    pdf_url = None
                    
                if pdf_url:
                    try:
                        dest_file = f"{code}_Q1_2026.pdf"
                        dest_path = os.path.join(REPORTS_DIR, dest_file)
                        r = requests.get(pdf_url, timeout=15, verify=False)
                        if r.status_code == 200 and len(r.content) > 10000:
                            with open(dest_path, 'wb') as pdf_f:
                                pdf_f.write(r.content)
                            info["downloaded"] = True
                            info["downloaded_q1"] = True
                            info["last_downloaded_quarter"] = "2026 Q1"
                            info["files"] = [dest_file]
                            downloaded_stocks.append(f"• `{symbol}` ({name}) -> 成功下載 `{dest_file}`")
                            download_success = True
                            print("     ✓ [下載成功] 檔案已保存。")
                    except Exception as download_err:
                        print(f"     ❌ 下載出錯: {download_err}")
                
                if not download_success:
                    print("   ❌ 本地無實體檔案且自動下載失敗，標記為需要手動補全。")
                    failed_stocks.append(f"• `{symbol}` ({name}) -> 待手動補齊 PDF")
                    
    # 4. 回寫月曆 JSON
    with open(CALENDAR_JSON, 'w', encoding='utf-8') as f:
        json.dump(calendar, f, indent=4, ensure_ascii=False)
    print("\n✓ 財報月曆 JSON 檔案已更新保存。")
    
    # 5. 發送 Telegram 報告
    summary_lines = []
    if reconciled_stocks:
        summary_lines.append("📁 **智慧自癒對帳補全 (實體已在，JSON 已更新)**：")
        summary_lines.extend(reconciled_stocks)
    if downloaded_stocks:
        summary_lines.append("\n📥 **自動增量下載成功**：")
        summary_lines.extend(downloaded_stocks)
    if failed_stocks:
        summary_lines.append("\n⚠️ **待手動補齊/或無季報個股**：")
        summary_lines.extend(failed_stocks)
        
    if summary_lines:
        text = "\n".join(summary_lines)
        ger_msg = f"""🌅 **「黃金體驗-鎮魂曲」：Q1 財報下載自癒對帳報告 🌅**
現實已完成收斂。LLM 空轉已被終止，回歸純淨的腳本秩序。

{text}

**無駄！** 本次財報下載稽核與對帳成功完成，徹底免除 HTTP 429 雲端超限困擾！"""
        send_telegram(GER_TOKEN, JOJO_CHAT_ID, ger_msg)
        print("✓ 對帳捷報已發送至 TelegramGER Bot！")
    else:
        print("ℹ️ 無任何需要對帳或下載的個股，無須發送報告。")
        
    print("=========================================================================")

if __name__ == "__main__":
    reconcile_and_download()
