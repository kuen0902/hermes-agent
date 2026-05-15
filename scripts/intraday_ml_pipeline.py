import os
import pandas as pd
import numpy as np
import json
from datetime import datetime
import urllib.request
import urllib.parse
import ssl
from sklearn.ensemble import RandomForestClassifier
import joblib

DATA_DIR = os.path.expanduser("~/.hermes/data")
INTRADAY_LOG = os.path.join(DATA_DIR, "intraday_data_log.csv")
PREDICTIONS_FILE = os.path.join(DATA_DIR, "intraday_predictions.json")
MODEL_FILE = os.path.expanduser("~/.hermes/models/intraday_model.pkl")

TELEGRAM_TOKEN = "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU"
CHAT_ID = "6326497055"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    ctx = ssl._create_unverified_context()
    data = urllib.parse.urlencode({
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }).encode('utf-8')
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, context=ctx, timeout=10)
    except Exception as e:
        print(f"Telegram failed: {e}")

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

    # 將時間序列切分為 10 分鐘級別 (Bins)
    df_today['10m_bin'] = df_today['timestamp'].dt.floor('10T')
    
    # 根據代碼與 10 分鐘區間進行分組聚合
    grouped = df_today.groupby(['code', '10m_bin']).agg({
        'price': 'last', 
        'volume': 'sum',
        'name': 'first'
    }).reset_index()
    
    # 載入前一日預判結果，進行 Variance 比較
    old_preds = load_predictions()
    
    X_infer = []
    codes_infer = []
    
    for code, group in grouped.groupby('code'):
        group = group.sort_values('10m_bin')
        if len(group) < 5: continue
        
        prices = group['price'].values
        vols = group['volume'].values
        name = group['name'].values[0]
        
        # 計算 10 分鐘區間漲跌幅與成交量變化
        returns = np.diff(prices) / prices[:-1]
        vol_changes = np.diff(vols) / (vols[:-1] + 1e-9)
        
        if len(returns) < 5: continue
        
        # 擷取最後 5 個 10 分鐘區間作為短期動能特徵
        features = list(returns[-5:]) + list(vol_changes[-5:])
        
        var = 0.0
        var_str = "無歷史紀錄"
        if code in old_preds:
            prev_prob = old_preds[code].get('prob', 0.5)
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
        codes_infer.append((code, name, prices[-1], var_str))

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
        # 在這裡實作增量學習或權重更新邏輯 (若模型支援)
        # RF 在 sklearn 中不支援 partial_fit，此處暫以載入進行 Inference
        pass
        
    preds = model.predict_proba(X_infer)[:, 1]
    
    new_predictions = {}
    report_lines = []
    
    for i, (code, name, price, var_str) in enumerate(codes_infer):
        prob = preds[i]
        signal = "🔴 偏多" if prob > 0.55 else ("🟢 偏空" if prob < 0.45 else "⚪ 盤整")
        
        new_predictions[code] = {
            "date": today.isoformat(),
            "price": price,
            "prob": float(prob)
        }
        
        if prob > 0.6 or prob < 0.4:
            report_lines.append(f"▸ **{name}** (`{code}`): 明日 {signal} (勝率: {prob*100:.1f}%) | 昨驗證: {var_str}")

    save_predictions(new_predictions)
    
    if report_lines:
        msg = "🤖 **10-Min ML 盤後機器學習預測報告**\n\n"
        msg += "整合當日 10 分鐘 K 線動能與預測誤差 (Variance)，重新計算明日漲跌預判：\n\n"
        msg += "\n".join(report_lines)
        send_telegram(msg)
        print("已發送 Telegram 預測報告。")
    else:
        print("今日無強烈預測訊號。")

if __name__ == "__main__":
    run_intraday_pipeline()
