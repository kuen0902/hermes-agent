#!/Users/bookid/.hermes/.venv/bin/python
import os
import json
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # headless execution
import matplotlib.pyplot as plt
import numpy as np

# Configuration
DATA_DIR = os.path.expanduser("~/.hermes/data")
INPUT_JSON_PATH = os.path.join(DATA_DIR, "top_50_potential_stocks.json")
OUTPUT_CHART_PATH = os.path.join(DATA_DIR, "top_20_potential_stocks.png")
OUTPUT_MD_PATH = os.path.join(DATA_DIR, "top_50_report.md")

def generate_report():
    print("--- 啟動 ML 潛力股視覺化與報告生成引擎 ---")
    if not os.path.exists(INPUT_JSON_PATH):
        print(f"❌ 找不到潛力股資料: {INPUT_JSON_PATH}")
        return False
        
    try:
        with open(INPUT_JSON_PATH, 'r', encoding='utf-8') as f:
            top_50 = json.load(f)
    except Exception as e:
        print(f"❌ 讀取潛力股資料失敗: {e}")
        return False
        
    if not top_50:
        print("⚠️ 潛力股資料為空，無法產生圖表。")
        return False
        
    # Get Top 20 for the chart
    top_20 = top_50[:20]
    
    # Reverse to have the highest rank at the top of horizontal bar chart
    top_20_rev = list(reversed(top_20))
    
    tickers = [f"{s['code']} {s['name']}" for s in top_20_rev]
    predicted_returns = [s['predicted_return_20d'] * 100 for s in top_20_rev]
    foreign_5d = [s['foreign_net_5d'] for s in top_20_rev]
    trust_5d = [s['trust_net_5d'] for s in top_20_rev]
    dual_force_5d = [s['dual_force_5d'] for s in top_20_rev]
    
    # Extract prediction date dynamically from dataset
    predict_date = top_50[0].get('date', datetime.now().strftime('%Y-%m-%d'))
    
    # 🚀 開始繪製極致美感深色圖表 🚀
    plt.rcParams['font.sans-serif'] = ['Heiti TC', 'PingFang TC', 'Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    
    # Background styling (Slate 900 matching generate_pnl_chart.py)
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')
    
    # Color gradient based on predicted return
    # Max predicted return gets the brightest emerald, min gets a deeper green
    norm = plt.Normalize(min(predicted_returns), max(predicted_returns))
    # Emerald green colors: from #10b981 to #065f46
    colors = plt.get_cmap('summer')(norm(predicted_returns))
    
    # Horizontal bars
    bars = ax.barh(tickers, predicted_returns, color=colors, alpha=0.85, height=0.6)
    
    # Highlight bars with high dual force buying (Foreign & Trust net buying)
    for idx, (bar, df_val) in enumerate(zip(bars, dual_force_5d)):
        # If both foreign and trust bought significantly (> 100張) in last 5 days
        if foreign_5d[idx] > 50 and trust_5d[idx] > 50:
            bar.set_edgecolor('#ec4899') # Pink border for "Dual Force" cohesion
            bar.set_linewidth(1.5)
            
    # Add values and chip info on the right side of the bars
    for idx, bar in enumerate(bars):
        width = bar.get_width()
        f_val = foreign_5d[idx]
        t_val = trust_5d[idx]
        close_val = top_20_rev[idx]['close']
        pred_val = close_val * (1.0 + top_20_rev[idx]['predicted_return_20d'])
        
        # Build text label for chip flow
        # e.g., " TWD 114.0 ➔ 預估 $143.5 (20日後) | 外: +1.2k 投: +500"
        f_str = f"+{f_val/1000:.1f}M" if f_val >= 1000 else f"+{f_val:.0f}" if f_val > 0 else f"{f_val:.0f}"
        t_str = f"+{t_val/1000:.1f}M" if t_val >= 1000 else f"+{t_val:.0f}" if t_val > 0 else f"{t_val:.0f}"
        
        chip_label = f" (外:{f_str} 投:{t_str})"
        label_text = f" {close_val:,.1f}元 → 預估 {pred_val:,.1f}元 (20日後) | +{width:.2f}%{chip_label}"
        
        ax.text(
            width + 0.1, 
            bar.get_y() + bar.get_height()/2, 
            label_text, 
            va='center', 
            ha='left', 
            fontsize=7.0,
            color='#cbd5e1',  # Slate 300
            fontweight='bold'
        )
        
    # Title and Labels - dynamically showing prediction date
    ax.set_title(f"台股 Top 20 潛力股預測 [{predict_date}]：機器學習波段勝率與法人籌碼雷達", fontsize=13, fontweight='bold', pad=15, color='#f1f5f9', loc='left')
    ax.set_xlabel("預期 20 日波段回報率 (%)", fontsize=9, color='#cbd5e1', labelpad=10)
    
    # Adjust axes
    ax.grid(True, axis='x', color='#334155', linestyle=':', linewidth=0.5, alpha=0.5)
    plt.xticks(color='#94a3b8', fontsize=8)
    plt.yticks(color='#f1f5f9', fontsize=8.5, fontweight='bold')
    
    # Hide borders
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#334155')
    ax.spines['bottom'].set_color('#334155')
    
    # Watermark
    ax.text(0.98, 0.02, 'Hermes AI Architect: XGBoost Potential Score v1.0', transform=ax.transAxes,
            fontsize=7, color='#64748b', alpha=0.7, ha='right', va='bottom')
            
    # Adjust limits (expanded to 2.1x to prevent long text labels from being cut off on the right)
    max_x = max(predicted_returns) * 2.1 if predicted_returns else 10.0
    ax.set_xlim(0, max_x)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_CHART_PATH, facecolor='#0f172a', edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"✓ Top 20 潛力股預測圖已成功繪製並儲存至: {OUTPUT_CHART_PATH}")
    
    # 📝 生成 Markdown 報告
    generate_md_report(top_50)
    return True

def generate_md_report(top_50):
    predict_date = top_50[0].get('date', datetime.now().strftime('%Y-%m-%d'))
    lines = []
    lines.append(f"# 台股 Top 50 機器學習波段潛力個股 analysis 報告 ({predict_date})")
    lines.append("")
    lines.append("> **分析模型**：XGBoost Regressor (波段特徵工程 + 三大法人籌碼流向篩選)")
    lines.append("> **回報標的**：未來 20 個交易日 (約一個月) 的預期超額報酬率")
    lines.append("> **篩選範圍**：過去 5 年持續在市場上運作的資深高流動性個股")
    lines.append("")
    lines.append("## 核心洞察 (Core Insights)")
    
    # Count dual force
    dual_force_count = sum(1 for s in top_50 if s['foreign_net_5d'] > 50 and s['trust_net_5d'] > 50)
    lines.append(f"- **外資投信聯手強推**：前 50 大潛力股中，有 **{dual_force_count} 檔** 個股在過去 5 天獲得外資與投信的同步大額買超 (雙強共振)。這通常是極度強烈的飆股波段起點訊號！")
    
    # Highlight top 3
    lines.append("- **首推三大明星個股**：")
    for s in top_50[:3]:
        s_pred = s['close'] * (1.0 + s['predicted_return_20d'])
        lines.append(f"  - **{s['ticker']} {s['name']}**：現價 **{s['close']:.2f}元** ➔ **預估 {s_pred:.2f}元** (20日後/約1個月後到達)，預期波段漲幅 **{s['predicted_return_20d']*100:.2f}%**，近5日法人聯手買超 **{s['dual_force_5d']:.0f}張**。")
        
    lines.append("")
    lines.append("## Top 50 潛力股詳細清單 (完整排名)")
    lines.append("")
    lines.append("| 排名 | 股號 | 股名 | 現價 (TWD) | 預估股價 (20日後) | 預期波段回報 | 5D 外資買超 (張) | 5D 投信買超 (張) | 5D 聯手買超 (張) | 20D 外資累計 (張) | 20D 投信累計 (張) | RSI (14) |")
    lines.append("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    
    for s in top_50:
        predicted_price = s['close'] * (1.0 + s['predicted_return_20d'])
        lines.append(f"| {s['rank']} | {s['code']} | {s['name']} | {s['close']:.2f} | **{predicted_price:.2f}** | **{s['predicted_return_20d']*100:.2f}%** | {s['foreign_net_5d']:.0f} | {s['trust_net_5d']:.0f} | **{s['dual_force_5d']:.0f}** | {s['foreign_net_20d']:.0f} | {s['trust_net_20d']:.0f} | {s['rsi_14']:.1f} |")
        
    with open(OUTPUT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
        
    print(f"✓ Top 50 潛力股 Markdown 報告已生成並儲存至: {OUTPUT_MD_PATH}")

def send_telegram_report(top_50, chart_path):
    import urllib.request
    import urllib.parse
    import ssl
    import requests
    
    print("--- 發送潛力股報告給 Jojo ---")
    token = "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU"
    chat_id = "6326497055"
    
    predict_date = top_50[0].get('date', datetime.now().strftime('%Y-%m-%d'))
    
    # 建立 Top 30 訊息
    msg_lines = [
        f"🤖 **AI Architect: 台股 Top 30 機器學習波段潛力股報告 ({predict_date})**",
        f"⏰ 播送時間：`{datetime.now().strftime('%Y-%m-%d %H:%M')}`",
        f"----------------------------",
        f"🎯 **篩選機制**：XGBoost 雙階段波段特徵工程 + 三大法人籌碼流向篩選。預估未來 20 個交易日 (約一個月) 的波段超額報酬率。",
        f"----------------------------",
    ]
    
    for s in top_50[:30]:
        rank = s['rank']
        code = s['code']
        name = s['name']
        close = s['close']
        pred_ret = s['predicted_return_20d'] * 100
        pred_price = close * (1.0 + s['predicted_return_20d'])
        df_5d = s['dual_force_5d']
        
        # 聯手買超標記
        star = "🔥" if s['foreign_net_5d'] > 50 and s['trust_net_5d'] > 50 else "•"
        msg_lines.append(f"{star} **No.{rank}** `{code}` **{name}**")
        msg_lines.append(f"  └ 現價: `{close:.1f}元` ➔ 預估: **`{pred_price:.1f}元`** ({pred_ret:+.2f}%)")
        msg_lines.append(f"  └ 5D法人買超: `{df_5d:.0f}張` (外:{s['foreign_net_5d']:.0f} 投:{s['trust_net_5d']:.0f})")
        
    msg_lines.append("----------------------------")
    msg_lines.append("💡 *註：本報告由機器學習模型依據籌碼與技術面特徵自動運算，僅供波段決策參考。*")
    
    message = "\n".join(msg_lines)
    
    # 發送純文字
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    ctx = ssl._create_unverified_context()
    data = urllib.parse.urlencode({
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, context=ctx, timeout=20)
        print("✓ 成功發送潛力股純文字報告給 Jojo")
    except Exception as e:
        print(f"❌ 發送 Telegram 文字失敗: {e}")
        
    # 發送圖表
    if os.path.exists(chart_path):
        url_photo = f"https://api.telegram.org/bot{token}/sendPhoto"
        try:
            with open(chart_path, 'rb') as f:
                files = {'photo': f}
                data_photo = {
                    'chat_id': chat_id, 
                    'caption': f"📈 台股 Top 20 機器學習波段潛力個股雷達圖 ({predict_date})", 
                    'parse_mode': 'Markdown'
                }
                requests.post(url_photo, data=data_photo, files=files, timeout=30)
                print("✓ 成功發送潛力股雷達圖給 Jojo")
        except Exception as e:
            print(f"❌ 發送 Telegram 圖表失敗: {e}")

if __name__ == "__main__":
    import sys
    send_tg = "--send-telegram" in sys.argv
    success = generate_report()
    if success and send_tg:
        try:
            with open(INPUT_JSON_PATH, 'r', encoding='utf-8') as f:
                top_50 = json.load(f)
            send_telegram_report(top_50, OUTPUT_CHART_PATH)
        except Exception as e:
            print(f"發送 Telegram 失敗: {e}")
