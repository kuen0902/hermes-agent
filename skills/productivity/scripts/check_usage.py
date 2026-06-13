import os, json, urllib.request

LOG_FILE = os.path.expanduser("~/.hermes/tavily_local_log.json")

def check_usage():
    # 1. 讀取 API 最新數據
    api_used = 0
    key = ""
    try:
        env_path = os.path.expanduser("~/.hermes/.env")
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("TAVILY_API_KEY="):
                    key = line.split("=")[1].strip().strip('"').strip("'")
        url = "https://api.tavily.com/usage"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {key}")
        with urllib.request.urlopen(req) as resp:
            u_data = json.loads(resp.read().decode())
            api_used = u_data.get("account", {}).get("plan_usage", 0)
    except:
        pass

    # 2. 獲取本地記錄
    config = {"base_value": 21, "calls": []}
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            config = json.load(f)
    
    # 2.1 每次檢查時記錄一次調用 (由用戶要求：每次 check 至少 +1)
    import datetime
    config["calls"].append({"timestamp": datetime.datetime.now().isoformat(), "type": "usage_check"})
    with open(LOG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    local_base = config["base_value"]
    local_increment = len(config["calls"])
    local_total = local_base + local_increment
    
    # 3. 對帳邏輯 (Reconciliation)
    status = ""
    sync_needed = False

    # 邏輯 A: 系統歸零偵測 (API = 0, 本地有積壓)
    if api_used == 0 and local_total > 5:
        config["base_value"] = 0
        config["calls"] = []
        sync_needed = True
        status = "RESET (System Zeroed, Local Synced)"
    
    # 邏輯 B: 官方數據領先 (本地漏記或 API 同步更新)
    elif api_used > local_total:
        config["base_value"] = api_used
        config["calls"] = []
        sync_needed = True
        status = "SYNCED (Official Data Leading, Local Updated)"
    
    # 邏輯 C: 本地領先或持平 (正常延遲狀態)
    elif api_used == local_total:
        status = "PERFECT (System Synced)"
    else:
        status = "LAGGING (API out of sync)"

    if sync_needed:
        with open(LOG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        local_total = config["base_value"]


    print(f"--- Tavily Managed Usage Report (v3.1) ---")
    print(f"Status: {status}")
    print(f"-------------------------------------------")
    print(f"API Returned Value: {api_used}")
    print(f"Local Recorded Value: {local_total}")
    print(f"-------------------------------------------")
    print(f"Final Counted Usage: {local_total} / 1000")
    print(f"Remaining Credits: {1000 - local_total}")
    print(f"-------------------------------------------")

if __name__ == "__main__":
    check_usage()
