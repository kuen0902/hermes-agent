#!/Users/bookid/.hermes/.venv/bin/python
import os
import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 無 GUI 環境執行
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

DATA_DIR = os.path.expanduser("~/.hermes/data")
DB_PATH = os.path.join(DATA_DIR, "portfolio.db")
OUTPUT_PATH = os.path.join(DATA_DIR, "pnl_curve.png")

def generate_chart():
    print("--- 啟動 PnL 累計損益曲線圖繪製引擎 ---")
    if not os.path.exists(DB_PATH):
        print(f"❌ 找不到資料庫: {DB_PATH}")
        return False
        
    try:
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT realized_pnl, closed_at FROM pnl_history ORDER BY closed_at ASC"
        df = pd.read_sql_query(query, conn)
        conn.close()
    except Exception as e:
        print(f"❌ 讀取資料庫失敗: {e}")
        return False
        
    if df.empty:
        print("⚠️ pnl_history 資料表為空，無法產生圖表。")
        return False
        
    # 資料處理與格式轉換
    df['closed_at'] = pd.to_datetime(df['closed_at'])
    df['date'] = df['closed_at'].dt.date
    
    # 計算累計損益 (Running Cumulative Sum)
    df = df.sort_values(by='closed_at')
    df['cum_pnl'] = df['realized_pnl'].cumsum()
    
    # 依日期群組，取每日最後一筆累計損益值
    daily_df = df.groupby('date').last().reset_index()
    daily_df = daily_df.sort_values(by='date')
    
    # 建立基準點 (T-1日，損益為 0)，讓曲線有美觀的起點
    start_date = daily_df['date'].min() - pd.Timedelta(days=1)
    base_row = pd.DataFrame([{'date': start_date, 'cum_pnl': 0.0}])
    daily_df = pd.concat([base_row, daily_df[['date', 'cum_pnl']]], ignore_index=True)
    
    # 🚀 開始繪製極致美感深色圖表 🚀
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(15, 6.5), dpi=300)
    
    # 背景配色調整：超深藍/灰底色，營造科技感
    fig.patch.set_facecolor('#0f172a') # Slate 900
    ax.set_facecolor('#0f172a')
    
    # 決定曲線顏色 (整體獲利為正用亮紅/橘，虧損用亮綠，迎合台灣習慣，或是使用高科技感的青色/翡翠綠)
    # 這裡我們使用與 Telegram Theme 契合的亮青色與翡翠綠，高質感亮色
    line_color = '#10b981' # Emerald Green
    glow_color = '#34d399'
    if daily_df['cum_pnl'].iloc[-1] < 0:
        line_color = '#ef4444' # Rose Red
        glow_color = '#f87171'
        
    # 繪製平滑曲線與微光發光效果
    x_dates = daily_df['date']
    y_pnl = daily_df['cum_pnl']
    
    # 微光效果：多重透明度的粗線疊加
    ax.plot(x_dates, y_pnl, color=glow_color, alpha=0.15, linewidth=7, label='_nolegend_')
    ax.plot(x_dates, y_pnl, color=glow_color, alpha=0.3, linewidth=4, label='_nolegend_')
    # 主實線
    ax.plot(x_dates, y_pnl, color=line_color, alpha=1.0, linewidth=2.5, marker='o', markersize=4, label='Cumulative PnL')
    
    # 曲線下方漸層填滿 (Gradient Fill Effect)
    # matplotlib fill_between 與顏色漸層模擬
    ax.fill_between(x_dates, y_pnl, 0, where=(y_pnl >= 0), color=line_color, alpha=0.10)
    ax.fill_between(x_dates, y_pnl, 0, where=(y_pnl < 0), color='#ef4444', alpha=0.08)
    
    # 基準參考線 (y=0 虛線)
    ax.axhline(0, color='#475569', linestyle='--', linewidth=1, alpha=0.6)
    
    # 標題與軸標籤美化
    current_pnl = y_pnl.iloc[-1]
    sign = "+" if current_pnl > 0 else ""
    title_text = f"Hermes Cumulative PnL: {sign}{current_pnl:,.0f} TWD"
    ax.set_title(title_text, fontsize=14, fontweight='bold', pad=15, color='#f1f5f9', loc='left')
    
    # 水印與副標
    ax.text(0.98, 0.02, 'Hermes Trading Engine', transform=ax.transAxes,
            fontsize=8, color='#64748b', alpha=0.7, ha='right', va='bottom')
    
    # 網格線調整
    ax.grid(True, which='both', color='#334155', linestyle=':', linewidth=0.5, alpha=0.5)
    
    # 標註每一個有交易的點，排除起點
    annotated_indices = set(range(1, len(daily_df)))
    
    # 🧠 垂直防重疊與陡峭防重合演算法 (Vertical Non-Crossing & Slope-Aware Dispersion Algorithm)
    # 1. 為了徹底避免引導指標線交叉，我們將所有引導線設為 100% 垂直 (x_offset = 0)。
    # 2. 透過雙側（TOP/BOTTOM）與三重高度（30/75/120 與 -35/-80/-125）的六階交替排版，完美避免相鄰標籤重疊與指針線穿透。
    # 3. ⚡ 陡峭度智慧過載判定 (Steepness Override Pass)：
    #    當相鄰交易日的累計損益出現劇烈跳動 (如單日跳動 > 150,000 元且間隔 <= 2 天) 時，
    #    強制將低點標籤朝下 (BOTTOM)、高點標籤朝上 (TOP) 指引，完美避開引導指標線與極陡峭主線重合的問題！
    
    y_offsets = {}
    for i in range(len(daily_df)):
        rem = i % 6
        if rem == 0:
            y_offsets[i] = 30
        elif rem == 1:
            y_offsets[i] = -35
        elif rem == 2:
            y_offsets[i] = 75
        elif rem == 3:
            y_offsets[i] = -80
        elif rem == 4:
            y_offsets[i] = 120
        else: # rem == 5
            y_offsets[i] = -125
            
    for i in range(1, len(daily_df) - 1):
        p1 = daily_df['cum_pnl'].iloc[i]
        p2 = daily_df['cum_pnl'].iloc[i+1]
        d1 = daily_df['date'].iloc[i]
        d2 = daily_df['date'].iloc[i+1]
        days = (d2 - d1).days
        
        if days <= 2:
            if p2 - p1 > 150000: # 陡峭上升
                if y_offsets[i] > 0:
                    y_offsets[i] = -y_offsets[i]
                if y_offsets[i+1] < 0:
                    y_offsets[i+1] = -y_offsets[i+1]
            elif p1 - p2 > 150000: # 陡峭下降
                if y_offsets[i] < 0:
                    y_offsets[i] = -y_offsets[i]
                if y_offsets[i+1] > 0:
                    y_offsets[i+1] = -y_offsets[i+1]

    # 標註關鍵節點的日期與累計損益總額
    for idx, (date, pnl) in enumerate(zip(daily_df['date'], daily_df['cum_pnl'])):
        if idx not in annotated_indices:
            continue
            
        x_offset = 0
        y_offset = y_offsets[idx]
        
        # 🧠 判斷該交易日是「損」還是「益」：與前一個交易日相比
        is_loss = False
        if idx > 0:
            prev_pnl = daily_df['cum_pnl'].iloc[idx-1]
            if pnl < prev_pnl:
                is_loss = True
                
        # 🎨 動態配色：益則維持翡翠綠，損則標粉紅色
        node_color = '#ec4899' if is_loss else '#10b981'     # Pink vs Emerald Green
        pointer_color = '#f472b6' if is_loss else '#34d399'  # Light Pink vs Light Emerald
        
        # 計算當日已實現損益 (與前一個交易日相比的變動額)
        prev_pnl = daily_df['cum_pnl'].iloc[idx-1] if idx > 0 else 0.0
        daily_pnl = pnl - prev_pnl
        
        # 格式化當日損益 (帶正負號，確保虧損為「-」且與粉紅框色契合)
        daily_sign = "+" if daily_pnl > 0 else "-" if daily_pnl < 0 else ""
        abs_daily = abs(daily_pnl)
        if abs_daily >= 1_000_000:
            daily_str = f"{daily_sign}{abs_daily/1_000_000:.2f}M"
        elif abs_daily >= 1_000:
            daily_str = f"{daily_sign}{abs_daily/1_000:.1f}k"
        else:
            daily_str = f"{daily_sign}{abs_daily:.0f}"
            
        # 格式化累計總額 (不帶正號，負值帶負號)
        cum_sign = "-" if pnl < 0 else ""
        abs_cum = abs(pnl)
        if abs_cum >= 1_000_000:
            cum_str = f"{cum_sign}{abs_cum/1_000_000:.2f}M"
        elif abs_cum >= 1_000:
            cum_str = f"{cum_sign}{abs_cum/1_000:.1f}k"
        else:
            cum_str = f"{cum_sign}{abs_cum:.0f}"
            
        # 組合標籤：當日完成損益 (累計總額)
        pnl_str = f"{daily_str} ({cum_str})"
            
        # 繪製高階氣泡框與精準指針 (Arrowprops)
        ax.annotate(
            f"{date.strftime('%m/%d')}\n{pnl_str}",
            (date, pnl),
            textcoords="offset points",
            xytext=(x_offset, y_offset),
            ha='center',
            va='bottom' if y_offset > 0 else 'top',
            fontsize=5.5,
            color='#cbd5e1', # Slate 300
            alpha=0.95,
            fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.25", fc="#1e293b", ec=node_color, alpha=0.9, lw=1.0),
            arrowprops=dict(
                arrowstyle="->",
                color=pointer_color,
                lw=0.8,
                alpha=0.9,
                connectionstyle="arc3,rad=0.0"
            )
        )
    
    # X軸日期格式與精確雙週（15天間隔）排版設定，徹底杜絕底部標籤密集重疊
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=15))
    plt.xticks(
        rotation=30, 
        color='#94a3b8', 
        fontsize=8.5
    )
    
    # Y軸千分位與顏色設定
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: f"{x:,.0f}"))
    plt.yticks(color='#94a3b8', fontsize=9)
    
    # 邊框線顏色微調 (隱藏上方和右方邊框)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#334155')
    ax.spines['bottom'].set_color('#334155')
    
    # 排版自動調整並儲存
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, facecolor='#0f172a', edgecolor='none', bbox_inches='tight')
    plt.close()
    
    print(f"✓ PnL 累計損益曲線圖已成功繪製並儲存至: {OUTPUT_PATH}")
    return True

if __name__ == "__main__":
    generate_chart()
