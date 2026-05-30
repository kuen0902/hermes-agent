#!/Users/bookid/.hermes/.venv/bin/python
# -*- coding: utf-8 -*-
import os
import sys
import json
import joblib
import time
import pandas as pd
import numpy as np
import duckdb
import pandas_ta_classic as ta
from datetime import datetime

# Add script folder to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rolling_ml_orchestrator import ( # type: ignore
    normalize_code,
    MODEL_DIR,
    DUCK_PATH,
    DAILY_FEATURES
)

def send_ger_notification(message):
    token = "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU" # Star Platinum (@taiwangupiaoBot) - User's active holdings channel
    chat_id = "6326497055"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        import requests
        response = requests.post(url, json=payload, timeout=10)
        if not response.json().get("ok", False):
            print(f"⚠️ Telegram API response error: {response.text}")
    except Exception as e:
        print(f"⚠️ Failed to send Telegram notification: {e}")

def load_all_data_optimized():
    conn = duckdb.connect(DUCK_PATH)
    try:
        row = conn.execute("SELECT MAX(date) FROM daily_stock_data").fetchone()
        if not row or not row[0]:
            conn.close()
            return None, {}
        latest_date_str = row[0]
        latest_dt = pd.to_datetime(latest_date_str)
        
        # 6 months (approx 200 calendar days) is safe to get 100 daily rows
        start_date = (latest_dt - pd.Timedelta(days=200)).strftime('%Y-%m-%d')
        
        print(f"  - 載入 {start_date} 以來之全市場歷史日線...")
        df_daily = conn.execute("""
            SELECT 
                code AS Code, 
                date AS Date, 
                open AS Open, 
                high AS High, 
                low AS Low, 
                close AS Close, 
                volume AS Volume, 
                foreign_net AS Foreign_Net, 
                trust_net AS Trust_Net, 
                dealer_net AS Dealer_Net
            FROM daily_stock_data
            WHERE date >= ?
            ORDER BY code, date ASC
        """, (start_date,)).fetchdf()
        
        print(f"  - 載入全市場月營收歷史...")
        df_rev = conn.execute("""
            SELECT code AS Code, date AS Rev_Date, revenue AS Monthly_Revenue, yoy AS Revenue_YoY, mom AS Revenue_MoM
            FROM monthly_revenue
            ORDER BY Code, Rev_Date ASC
        """).fetchdf()
        
        print(f"  - 載入全市場財務季報歷史...")
        df_fin = conn.execute("""
            SELECT code AS Code, report_date AS Fin_Date, eps AS EPS, gross_profit_margin AS Gross_Profit_Margin, operating_profit_margin AS Operating_Profit_Margin, net_profit_margin AS Net_Profit_Margin
            FROM financial_statements
            ORDER BY Code, Fin_Date ASC
        """).fetchdf()
        
        # Get names dictionary
        names_rows = conn.execute("SELECT DISTINCT code, name FROM daily_stock_data").fetchall()
        code_to_name = {normalize_code(c): n for c, n in names_rows if c}
        
    except Exception as e:
        print(f"❌ Error querying DuckDB: {e}")
        conn.close()
        return None, {}
    conn.close()
    
    # Normalize Code strings
    df_daily['Code'] = df_daily['Code'].apply(normalize_code)
    df_rev['Code'] = df_rev['Code'].apply(normalize_code)
    df_fin['Code'] = df_fin['Code'].apply(normalize_code)
    
    # Convert dates to datetime objects for merge_asof
    df_daily['Date_dt'] = pd.to_datetime(df_daily['Date'])  # type: ignore
    df_rev['Rev_Date_dt'] = pd.to_datetime(df_rev['Rev_Date'])  # type: ignore
    df_fin['Fin_Date_dt'] = pd.to_datetime(df_fin['Fin_Date'])  # type: ignore
    
    # Sort by datetime keys for pd.merge_asof requirement
    df_daily = df_daily.sort_values('Date_dt')
    df_rev = df_rev.sort_values('Rev_Date_dt')
    df_fin = df_fin.sort_values('Fin_Date_dt')
    
    # Perform fast pd.merge_asof
    print("  - 合併歷史日線與月營收特徵...")
    df_merged = pd.merge_asof(
        df_daily, df_rev,
        left_on='Date_dt', right_on='Rev_Date_dt',
        by='Code',
        direction='backward'
    )  # type: ignore
    
    print("  - 合併歷史日線與財務季報特徵...")
    df_merged = pd.merge_asof(
        df_merged, df_fin,
        left_on='Date_dt', right_on='Fin_Date_dt',
        by='Code',
        direction='backward'
    )  # type: ignore
    
    df_merged = df_merged.drop(columns=['Date_dt', 'Rev_Date_dt', 'Fin_Date_dt'])
    return df_merged, code_to_name

def prepare_daily_features_local(df):
    """Generates 35 features locally using shared DRY features_utils."""
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from features_utils import prepare_daily_features  # type: ignore
    return prepare_daily_features(df)

def main():
    print("=========================================================")
    print(" 🤖 啟動全市場個股獨立模型 - 最佳 30 潛力股智能篩選器 ")
    print("=========================================================")
    
    start_time = time.time()
    
    # 1. 載入並高效率合併所有特徵數據
    df_all, code_to_name = load_all_data_optimized()
    if df_all is None:
        print("❌ 無法載入資料庫特徵，程序結束。")
        return
        
    print(f"合併後日線總數據量: {len(df_all)} 筆")
    
    results = []
    
    # 2. 分組計算每檔股票技術指標並執行專屬模型預測
    print("  - 開始計算全市場商品特徵並呼叫個股專屬 XGBoost 模型預測...")
    grouped = df_all.groupby('Code')
    
    processed_count = 0
    for code, group in grouped:
        model_path = os.path.join(MODEL_DIR, f"daily_model_{code}.pkl")
        if not os.path.exists(model_path):
            continue
            
        try:
            # 本地特徵工程
            df_feat = prepare_daily_features_local(group)
            if df_feat is None or df_feat.empty:
                continue
                
            latest_row = df_feat.tail(1)
            feats_clean = latest_row[DAILY_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0.0)
            
            # 載入專屬模型進行預估
            model = joblib.load(model_path)
            pred_ret = float(model.predict(feats_clean)[0])
            latest_price = float(latest_row['Close'].values[0])
            latest_date = str(latest_row['Date'].values[0])[:10]
            
            f_net = float(latest_row['Foreign_Net'].values[0]) if 'Foreign_Net' in latest_row.columns else 0.0
            t_net = float(latest_row['Trust_Net'].values[0]) if 'Trust_Net' in latest_row.columns else 0.0
            
            name = code_to_name.get(code, code)
            
            results.append({
                "code": code,
                "name": name,
                "pred_return_pct": pred_ret * 100,
                "price": latest_price,
                "date": latest_date,
                "foreign_net": f_net,
                "trust_net": t_net
            })
            processed_count += 1
        except Exception:
            pass
            
    if not results:
        print("❌ 未能成功預估任何商品的潛力股，請檢查模型狀態。")
        return
        
    # Sort results by predicted return descending
    results = sorted(results, key=lambda x: x['pred_return_pct'], reverse=True)
    
    # Take top 30
    top_30 = results[:30]
    
    # Save to data directory
    output_path = os.path.join(os.path.expanduser("~/.hermes/data"), "top_30_potentials_individual.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(top_30, f, indent=2, ensure_ascii=False)
        
    elapsed = time.time() - start_time
    print(f"\n✓ 成功篩選出 Top 30 潛力個股，並已儲存至：{output_path}")
    print(f"  - 成功預估個股數量：{processed_count} 檔")
    print(f"  - 總計耗時：{elapsed:.2f} 秒")
    
    # 輸出 Markdown 預覽
    print("\n---------------------------------------------------------")
    print(" 🏆 全市場個股獨立模型 - 波段最佳 30 潛力股排行榜")
    print("---------------------------------------------------------")
    print(f"| 排名 | 代號 | 股名 | 最新股價 | 預估20D報酬率 | 外資買超(張) | 投信買超(張) | 基準日期 |")
    print(f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    report_lines = []
    for rank, item in enumerate(top_30, 1):
        line = f"| {rank:02d} | {item['code']} | {item['name']} | {item['price']:.2f} | {item['pred_return_pct']:+.2f}% | {item['foreign_net']:+.1f} | {item['trust_net']:+.1f} | {item['date']} |"
        print(line)
        
        # Format for Telegram
        telegram_line = f"Rank {rank:02d}: `{item['code']}` **{item['name']}** | 股價: `{item['price']:.1f}` | 預估變動: `{item['pred_return_pct']:+.2f}%` | 外資: `{item['foreign_net']:+.1f}張`"
        report_lines.append(telegram_line)
        
    # Send Telegram message
    tel_msg = f"""🌅 **「黃金體驗-鎮魂曲」：全市場個股專屬模型波段最佳 30 潛力股排行榜** 🌅

🎯 整合 14 年日線歷史、最新三大法人籌碼比率與絕對均線特徵，透過全市場在線商品**獨立自適應模型**運算得出最新波段（未來 20 交易日）最佳 30 檔潛力商品：

"""
    tel_msg += "\n".join(report_lines)
    send_ger_notification(tel_msg)
    print("\n✓ 最佳 30 潛力個股報告已發送至 Telegram 黃金體驗-鎮魂曲！")

if __name__ == "__main__":
    main()
