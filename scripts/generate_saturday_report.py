#!/usr/bin/env python3
import json
from datetime import datetime
import pytz
import os

# Load bridge data
bridge_path = os.path.expanduser("~/.hermes/data/market_prices_bridge.json")
with open(bridge_path, 'r') as f:
    prices = json.load(f)

taipei_tz = pytz.timezone('Asia/Taipei')
now = datetime.now(taipei_tz).strftime('%Y-%m-%d %H:%M:%S')

print("=== 夜盤監控週六彙總報告 ===")
print(f"報告時間: {now}")
print(f"交易日: 2026-05-16 (週六)")
print(f"狀態: 夜盤已結束 (05:00 收市)")
print()
print("---")
print()
print("【最新市場價格 (yFinance 實時)】")
print()
print(f"NQ (Nasdaq 100 Futures): {prices['NQ']:,.2f} (NY Open: -1.06%)")
print(f"TSM (台積電 ADR): {prices['TSM']:.2f} (昨收數據)")
print(f"NVDA (Nvidia): {prices['NVDA']:.2f} (昨收數據)")
print(f"SYNA (Synaptics): {prices['SYNA']:.2f} (昨收數據)")
print(f"FITXP (台指期夜盤): {prices['FITXP']:,.2f} (^TWII 代理數據)")
print()
print("---")
print()
print("【關鍵分析】")
print()
print("1. NQ 期貨: 29,231.75 (NY 盤下跌 1.06%)")
print("2. 台指期代理值: 41,172.36 (^TWII 指數)")
print("3. 台積電 ADR: $404.35")
print("4. 輝達: $225.32")
print()
print("---")
print("注意:")
print("- 夜盤已於週六 05:00 收市")
print("- 下次夜盤開始: 週一至週五 15:00")
print("- 若逢台灣假日，夜盤將跳過")
print()
print("數據來源: Yahoo Finance")
print(f"橋接檔案時間: {prices['timestamp']}")
