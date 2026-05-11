import os, json, datetime

LOG_FILE = os.path.expanduser("~/.hermes/tavily_local_log.json")

def record_usage(call_type="web_search"):
    # 預設配置
    config = {"base_value": 0, "calls": []}
    
    # 讀取現有紀錄
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                pass
    
    # 增加一筆紀錄
    config["calls"].append({
        "timestamp": datetime.datetime.now().isoformat(),
        "type": call_type
    })
    
    # 寫入檔案
    with open(LOG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    
    local_total = config["base_value"] + len(config["calls"])
    print(f"--- Tavily Step-Increment ---\nEvent: {call_type}\nLocal Total: {local_total}")

if __name__ == "__main__":
    import sys
    ctype = sys.argv[1] if len(sys.argv) > 1 else "web_search"
    record_usage(ctype)
