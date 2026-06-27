import sys

FILE_PATH = "/Users/bookid/.hermes/scripts/fetchers/sync_historical_5m.py"

with open(FILE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

replacement = """                elif r.status_code == 403:
                    try:
                        res_data = r.json()
                        if "banned" in str(res_data.get('msg', '')).lower():
                            retry_after = res_data.get('retry_after', 1800)
                            print(f"    ⏳ [FinMind API] 收到 HTTP 403 (IP Banned)，需冷卻 {retry_after} 秒，強制休眠...")
                            time.sleep(retry_after + 10)
                            print("    ⏰ 休眠結束，重試抓取！")
                            continue
                    except:
                        pass
                    print(f"    ⚠️ 從 FinMind 下載失敗 HTTP 403")
                    break"""

content = content.replace("""                else:
                    print(f"    ⚠️ 從 FinMind 下載失敗 HTTP {r.status_code}")
                    break""", replacement + """
                else:
                    print(f"    ⚠️ 從 FinMind 下載失敗 HTTP {r.status_code}")
                    break""")

with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print("FinMind 403 handling patched.")
