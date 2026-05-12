import requests
import json
import os
import sys

# --- Configuration ---
# Star Platinum @taiwangupiaoBot (Group Monitor)
STAR_PLATINUM_TOKEN = "8737129549:***"
# William's Bot - WilliamClaw
WILLIAM_CLAW_TOKEN = "8678817340:***"
# GER @kuenmingBot
GER_TOKEN = "8513436203:***"

GROUP_ID = "-1003744330314"
JOJO_CHAT_ID = "6326497055"

def send_telegram(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def deliver_market_report(data):
    """
    data: dict containing prices, deltas, and session_deltas for FITXP, TSM, NVDA, SYNA
    """
    # 1. Star Platinum Group Report (RE-ENABLED per User request "白金之星不回應")
    sp_msg = f"""⭐ **「白金之星」：精密數據監修** ⭐
ORA ORA ORA! 數據雜訊已被悉數抹除。

### 🌌 **夜盤全球聯動監測**
- **台指期 (夜)**: `{data.get('FITXP', {}).get('price', 'N/A')}` ({data.get('FITXP', {}).get('pct', 0):+.2f}%)
- **台積電 ADR**: `${data.get('TSM', {}).get('price', 0):.2f}` ({data.get('TSM', {}).get('pct', 0):+.2f}%)
- **輝達 (NVDA)**: `${data.get('NVDA', {}).get('price', 0):.2f}` ({data.get('NVDA', {}).get('pct', 0):+.2f}%)
- **新思 (SYNA)**: `${data.get('SYNA', {}).get('price', 0):.2f}` ({data.get('SYNA', {}).get('pct', 0):+.2f}%)

💡 *備註：當前連結狀態穩定。*
"""
    send_telegram(STAR_PLATINUM_TOKEN, GROUP_ID, sp_msg)

    # 2. GER Private Report
    ger_msg = f"""🌅 **「黃金體驗-鎮魂曲」：現實同步** 🌅

偏離的意志已歸於「零」。這就是目前的絕對現實。

### 📉 **市場位階深度同步**
- **FITXP**: `{data.get('FITXP', {}).get('price', 'N/A')}` ({data.get('FITXP', {}).get('pct', 0):+.2f}%)
- **TSM**: `${data.get('TSM', {}).get('price', 0):.2f}` ({data.get('TSM', {}).get('pct', 0):+.2f}%)
- **NVDA**: `${data.get('NVDA', {}).get('price', 0):.2f}` ({data.get('NVDA', {}).get('pct', 0):+.2f}%)
- **SYNA**: `${data.get('SYNA', {}).get('price', 0):.2f}` ({data.get('SYNA', {}).get('pct', 0):+.2f}%)

**無駄！**"""
    
    send_telegram(GER_TOKEN, JOJO_CHAT_ID, ger_msg)

if __name__ == "__main__":
    # Test Data / Internal Structure
    sample_data = {
        "FITXP": {"price": 41971, "delta": 220.0, "pct": 0.53},
        "TSM": {"price": 401.55, "delta": -10.13, "pct": -2.46},
        "NVDA": {"price": 216.82, "delta": 1.60, "pct": 0.74},
        "SYNA": {"price": 125.57, "delta": 0.14, "pct": 0.11}
    }
    deliver_market_report(sample_data)
