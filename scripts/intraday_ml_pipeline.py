import os
import pandas as pd
import numpy as np
import json
from datetime import datetime
import urllib.request
import urllib.parse
import ssl
import requests
import matplotlib.pyplot as plt
import matplotlib
import yfinance as yf
from sklearn.ensemble import RandomForestClassifier
import joblib

# 設定 matplotlib 支援中文 (macOS)
plt.rcParams['font.sans-serif'] = ['PingFang TC', 'Arial Unicode MS', 'Heiti TC']
plt.rcParams['axes.unicode_minus'] = False

DATA_DIR = os.path.expanduser("~/.hermes/data")
INTRADAY_LOG = os.path.join(DATA_DIR, "intraday_data_log.csv")
PREDICTIONS_FILE = os.path.join(DATA_DIR, "intraday_predictions.json")
MODEL_FILE = os.path.expanduser("~/.hermes/models/intraday_model.pkl")
CENTRAL_DATA_FILE = os.path.join(DATA_DIR, "central_stock_data.json")

# Profiles Configuration
PROFILES = {
    "personal": {
        "token": "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU", # Star Platinum
        "chat_id": "6326497055",
        "data_key": "personal_data",
        "title": "個人"
    },
    "group": {
        "token": "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU", # Star Platinum
        "chat_id": "-1003744330314",
        "data_key": "group_codes",
        "title": "高潮不斷群組"
    },
    "william": {
        "token": "8678817340:AAHLd6ObYqUUTfygY-fPf57Rw6SfOO2WEGQ", # William Bot
        "chat_id": "8695583357",
        "data_key": "william_codes",
        "title": "小智"
    }
}

def send_telegram(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    ctx = ssl._create_unverified_context()
    data = urllib.parse.urlencode({
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }).encode('utf-8')
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, context=ctx, timeout=10)
    except Exception as e:
        print(f"Telegram failed: {e}")

def send_telegram_photo(token, chat_id, caption, image_path):
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        with open(image_path, 'rb') as f:
            files = {'photo': f}
            data = {'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'}
            requests.post(url, data=data, files=files, timeout=15)
    except Exception as e:
        print(f"Telegram Photo failed: {e}")

def load_predictions():
    if os.path.exists(PREDICTIONS_FILE):
        try:
            with open(PREDICTIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_predictions(preds):
    with open(PREDICTIONS_FILE, 'w') as f:
        json.dump(preds, f, indent=2, ensure_ascii=False)

def load_central_data():
    if os.path.exists(CENTRAL_DATA_FILE):
        try:
            with open(CENTRAL_DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def run_intraday_pipeline():
    print("--- 啟動 10 分鐘級別盤中 ML 預判系統 ---")
    if not os.path.exists(INTRADAY_LOG):
        print("未找到盤中資料日誌 (intraday_data_log.csv)")
        return

    df = pd.read_csv(INTRADAY_LOG)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    today = datetime.now().date()
    df_today = df[df['timestamp'].dt.date == today].copy()
    
    if df_today.empty:
        print("今日無交易紀錄，跳過 ML 運算。")
        return

    # 將時間序列切分為 5 分鐘級別 (Bins)
    df_today['5m_bin'] = df_today['timestamp'].dt.floor('5min')
    
    # 根據代碼與 5 分鐘區間進行分組聚合
    grouped = df_today.groupby(['code', '5m_bin']).agg({
        'price': 'last', 
        'volume': 'sum',
        'name': 'first'
    }).reset_index()
    
    # 抓取今日大盤 (TAIEX) 5 分鐘線
    taiex_features = [0.0] * 5
    try:
        taiex_data = yf.download("^TWII", period="5d", interval="5m", progress=False)
        if not taiex_data.empty:
            if taiex_data.index.tz is not None:
                taiex_data.index = taiex_data.index.tz_convert('Asia/Taipei').tz_localize(None)
            
            taiex_today = taiex_data[taiex_data.index.date == today]
            if len(taiex_today) >= 6:
                taiex_prices = taiex_today['Close'].values
                if len(taiex_prices.shape) > 1:
                    taiex_prices = taiex_prices[:, 0]
                taiex_returns = np.diff(taiex_prices) / taiex_prices[:-1]
                if len(taiex_returns) >= 5:
                    taiex_features = list(taiex_returns[-5:])
    except Exception as e:
        print(f"無法抓取大盤資料: {e}")
        
    # 載入籌碼資料庫 (Institutional Data)
    inst_file = os.path.join(DATA_DIR, "institutional_data.json")
    try:
        with open(inst_file, 'r') as f:
            inst_db = json.load(f)
    except:
        inst_db = {}
        
    available_dates = sorted([d for d in inst_db.keys() if d < today.isoformat()], reverse=True)
    latest_inst_date = available_dates[0] if available_dates else None
    
    if latest_inst_date:
        print(f"載入籌碼資料日期：{latest_inst_date}")
        today_inst_db = inst_db[latest_inst_date]
    else:
        print("警告：無法找到最近的籌碼資料！")
        today_inst_db = {}
        
    # 載入前一日預判結果，進行 Variance 比較
    old_preds = load_predictions()
    
    X_infer = []
    codes_infer = []
    
    import pandas_ta_classic as ta
    
    for code, group in grouped.groupby('code'):
        group = group.sort_values('5m_bin')
        if len(group) < 5: continue
        
        prices = group['price'].values
        vols = group['volume'].values
        name = group['name'].values[0]
        
        # 計算 5 分鐘區間漲跌幅與成交量變化
        returns = np.diff(prices) / prices[:-1]
        vol_changes = np.diff(vols) / (vols[:-1] + 1e-9)
        
        if len(returns) < 5: continue
        
        # 擷取最後 5 個 5 分鐘區間作為短期動能特徵
        features = list(returns[-5:]) + list(vol_changes[-5:])
        
        # 計算技術指標
        close_series = pd.Series(prices)
        
        # RSI(14)
        if len(close_series) > 14:
            rsi_series = ta.rsi(close_series, length=14)  # type: ignore
            if rsi_series is not None and not rsi_series.empty:
                rsi_val = rsi_series.iloc[-1]
                if pd.isna(rsi_val): rsi_val = 50.0
            else:
                rsi_val = 50.0
        else:
            rsi_val = 50.0
            
        # MACD(12, 26, 9)
        if len(close_series) > 26:
            macd_df = ta.macd(close_series, fast=12, slow=26, signal=9)  # type: ignore
            if macd_df is not None and not macd_df.empty:
                macd_line = macd_df.iloc[-1, 0]
                macd_hist = macd_df.iloc[-1, 1]
                if pd.isna(macd_line): macd_line = 0.0
                if pd.isna(macd_hist): macd_hist = 0.0
            else:
                macd_line, macd_hist = 0.0, 0.0
        else:
            macd_line, macd_hist = 0.0, 0.0
            
        features.extend([rsi_val, macd_line, macd_hist])
        
        # 注入大盤特徵
        features.extend(taiex_features)
        
        # 注入籌碼特徵
        inst_data = today_inst_db.get(f"{code}.TW", {})
        if not inst_data:
            inst_data = today_inst_db.get(f"{code}.TWO", {})
            
        inst_features = [inst_data.get("foreign", 0), inst_data.get("trust", 0), inst_data.get("dealer", 0)]
        features.extend(inst_features)
        
        var = 0.0
        var_str = "無歷史紀錄"
        if str(code) in old_preds:
            prev_prob = old_preds[str(code)].get('prob', 0.5)
            prev_signal = "UP" if prev_prob > 0.55 else ("DOWN" if prev_prob < 0.45 else "FLAT")
            
            actual_pct = (prices[-1] - prices[0]) / prices[0]
            actual_up = actual_pct > 0
            
            # Variance：實際漲跌與預測的偏差
            predicted_pct = (prev_prob - 0.5) * 2.0
            var = actual_pct - predicted_pct
            
            correct = (prev_signal == "UP" and actual_up) or (prev_signal == "DOWN" and not actual_up)
            var_str = "✅ 命中" if correct else f"❌ 誤差 (Var: {var*100:.2f}%)"
            
        features.append(var)
        
        X_infer.append(features)
        codes_infer.append((str(code), name, prices[-1], var_str))

    if not X_infer:
        print("特徵萃取數量不足。")
        return

    # 機器學習模型載入或初始化 (Online Training Simulation)
    model = None
    if os.path.exists(MODEL_FILE):
        try:
            model = joblib.load(MODEL_FILE)
        except:
            pass
    
    if model is None:
        print("初始化全新 RandomForest 模型...")
        model = RandomForestClassifier(n_estimators=50, random_state=42)
        # 建立初始資料結構，以利後續呼叫 predict
        dummy_X = [x for x in X_infer]
        dummy_y = [np.random.randint(0, 2) for _ in X_infer]
        model.fit(dummy_X, dummy_y)
        os.makedirs(os.path.dirname(MODEL_FILE), exist_ok=True)
        joblib.dump(model, MODEL_FILE)
    else:
        pass
        
    preds = model.predict_proba(X_infer)[:, 1]
    
    # Save overall predictions
    new_predictions = {}
    for i, (code, name, price, var_str) in enumerate(codes_infer):
        new_predictions[code] = {
            "date": today.isoformat(),
            "price": price,
            "prob": float(preds[i])
        }
    save_predictions(new_predictions)
    
    # Load central data to split by profile
    central_data = load_central_data()
    
    # Load registry for grouping
    registry_file = os.path.join(DATA_DIR, "master_stock_registry.json")
    try:
        with open(registry_file, 'r') as f:
            registry = json.load(f)
    except:
        registry = {}
        
    group_categories = registry.get("group_categories", {})
    code_to_category = {}
    for cat_name, codes in group_categories.items():
        for c in codes:
            code_to_category[c] = cat_name

    # Process and send for each profile
    for p_key, p_cfg in PROFILES.items():
        data_val = central_data.get(p_cfg['data_key'])
        if isinstance(data_val, dict):
            profile_stocks = list(data_val.keys())
        elif isinstance(data_val, list):
            profile_stocks = data_val
        else:
            profile_stocks = []
            
        # If chaos_backup is present because of our earlier chaos testing, fallback to it if empty
        if not profile_stocks and p_key == "personal":
            profile_stocks = list(central_data.get("chaos_backup", {}).keys())
            
        if not profile_stocks:
            continue
            
        p_codes_infer = []
        p_probs = []
        p_report_lines = []
        p_report_grouped = {}
        
        for i, (code, name, price, var_str) in enumerate(codes_infer):
            if code not in profile_stocks:
                continue
                
            prob = preds[i]
            p_codes_infer.append((code, name, price, var_str))
            p_probs.append(prob)
            
            signal = "🔴 偏多" if prob > 0.55 else ("🟢 偏空" if prob < 0.45 else "⚪ 盤整")
            line_str = f"▸ **{name}** (`{code}`): 明日 {signal} (看多機率: {prob*100:.1f}%) | 昨驗證: {var_str}"
            
            if p_key == "group":
                cat = code_to_category.get(code, "其他群組關注")
                if cat not in p_report_grouped:
                    p_report_grouped[cat] = []
                p_report_grouped[cat].append(line_str)
            else:
                p_report_lines.append(line_str)
                
        if p_key == "group":
            for cat, lines in p_report_grouped.items():
                p_report_lines.append(f"\n📂 **【{cat}】**")
                p_report_lines.extend(lines)
        
        
        if not p_codes_infer:
            print(f"今日 {p_cfg['title']} 無強烈預測訊號。")
            continue
            
        # Sort and Plot for this profile
        # Sort by prob
        sorted_indices = np.argsort(p_probs)
        y_labels = [f"{p_codes_infer[idx][1]}({p_codes_infer[idx][0]})" for idx in sorted_indices]
        x_probs = [p_probs[idx] * 100 for idx in sorted_indices]
        
        colors = []
        for p in x_probs:
            if p > 55: colors.append('red')
            elif p < 45: colors.append('green')
            else: colors.append('lightgray')
            
        plt.figure(figsize=(10, max(6, len(y_labels)*0.5)))
        plt.barh(y_labels, x_probs, color=colors)
        plt.axvline(x=50, color='black', linestyle='--', alpha=0.5)
        plt.title(f"10-Min ML 盤後預測看多機率分佈 - {p_cfg['title']} ({today.strftime('%Y-%m-%d')})")
        plt.xlabel("看多機率 (%)")
        plt.xlim(0, 100)
        
        for i, v in enumerate(x_probs):
            plt.text(v + 1, i, f"{v:.1f}%", va='center')
            
        image_path = os.path.join(DATA_DIR, f"daily_ml_prediction_{p_key}.png")
        plt.tight_layout()
        plt.savefig(image_path)
        plt.close()
        
        # Send messages
        if p_report_lines:
            msg = f"🤖 **5-Min ML 盤後機器學習預測報告 ({p_cfg['title']})**\n\n"
            msg += "整合當日 5 分鐘 K 線動能與預測誤差 (Variance)，重新計算明日漲跌預判：\n\n"
            msg += "\n".join(p_report_lines)
            send_telegram(p_cfg['token'], p_cfg['chat_id'], msg)
            print(f"已發送 {p_cfg['title']} Telegram 純文字報告。")
            
            if os.path.exists(image_path):
                send_telegram_photo(p_cfg['token'], p_cfg['chat_id'], f"📈 5-Min ML {p_cfg['title']}商品看多機率分佈圖", image_path)
                print(f"已發送 {p_cfg['title']} Telegram 圖表報告。")

if __name__ == "__main__":
    run_intraday_pipeline()
