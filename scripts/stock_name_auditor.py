#!/Users/bookid/.hermes/.venv/bin/python
import os
import json
import urllib.request
import urllib.parse
import ssl

DATA_DIR = os.path.expanduser("~/.hermes/data")
REGISTRY_FILE = os.path.join(DATA_DIR, "master_stock_registry.json")

# Use Star Platinum token for the auditor alerts
SP_TOKEN = "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU"
JOJO_CHAT_ID = "6326497055"

def send_alert(msg):
    url = f"https://api.telegram.org/bot{SP_TOKEN}/sendMessage"
    ctx = ssl._create_unverified_context()
    data = urllib.parse.urlencode({'chat_id': JOJO_CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'}).encode('utf-8')
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, context=ctx, timeout=5)
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

def fetch_twse_names(codes):
    official_names = {}
    ctx = ssl._create_unverified_context()
    for i in range(0, len(codes), 50):
        chunk = codes[i:i+50]
        query = "|".join([f"tse_{c}.tw" for c in chunk] + [f"otc_{c}.tw" for c in chunk])
        url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={query}&json=1&delay=0"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if "msgArray" in data:
                    for item in data["msgArray"]:
                        c = item.get("c")
                        n = item.get("n", "")
                        if c and n:
                            clean_name = n.replace(" ", "").replace("股份有限公司", "").strip()
                            official_names[c] = clean_name
        except Exception as e:
            print(f"Error fetching chunk from TWSE: {e}")
    return official_names

def run_audit(auto_heal=False):
    if not os.path.exists(REGISTRY_FILE):
        print("❌ Registry file not found.")
        return False
        
    with open(REGISTRY_FILE, 'r') as f:
        registry = json.load(f)
        
    old_names = registry.get("official_names", {})
    all_codes = list(old_names.keys())
    
    print(f"🔍 正在稽核 {len(all_codes)} 檔股票名稱 (TWSE Official Names)...")
    new_names = fetch_twse_names(all_codes)
    
    mismatches = []
    for c in all_codes:
        if c in new_names:
            if new_names[c] != old_names[c]:
                # Exclude trivial format differences (like appended ETF identifiers) unless it's completely wrong
                # But since the user wants 100% strict match, we append all mismatches
                mismatches.append((c, old_names[c], new_names[c]))
                
    if not mismatches:
        print("✅ [股名/股號一致性] 100% PASS")
        return True
        
    print(f"⚠️ 發現 {len(mismatches)} 筆名稱不一致！")
    for c, old, new in mismatches:
        print(f"  - {c}: '{old}' -> '{new}'")
        
    if auto_heal:
        msg_lines = ["⚠️ **[自我修復] 股名稽核更新**\n"]
        msg_lines.append("系統偵測到以下股票名稱與證交所官方登記不符，已自動校正：\n")
        
        for c, old, new in mismatches:
            registry["official_names"][c] = new
            msg_lines.append(f"• `{c}`: {old} ➜ **{new}**")
            
        with open(REGISTRY_FILE, 'w') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
            
        send_alert("\n".join(msg_lines))
        print("✅ 修復完成，已更新 registry 並發送 Telegram 通知。")
        return True
    
    return False

if __name__ == "__main__":
    import sys
    auto = "--auto-heal" in sys.argv
    success = run_audit(auto_heal=auto)
    sys.exit(0 if success else 1)
