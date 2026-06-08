import requests
import json
import os
import sys

# --- Configuration ---
# Star Platinum @taiwangupiaoBot (Group Monitor)
STAR_PLATINUM_TOKEN = "8513436203:AAFgyNQja4cXVsyhFurVlKMOaKugyOJG1uM"
# William's Bot - WilliamClaw
WILLIAM_CLAW_TOKEN = "8678817340:AAHLd6ObYqUUTfygY-fPf57Rw6SfOO2WEGQ"
# GER @kuenmingBot (If you have the real token, please replace the *** here)
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
    data: dict containing filtered assets that crossed the threshold:
          {sym: {"name": "...", "price": 123.4, "pct": 3.2, "tier": 3}, ...}
    """
    # Strict Time Gate check to enforce silencing outside 15:00 - 05:15 Taipei time
    try:
        if "/Users/bookid/.hermes/scripts" not in sys.path:
            sys.path.append("/Users/bookid/.hermes/scripts")
        from night_market_gatekeeper import is_night_session_active
        if not is_night_session_active():
            print("Muted: deliver_market_report called outside night session hours.")
            return
    except Exception as e:
        import pytz
        from datetime import datetime
        taipei_tz = pytz.timezone('Asia/Taipei')
        now = datetime.now(taipei_tz)
        hour = now.hour
        if not (hour >= 15 or hour < 5 or (hour == 5 and now.minute <= 15)):
            print("Muted: deliver_market_report called outside night session hours (fallback check).")
            return

    if not data:
        return
        
    # 1. Star Platinum Group Report
    sp_msg = f"""⭐ **「白金之星」：精密數據監修** ⭐
ORA ORA ORA! 數據雜訊已被悉數抹除。

### 🌌 **夜盤全球聯動監測 (階梯突破)**
"""
    for sym, info in data.items():
        # Format properly if it's a large number or decimal
        price_fmt = f"{info['price']:,.2f}" if isinstance(info['price'], (float, int)) else info['price']
        sp_msg += f"- **{info['name']}** ({sym}): `{price_fmt}` ({info['pct']:+.2f}%) 突破 `{info['tier']}%`\n"

    # 1. Star Platinum Group Report
    send_telegram(STAR_PLATINUM_TOKEN, GROUP_ID, sp_msg)

    # 2. GER Private Report [DISABLED - User requested night session reports to group only]
    # ger_msg = f"""🌅 **「黃金體驗-鎮魂曲」：現實同步** 🌅
    # 
    # 偏離的意志已歸於「零」。這就是目前的絕對現實。
    # 
    # ### 📉 **市場位階深度同步 (階梯突破)**
    # """
    # for sym, info in data.items():
    #     price_fmt = f"{info['price']:,.2f}" if isinstance(info['price'], (float, int)) else info['price']
    #     ger_msg += f"- **{info['name']}** ({sym}): `{price_fmt}` ({info['pct']:+.2f}%) 突破 `{info['tier']}%`\n"
    # 
    # ger_msg += "\n**無駄！**"
    # 
    # send_telegram(GER_TOKEN, JOJO_CHAT_ID, ger_msg)

if __name__ == "__main__":
    # Test Data / Internal Structure
    sample_data = {
        "FITXP": {"name": "台指期 (夜)", "price": 41971, "pct": 3.53, "tier": 3},
        "TSM": {"name": "台積電 ADR", "price": 401.55, "pct": -5.46, "tier": -5},
    }
    deliver_market_report(sample_data)
