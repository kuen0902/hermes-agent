import os, json, datetime

LOG_FILE = os.path.expanduser("~/.hermes/tavily_local_log.json")

def log_call(query):
    # 初始化日誌
    if not os.path.exists(LOG_FILE):
        data = {"last_api_sync_value": 7, "calls": []}
    else:
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
    
    # 增加紀錄
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "query": query[:50] + "...",
        "estimated_cost": 1
    }
    data["calls"].append(entry)
    
    with open(LOG_FILE, "wb") as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8'))

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        log_call(sys.argv[1])
