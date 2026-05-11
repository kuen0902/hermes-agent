import json
import os
from datetime import datetime

SIGNALS_FILE = os.path.expanduser("~/.hermes/data/ml_signals.json")

def format_signals():
    if not os.path.exists(SIGNALS_FILE):
        return "⚠️ ML 訊號文件不存在。"
    
    with open(SIGNALS_FILE, 'r') as f:
        data = json.load(f)
    
    gen_time = datetime.fromisoformat(data['generated_at']).strftime("%Y-%m-%d %H:%M")
    
    output = [
        f"🤖 **AI Architect: ML 交易訊號報告**",
        f"⏰ 生成時間：`{gen_time}`",
        f"----------------------------",
    ]
    
    if data['buy']:
        output.append("🔥 **買入訊號 (預期 5 日漲幅 > 3%)**")
        # Show top 10 by confidence
        sorted_buy = sorted(data['buy'], key=lambda x: float(x['confidence'].strip('%')), reverse=True)[:10]
        for s in sorted_buy:
            output.append(f"• `{s['symbol']}` ({s['name']}): `{s['confidence']}` @ ${s['price']:.2f}")
    else:
        output.append("⚪ 目前無顯著買入訊號。")
        
    output.append("")
    
    if data['sell']:
        output.append("❄️ **賣出訊號 (預期 5 日跌幅 > 3%)**")
        sorted_sell = sorted(data['sell'], key=lambda x: float(x['confidence'].strip('%')), reverse=True)[:10]
        for s in sorted_sell:
            output.append(f"• `{s['symbol']}` ({s['name']}): `{s['confidence']}` @ ${s['price']:.2f}")
    else:
        output.append("⚪ 目前無顯著賣出訊號。")
        
    output.append("----------------------------")
    output.append("💡 *註：此為 ML 模型預測，僅供參考，請務必搭配基本面分析。*")
    
    return "\n".join(output)

if __name__ == "__main__":
    print(format_signals())
