#!/usr/bin/env python3
"""
Night Session Report Generator - Standalone Report
Generates a report even when night session gatekeeper returns inactive
"""

import json
import os
import pytz
from datetime import datetime

# Load bridge data
bridge_path = "/Users/bookid/.hermes/data/market_prices_bridge.json"
data = {}
if os.path.exists(bridge_path):
    with open(bridge_path, 'r') as f:
        data = json.load(f)

# Extract prices
prices = {
    "NQ": data.get("NQ"),
    "TSM": data.get("TSM"),
    "NVDA": data.get("NVDA"),
    "SYNA": data.get("SYNA"),
    "FITXP": data.get("FITXP")
}

timestamp = data.get("timestamp", "Unknown")

# Generate report
taipei_tz = pytz.timezone('Asia/Taipei')
report_time = datetime.now(taipei_tz).strftime("%Y-%m-%d %H:%M")

report = []
report.append("=" * 50)
report.append("📊 台股夜盤監偵 市場價格報告")
report.append("=" * 50)
report.append(f"🕐 報告時間：{report_time}")
report.append(f"📅 日期：{datetime.now(taipei_tz).strftime('%Y-%m-%d')} ({datetime.now(taipei_tz).strftime('%A')})")
report.append("-" * 50)

# Check if night session is active
def is_night_session_active():
    weekday = datetime.now(taipei_tz).weekday()
    hour = datetime.now(taipei_tz).hour
    if 0 <= weekday <= 4:
        if hour >= 15:
            return True
    if 1 <= weekday <= 5:
        if hour < 6:
            return True
    return False

if not is_night_session_active():
    report.append("")
    report.append("⚠️ 注意：台灣夜盤目前 **不活躍**")
    report.append("   (週六下午，夜盤交易時間為週二至週六 00:00-06:00)")
    report.append("")
    report.append("-" * 50)

report.append("")
report.append("**市場價格摘要 (透過殘留橋接資料)**:")
report.append("")

for ticker, name in [("NQ", "Nasdaq 100 期貨"), 
                      ("TSM", "台積電 ADR"), 
                      ("NVDA", "Nvidia"),
                      ("SYNA", "Synaptics"),
                      ("FITXP", "台指期 (夜)")]:
    price = prices.get(ticker)
    if price is not None:
        if ticker == "FITXP":
            report.append(f"  📈 {name} ({ticker}): {price:,.1f}")
        elif ticker in ["NQ", "FITXP"]:
             report.append(f"  📈 {name} ({ticker}): {price:,.2f}")
        else:
            report.append(f"  💰 {name} ({ticker}): ${price:.2f}")
    else:
        report.append(f"  ❌ {name} ({ticker}): 無資料")

report.append("")
report.append("-" * 50)
report.append(f"📄 資料來源：Web 爬取 (yfinance 速率限制)")
report.append(f"🕐 時間戳：{timestamp}")

if not is_night_session_active():
    report.append("")
    report.append("🔔 下次夜盤時間：週日 23:00 (週一開盤前) 或 週日 00:00-06:00")

report.append("=" * 50)

print("\n".join(report))

# Also print raw JSON for programmatic use
print("\n\n[JSON DATA]")
print(json.dumps(prices, indent=2))
