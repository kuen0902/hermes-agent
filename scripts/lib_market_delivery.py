import requests
import json
import os
import sys

# --- Configuration ---
# Star Platinum @taiwangupiaoBot (Group Monitor)
STAR_PLATINUM_TOKEN = "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU"
# William's Bot - WilliamClaw
WILLIAM_CLAW_TOKEN = "8678817340:AAHLd6ObYqUUTfygY-fPf57Rw6SfOO2WEGQ"
# GER @kuenmingBot
GER_TOKEN = "8513436203:AAHcvVxNgLEqQ_U_JH55mZaENCWfl4VTFJ4"

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
    # 1. Star Platinum Group Report (DISABLED per User request)
    # sp_msg = f"""⭐ **「白金之星」：精密數據監修** ⭐
    # ORA ORA ORA! 所有的數據誤差已被速度抹除。
    # ...
    # send_telegram(STAR_PLATINUM_TOKEN, GROUP_ID, sp_msg)
    pass

    # 2. GER Private Report
    ger_msg = f"""🌅 **「黃金體驗-鎮魂曲」：現實同步** 🌅

偏離的意志已歸於「零」。這就是目前的絕對現實。

### 📉 **市場位階深度同步**
- **FITXP**: `{data['FITXP']['price']}` ({data['FITXP']['pct']:+.2f}%)
- **TSM**: `${data['TSM']['price']:.2f}` ({data['TSM']['pct']:+.2f}%)
- **NVDA**: `${data['NVDA']['price']:.2f}` ({data['NVDA']['pct']:+.2f}%)
- **SYNA**: `${data['SYNA']['price']:.2f}` ({data['SYNA']['pct']:+.2f}%)

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
