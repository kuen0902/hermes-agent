#!/usr/bin/env python3
import json
import subprocess
import sys

def run_script_output(path):
    try:
        result = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=10)
        return result.stdout.strip() if result.returncode == 0 else ""
    except:
        return ""

# Get outputs
print("="*60)
print("🌙 台股夜盤監控 - 聚合報告 (Night Session Aggregated Report)")
print("="*60)

# Load bridge data for context
bridge_path = "/Users/bookid/.hermes/data/market_prices_bridge.json"
with open(bridge_path, 'r') as f:
    bridge = json.load(f)

print(f"\n📅 報告時間：{bridge.get('timestamp', 'N/A')}")
print(f"📊 資料來源：Web 爬取 (yfinance 速率限制，使用 Resilient Bridge 機制)")

print("\n" + "-"*60)
print("📈 ADR/領先指標 (tw_night_monitor_adri.py)")
print("-"*60)
adri_output = run_script_output("/Users/bookid/.hermes/scripts/tw_night_monitor_adri.py")
if adri_output:
    print(adri_output)
else:
    print("[SILENT] - 未有階梯突破觸發 (無門檻突破)")

print("\n" + "-"*60)
print("📊 台指期夜盤指標 (tw_night_session_hourly.py)")
print("-"*60)
futures_output = run_script_output("/Users/bookid/.hermes/scripts/tw_night_session_hourly.py")
print(futures_output if futures_output else "無數據")

print("\n" + "-"*60)
print("💡 當前市場價格摘要")
print("-"*60)
prices = {
    "NQ": ("Nasdaq 100 期貨", bridge.get("NQ")),
    "TSM": ("台積電 ADR", bridge.get("TSM")),
    "NVDA": ("Nvidia", bridge.get("NVDA")),
    "SYNA": ("Synaptics", bridge.get("SYNA")),
    "FITXP": ("台指期 (夜)", bridge.get("FITXP"))
}

for ticker, (name, price) in prices.items():
    if price:
        if ticker in ["NQ", "FITXP"]:
            print(f"  {name} ({ticker}): {price:,.1f}")
        else:
            print(f"  {name} ({ticker}): ${price:.2f}")

print("\n" + "="*60)
print("📝 注意：當前為週六下午，台灣夜盤處於非交易時段")
print("   下次夜盤：週日 15:00 開始 (週一至週五 15:00 - 23:59)")
print("   或 週日 00:00-06:00 (週二至週六 00:00-06:00)")
print("="*60)
