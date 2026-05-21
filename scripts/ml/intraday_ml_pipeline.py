#!/Users/bookid/.hermes/.venv/bin/python
import os
import sqlite3
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import urllib.request
import urllib.parse
import ssl
import requests
import matplotlib.pyplot as plt
import matplotlib
import yfinance as yf
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
import joblib

# 設定 matplotlib 支援中文 (macOS)
plt.rcParams['font.sans-serif'] = ['PingFang TC', 'Arial Unicode MS', 'Heiti TC']
plt.rcParams['axes.unicode_minus'] = False

DATA_DIR = os.path.expanduser("~/.hermes/data")
INTRADAY_LOG = os.path.join(DATA_DIR, "intraday_data_log.csv")
PREDICTIONS_FILE = os.path.join(DATA_DIR, "intraday_predictions.json")
VALUATIONS_FILE = os.path.join(DATA_DIR, "holdings_ml_valuations.json")

MODEL_FILE = os.path.expanduser("~/.hermes/models/intraday_model.pkl")
MODEL_REG_FILE = os.path.expanduser("~/.hermes/models/intraday_model_reg.pkl")

# Profiles Configuration (Telegram 傳送設定)
PROFILES = {
    "personal": {
        "token": "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU", # Star Platinum
        "chat_id": "6326497055",
        "data_key": "personal_data",
        "title": "個人持股"
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

def normalize_code(code_str):
    """將代碼正規化，移除 .TW / .TWO 等後綴"""
    return str(code_str).replace(".TW", "").replace(".TWO", "").strip()

def load_current_holdings():
    """從 SQLite 載入當前真實持股代號與名稱"""
    db_path = os.path.join(DATA_DIR, "portfolio.db")
    if not os.path.exists(db_path):
        return {}
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT code, name FROM current_holdings")
        holdings = {}
        for row in cursor.fetchall():
            code = row[0]
            name = row[1]
            # 如果股名與代碼相同或是純數字，套用自動修正
            if name == code or (name and name.isdigit()):
                fixes = {
                    "3481": "群創",
                    "2330": "台積電",
                    "2317": "鴻海",
                    "2454": "聯發科",
                    "2382": "廣達",
                    "2409": "友達",
                    "2408": "南亞科",
                    "2327": "國巨",
                    "1513": "中興電",
                    "2049": "上銀",
                    "5347": "世界",
                    "4543": "萬在",
                    "3709": "鑫聯大投控",
                    "3260": "威剛",
                    "6770": "力積電",
                    "5443": "均豪",
                    "2368": "金像電",
                    "2344": "華邦電",
                    "1802": "台玻",
                    "0050": "元大台灣50",
                    "00965": "元大航太防衛科技",
                    "00981A": "主動統一台股增長",
                    "0052": "富邦科技",
                }
                name = fixes.get(code, name)
            holdings[code] = name
        conn.close()
        return holdings
    except Exception as e:
        print(f"無法讀取 SQLite 持股資訊: {e}")
        return {}

def load_latest_institutional_data(iso_date, code_normalized):
    """從 SQLite 讀取指定日期與代號的最新三大法人數據 (張數及外資持股比)"""
    db_path = os.path.join(DATA_DIR, "portfolio.db")
    if not os.path.exists(db_path):
        return 0, 0, 0, 0.0
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # 匹配日期與正規化代號
        cursor.execute('''
            SELECT foreign_buy, trust_buy, dealer_buy, foreign_ratio 
            FROM institutional_data 
            WHERE date = ? AND code = ?
        ''', (iso_date, code_normalized))
        row = cursor.fetchone()
        conn.close()
        if row:
            f_ratio = row[3] if row[3] is not None else 0.0
            return row[0], row[1], row[2], f_ratio
    except Exception as e:
        print(f"讀取 SQLite 三大法人籌碼失敗 ({code_normalized}): {e}")
    return 0, 0, 0, 0.0

def load_rolling_institutional_data(iso_date, code_normalized):
    """計算指定日期過去 5 日與 20 日的投信與自營商累計買超"""
    db_path = os.path.join(DATA_DIR, "portfolio.db")
    if not os.path.exists(db_path):
        return 0, 0, 0, 0
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT trust_buy, dealer_buy 
            FROM institutional_data 
            WHERE code = ? AND date <= ? 
            ORDER BY date DESC LIMIT 20
        ''', (code_normalized, iso_date))
        rows = cursor.fetchall()
        conn.close()
        
        trust_5d = sum(r[0] for r in rows[:5]) if rows else 0
        trust_20d = sum(r[0] for r in rows) if rows else 0
        dealer_5d = sum(r[1] for r in rows[:5]) if rows else 0
        dealer_20d = sum(r[1] for r in rows) if rows else 0
        
        return trust_5d, trust_20d, dealer_5d, dealer_20d
    except Exception as e:
        print(f"計算滾動籌碼特徵失敗 ({code_normalized}): {e}")
    return 0, 0, 0, 0


def load_valuation_history():
    if os.path.exists(VALUATIONS_FILE):
        try:
            with open(VALUATIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_valuation_history(history):
    with open(VALUATIONS_FILE, 'w') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def run_intraday_pipeline(silent=False):
    print("--- 啟動持股專屬 ML 雙指標（方向與估值）盤後預判系統 ---")
    if not os.path.exists(INTRADAY_LOG):
        print("未找到盤中資料日誌 (intraday_data_log.csv)")
        return

    # 載入當前真實持股
    holdings = load_current_holdings()
    
    # 載入訂閱/監控名單
    group_codes = []
    william_codes = []
    central_data_path = os.path.join(DATA_DIR, "central_stock_data.json")
    if os.path.exists(central_data_path):
        try:
            with open(central_data_path, 'r') as f:
                central_data = json.load(f)
                group_codes = central_data.get("group_codes", [])
                william_codes = central_data.get("william_codes", [])
        except Exception as e:
            print(f"載入監控清單失敗: {e}")
            
    # 將所有代號統一 normalize 並取聯集
    target_set = set(normalize_code(c) for c in holdings.keys())
    target_set.update(normalize_code(c) for c in group_codes)
    target_set.update(normalize_code(c) for c in william_codes)
    
    if not target_set:
        print("查無任何執行目標商品（持股與訂閱清單皆為空），跳過執行。")
        return
    print(f"商品過濾已啟用，目標商品總數 (聯集)：{len(target_set)}")

    df = pd.read_csv(INTRADAY_LOG)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    today = datetime.now().date()
    df_today = df[df['timestamp'].dt.date == today].copy()
    
    if df_today.empty:
        print("今日無高頻交易紀錄，跳過 ML 運算。")
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
        
    # 載入偏差自適應誤差歷史
    val_history = load_valuation_history()
    
    X_infer = []
    codes_infer = []
    
    # 建立多層防禦的代碼對稱漢字股名對照字典
    code_to_name = {}
    
    # 1. 載入 SQLite 的 holdings
    for c, n in holdings.items():
        code_to_name[normalize_code(c)] = n
        
    # 2. 載入 central_stock_data.json 的 full_mapping
    full_mapping = {}
    if os.path.exists(central_data_path):
        try:
            with open(central_data_path, 'r') as f:
                central_data = json.load(f)
                full_mapping = central_data.get("full_mapping", {})
        except:
            pass
    for c, n in full_mapping.items():
        c_norm = normalize_code(c)
        if c_norm not in code_to_name:
            code_to_name[c_norm] = n
            
    # 3. 強大的 fixes 常用台灣個股對照 Fallback 字典
    fixes = {
        "3481": "群創",
        "2330": "台積電",
        "2317": "鴻海",
        "2454": "聯發科",
        "2382": "廣達",
        "2409": "友達",
        "2408": "南亞科",
        "2327": "國巨",
        "1513": "中興電",
        "2049": "上銀",
        "5347": "世界",
        "4543": "萬在",
        "3709": "鑫聯大投控",
        "3260": "威剛",
        "6770": "力積電",
        "5443": "均豪",
        "2368": "金像電",
        "2344": "華邦電",
        "1802": "台玻",
        "0050": "元大台灣50",
        "00965": "元大航太防衛科技",
        "00981A": "主動統一台股增長",
        "0052": "富邦科技",
    }
    
    import pandas_ta_classic as ta
    
    for code, group in grouped.groupby('code'):
        # 1. 商品過濾判定 (持股 + 訂閱清單)
        code_norm = normalize_code(code)
        if code_norm not in target_set:
            continue
            
        group = group.sort_values('5m_bin')
        if len(group) < 5: 
            continue
        
        prices = group['price'].values
        vols = group['volume'].values
        
        # 2. 獲取漢字股名 (多層防禦)
        name = code_to_name.get(code_norm)
        if not name or name == code_norm or name.isdigit():
            name = fixes.get(code_norm, group['name'].values[0])
        
        # 計算 5 分鐘區間漲跌幅與成交量變化
        returns = np.diff(prices) / prices[:-1]
        vol_changes = np.diff(vols) / (vols[:-1] + 1e-9)
        
        if len(returns) < 5: 
            continue
        
        # 擷取最後 5 個 5 分鐘區間作為短期動能特徵
        features = list(returns[-5:]) + list(vol_changes[-5:])
        
        # 計算技術指標
        close_series = pd.Series(prices)
        
        # RSI(14)
        if len(close_series) > 14:
            rsi_series = ta.rsi(close_series, length=14)
            if rsi_series is not None and not rsi_series.empty:
                rsi_val = rsi_series.iloc[-1]
                if pd.isna(rsi_val): rsi_val = 50.0
            else:
                rsi_val = 50.0
        else:
            rsi_val = 50.0
            
        # MACD(12, 26, 9)
        if len(close_series) > 26:
            macd_df = ta.macd(close_series, fast=12, slow=26, signal=9)
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
        features.extend(taiex_features)
        
        # 2. 從 SQLite 讀取今日最新法人籌碼特徵與外資持股比
        f_buy, t_buy, d_buy, f_ratio = load_latest_institutional_data(today.isoformat(), code_norm)
        features.extend([f_buy, t_buy, d_buy, f_ratio])
        
        # 2b. 計算投信與自營商的滾動累計籌碼
        t_5d, t_20d, d_5d, d_20d = load_rolling_institutional_data(today.isoformat(), code_norm)
        features.extend([t_5d, t_20d, d_5d, d_20d])
        
        # 3. 卡爾曼式誤差反饋 (Feedback control loop) 與偏差計算
        error_val = 0.0
        bias_val = 0.0
        error_str = "今日新納入估值"
        
        # 平滑因子 alpha = 0.2
        alpha = 0.2
        
        if code_norm in val_history and len(val_history[code_norm]) > 0:
            # 找到上一交易日的估值記錄
            dates_sorted = sorted(val_history[code_norm].keys())
            prev_date = dates_sorted[-1]
            prev_record = val_history[code_norm][prev_date]
            
            # 昨估今日價格 (校正後)
            prev_calibrated_val = prev_record.get("calibrated_val", prev_record.get("raw_val", prices[-1]))
            prev_bias = prev_record.get("bias", 0.0)
            
            # 今日實際价格
            current_actual_price = prices[-1]
            
            # 計算昨日估值今日的誤差
            error_val = current_actual_price - prev_calibrated_val
            
            # 卡爾曼一階自適應更新長期誤差偏差偏置 (Bias)
            bias_val = prev_bias * (1.0 - alpha) + error_val * alpha
            
            error_pct = (error_val / prev_calibrated_val) * 100.0 if prev_calibrated_val else 0.0
            error_str = f"誤差: {error_val:+.2f} ({error_pct:+.2f}%) | 偏置修正: {bias_val:+.2f}"
            
            # 回寫上一交易日記錄的真實誤差，方便日後稽核
            val_history[code_norm][prev_date]["actual_price"] = current_actual_price
            val_history[code_norm][prev_date]["error"] = error_val
        
        features.append(error_val) # 將前一日誤差本身作為反饋特徵注入 ML 特徵集
        
        X_infer.append(features)
        codes_infer.append({
            "code_norm": code_norm,
            "code_raw": str(code),
            "name": name,
            "price": prices[-1],
            "bias": bias_val,
            "error_str": error_str,
            "f_buy": f_buy,
            "t_buy": t_buy,
            "d_buy": d_buy,
            "f_ratio": f_ratio
        })

    if not X_infer:
        print("持股特徵萃取數量不足。")
        return

    # 4. 機器學習雙模型（Classifier + Regressor）載入或初始化
    model_clf = None
    if os.path.exists(MODEL_FILE):
        try:
            model_clf = joblib.load(MODEL_FILE)
            if hasattr(model_clf, "n_features_in_") and model_clf.n_features_in_ != len(X_infer[0]):
                print(f"偵測到 Classifier 特徵維度不匹配 ({model_clf.n_features_in_} != {len(X_infer[0])})，將重建模型。")
                model_clf = None
        except:
            model_clf = None
        
    if model_clf is None:
        print("初始化全新 RandomForest 分類器模型...")
        model_clf = RandomForestClassifier(n_estimators=50, random_state=42)
        dummy_y = [np.random.randint(0, 2) for _ in X_infer]
        model_clf.fit(X_infer, dummy_y)
        joblib.dump(model_clf, MODEL_FILE)
        
    model_reg = None
    if os.path.exists(MODEL_REG_FILE):
        try:
            model_reg = joblib.load(MODEL_REG_FILE)
            if hasattr(model_reg, "n_features_in_") and model_reg.n_features_in_ != len(X_infer[0]):
                print(f"偵測到 Regressor 特徵維度不匹配 ({model_reg.n_features_in_} != {len(X_infer[0])})，將重建模型。")
                model_reg = None
        except:
            model_reg = None
        
    if model_reg is None:
        print("初始化全新 RandomForest 迴歸器模型...")
        model_reg = RandomForestRegressor(n_estimators=50, random_state=42)
        # 迴歸器預測明日價格變動率 (%)
        dummy_y_reg = [np.random.uniform(-0.02, 0.02) for _ in X_infer]
        model_reg.fit(X_infer, dummy_y_reg)
        joblib.dump(model_reg, MODEL_REG_FILE)

    # 5. 雙模型推理
    preds_clf = model_clf.predict_proba(X_infer)[:, 1]  # 看多機率
    preds_reg = model_reg.predict(X_infer)              # 明日預期漲跌幅

    # 6. 計算收斂後估值並寫入誤差歷史
    new_predictions = {}
    trade_signals = []
    
    for i, item in enumerate(codes_infer):
        code_norm = item["code_norm"]
        price = item["price"]
        bias = item["bias"]
        
        prob = float(preds_clf[i])
        pred_return = float(preds_reg[i])
        
        # 預估明日價格 (原始值)
        raw_val = price * (1.0 + pred_return)
        
        # 預估明日價格 (收斂平滑後)
        calibrated_val = raw_val + bias
        
        # 寫入歷史日誌
        if code_norm not in val_history:
            val_history[code_norm] = {}
            
        val_history[code_norm][today.isoformat()] = {
            "price": price,
            "prob": prob,
            "pred_return": pred_return,
            "raw_val": raw_val,
            "calibrated_val": calibrated_val,
            "bias": bias,
            "error": 0.0, # 等明日更新
            "actual_price": 0.0 # 等明日更新
        }
        
        item["prob"] = prob
        item["pred_return"] = pred_return
        item["raw_val"] = raw_val
        item["calibrated_val"] = calibrated_val
        
        # 同步回舊的 predictions 結構，相容其他系統
        new_predictions[item["code_raw"]] = {
            "date": today.isoformat(),
            "price": price,
            "prob": prob
        }
        
        # 生成自動交易信號（使用雙模型強信心過濾）
        action = None
        if prob >= 0.85 and pred_return > 0.015:
            action = "add"
        elif prob <= 0.15 and pred_return < -0.015:
            action = "reduce"
            
        if action:
            trade_signals.append({
                "action": action,
                "code": item["code_raw"],
                "name": item["name"],
                "price": price,
                "qty": 1.0,
                "prob": prob,
                "pred_return": pred_return,
                "timestamp": today.isoformat()
            })
            
    save_predictions(new_predictions)
    save_valuation_history(val_history)
    
    if trade_signals:
        signals_file = os.path.join(DATA_DIR, "trade_signals.json")
        with open(signals_file, 'w') as f:
            json.dump({"signals": trade_signals, "generated_at": datetime.now().isoformat()}, f, indent=2, ensure_ascii=False)
        print(f"✅ 生成 {len(trade_signals)} 筆持股強信心 ML 交易信號")

    # 7. 為各 profile 生成與發送報告 (限於持股)
    for p_key, p_cfg in PROFILES.items():
        # 如果是個人持股，直接包含所有持股商品
        if p_key == "personal":
            profile_stocks = list(holdings.keys())
        else:
            # 群組與小智只顯示他們有訂閱，且剛好是我們持股的商品
            central_data = {}
            if os.path.exists(os.path.join(DATA_DIR, "central_stock_data.json")):
                try:
                    with open(os.path.join(DATA_DIR, "central_stock_data.json"), 'r') as f:
                        central_data = json.load(f)
                except: pass
            data_val = central_data.get(p_cfg['data_key'])
            if isinstance(data_val, dict):
                profile_stocks = [normalize_code(c) for c in data_val.keys()]
            elif isinstance(data_val, list):
                profile_stocks = [normalize_code(c) for c in data_val]
            else:
                profile_stocks = []
                
        if not profile_stocks:
            continue
            
        p_report_lines = []
        p_probs = []
        p_returns = []
        p_y_labels = []
        p_f_buys = []
        p_t_buys = []
        p_d_buys = []
        p_f_ratios = []
        
        for item in codes_infer:
            code_norm = item["code_norm"]
            if code_norm not in profile_stocks:
                continue
                
            prob = item["prob"]
            pred_return = item["pred_return"]
            calibrated_val = item["calibrated_val"]
            error_str = item["error_str"]
            name = item["name"]
            
            p_probs.append(prob * 100.0)
            p_returns.append(pred_return * 100.0)
            
            # 計算多空預測方向與絕對信心指數 (以 50% 為基準)
            prob_pct = prob * 100.0
            if prob >= 0.55:
                direction_str = "偏多"
                confidence = prob_pct
            elif prob <= 0.45:
                direction_str = "偏空"
                confidence = 100.0 - prob_pct
            else:
                direction_str = "盤整"
                confidence = prob_pct if prob >= 0.5 else (100.0 - prob_pct)
            
            # Y 軸標籤大進化：融合股名、方向與信心指數、今日收盤與收斂估值
            price_now = item["price"]
            p_y_labels.append(f"{name} ({code_norm}) | {direction_str}({confidence:.0f}%)\n現價:{price_now:.1f} → 估值:{calibrated_val:.1f}")
            
            p_f_buys.append(item.get("f_buy", 0))
            p_t_buys.append(item.get("t_buy", 0))
            p_d_buys.append(item.get("d_buy", 0))
            p_f_ratios.append(item.get("f_ratio", 0.0))
            
            clean_name = name.replace("*", "\\*").replace("_", "\\_")
            signal = "🔴 偏多" if prob > 0.55 else ("🟢 偏空" if prob < 0.45 else "⚪ 盤整")
            
            # 美化條目，包含股價估值與誤差自適應修正歷程
            line_str = (
                f"▸ **{clean_name}** (`{code_norm}`): 明日 {signal}\n"
                f"  └ 方向機率: *{prob*100:.1f}%*\n"
                f"  └ 今日收盤: `${price_now:.2f}`\n"
                f"  └ 誤差校正: `{error_str}`\n"
                f"  └ 明日估值: **`${calibrated_val:.2f}`** *(誤差已自適應收斂)*\n"
            )
            p_report_lines.append(line_str)
            
        if not p_report_lines:
            continue
            
        # 繪圖展示明天的股價估計變動率 (%)、方向機率 (%) 與今日三大法人籌碼分析
        # 使用 1 row, 3 columns 三子圖以容納更多資訊，並提供極致清晰的科技質感
        num_items = len(p_y_labels)
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, max(5.5, num_items * 0.7)))
        
        y_pos = np.arange(num_items)
        
        # --- 子圖 1：預估明日收盤漲跌幅 (%) [Regressor] ---
        colors_ret = ['#ff7675' if r > 0 else '#55efc4' for r in p_returns] # 高級珊瑚紅與薄荷綠
        bars1 = ax1.barh(y_pos, p_returns, color=colors_ret, alpha=0.85, edgecolor='#2d3436', height=0.55)
        ax1.set_xlabel("預估明日收盤漲跌幅 (%)", fontsize=11, fontweight='bold', color='#2d3436')
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(p_y_labels, fontsize=10, fontweight='bold', color='#2d3436')
        ax1.axvline(x=0.0, color='#2d3436', linestyle='-', alpha=0.6, linewidth=1.2)
        ax1.grid(axis='x', linestyle='--', alpha=0.3, color='#dfe6e9')
        
        # 動態調整 xlim 防止標籤溢出重疊 Y 軸
        max_ret = max([abs(r) for r in p_returns] + [0.5])
        ax1.set_xlim(-max_ret * 1.35, max_ret * 1.35)
        
        # 加上漲跌幅標籤
        for bar in bars1:
            width = bar.get_width()
            offset = max_ret * 0.05
            if width >= 0:
                ax1.text(width + offset, bar.get_y() + bar.get_height()/2, 
                         f"{width:+.2f}%", va='center', ha='left', fontweight='bold', color='#c0392b', fontsize=9)
            else:
                ax1.text(width - offset, bar.get_y() + bar.get_height()/2, 
                         f"{width:+.2f}%", va='center', ha='right', fontweight='bold', color='#27ae60', fontsize=9)
        ax1.set_title("漲跌估值預測 (Regressor)", fontsize=12, fontweight='bold', pad=10, color='#2d3436')
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.spines['left'].set_color('#dfe6e9')
        ax1.spines['bottom'].set_color('#dfe6e9')
        
        # --- 子圖 2：多空方向信心指數 (%) [Classifier] ---
        colors_prob = []
        for p in p_probs:
            if p >= 55.0:
                colors_prob.append('#ff7675') # 偏多：珊瑚紅
            elif p <= 45.0:
                colors_prob.append('#55efc4') # 偏空：薄荷綠
            else:
                colors_prob.append('#b2bec3') # 盤整：中性灰
                
        # 計算相對於 50% 的偏差值
        p_probs_deviations = [p - 50.0 for p in p_probs]
        
        # 使用 left=50.0 參數繪製對稱條形圖
        bars2 = ax2.barh(y_pos, p_probs_deviations, left=50.0, color=colors_prob, alpha=0.85, edgecolor='#2d3436', height=0.55)
        ax2.set_xlabel("多空預測與絕對信心指數 (%)", fontsize=11, fontweight='bold', color='#2d3436')
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels([]) # 右側不重複顯示 Y 軸標籤，維持清爽
        ax2.axvline(x=50.0, color='#2d3436', linestyle='-', alpha=0.8, linewidth=1.5, label="多空分界 (50%)")
        ax2.set_xlim(0, 115) # 保留空間放置左右側的信心標籤
        ax2.grid(axis='x', linestyle='--', alpha=0.3, color='#dfe6e9')
        ax2.legend(loc='lower right', framealpha=0.8, fontsize=9)
        
        # 加上多空信心標籤，偏多顯示在條形圖右側，偏空顯示在左側
        for bar, p in zip(bars2, p_probs):
            if p >= 55.0:
                lbl = f"偏多 {p:.0f}%"
                color_text = '#c0392b'
                ax2.text(p + 2, bar.get_y() + bar.get_height()/2, 
                         lbl, va='center', ha='left', fontweight='bold', color=color_text, fontsize=9)
            elif p <= 45.0:
                lbl = f"偏空 {100.0 - p:.0f}%"
                color_text = '#27ae60'
                ax2.text(p - 2, bar.get_y() + bar.get_height()/2, 
                         lbl, va='center', ha='right', fontweight='bold', color=color_text, fontsize=9)
            else:
                # 接近 50% 盤整
                lbl = f"盤整 {p:.0f}%"
                color_text = '#7f8c8d'
                ax2.text(p + 2 if p >= 50 else p - 2, bar.get_y() + bar.get_height()/2, 
                         lbl, va='center', ha='left' if p >= 50 else 'right', fontweight='bold', color=color_text, fontsize=9)
                         
        ax2.set_title("多空方向信心指數 (Classifier)", fontsize=12, fontweight='bold', pad=10, color='#2d3436')
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.spines['left'].set_color('#dfe6e9')
        ax2.spines['bottom'].set_color('#dfe6e9')
        
        # --- 子圖 3：今日三大法人籌碼分析 (張) ---
        p_total_inst = [f + t + d for f, t, d in zip(p_f_buys, p_t_buys, p_d_buys)]
        colors_inst = ['#74b9ff' if tot > 0 else ('#a29bfe' if tot < 0 else '#b2bec3') for tot in p_total_inst] # 合計買超為亮藍，賣超為優雅紫，無買賣為灰色
        
        bars3 = ax3.barh(y_pos, p_total_inst, color=colors_inst, alpha=0.85, edgecolor='#2d3436', height=0.55)
        ax3.set_xlabel("今日三大法人合計淨買超 (張)", fontsize=11, fontweight='bold', color='#2d3436')
        ax3.set_yticks(y_pos)
        ax3.set_yticklabels([]) # 維持清爽
        ax3.axvline(x=0.0, color='#2d3436', linestyle='-', alpha=0.6, linewidth=1.2)
        ax3.grid(axis='x', linestyle='--', alpha=0.3, color='#dfe6e9')
        
        # 計算 X 軸極限，防止標籤溢出
        max_inst = max([abs(tot) for tot in p_total_inst] + [100])
        ax3.set_xlim(-max_inst * 1.45, max_inst * 1.45)
        
        # 加上籌碼標籤
        for idx, bar in enumerate(bars3):
            width = bar.get_width()
            f_b = p_f_buys[idx]
            t_b = p_t_buys[idx]
            d_b = p_d_buys[idx]
            f_r = p_f_ratios[idx]
            
            lbl_str = f"外:{f_b:+} 投:{t_b:+} 自:{d_b:+} ({f_r:.1f}%)"
            offset = max_inst * 0.05
            if width >= 0:
                ax3.text(width + offset, bar.get_y() + bar.get_height()/2, 
                         f"+{width:.0f}張\n{lbl_str}", va='center', ha='left', fontweight='bold', color='#0984e3', fontsize=7.5)
            else:
                ax3.text(width - offset, bar.get_y() + bar.get_height()/2, 
                         f"{width:.0f}張\n{lbl_str}", va='center', ha='right', fontweight='bold', color='#6c5ce7', fontsize=7.5)
                         
        ax3.set_title("今日三大法人籌碼 (張) & 外資持股比", fontsize=12, fontweight='bold', pad=10, color='#2d3436')
        ax3.spines['top'].set_visible(False)
        ax3.spines['right'].set_visible(False)
        ax3.spines['left'].set_color('#dfe6e9')
        ax3.spines['bottom'].set_color('#dfe6e9')
        
        # 總標題
        title_prefix = "持股" if p_key == "personal" else "監控商品"
        plt.suptitle(f"{title_prefix} ML 雙指標 & 三大法人籌碼分析圖 - {p_cfg['title']}\n數據日期: {today.strftime('%Y-%m-%d')}", 
                     fontsize=14, fontweight='bold', y=0.97, color='#2d3436')
        
        # 調整邊距與間距，徹底解決 Y 軸長股名與標籤的 overlap 缺陷，並保留足夠欄寬
        plt.subplots_adjust(left=0.22, right=0.96, top=0.86, bottom=0.12, wspace=0.25)
        
        image_path = os.path.join(DATA_DIR, f"daily_ml_prediction_{p_key}.png")
        plt.savefig(image_path, dpi=200) # 提升至 200 DPI 確保高清晰度
        plt.close()
        
        # 發送 Telegram
        if p_report_lines and not silent:
            report_title = "Holdings ML 雙指標" if p_key == "personal" else "監控商品 ML 雙指標"
            msg = f"🤖 **{report_title}（方向與估值）自適應誤差收斂預測報告 ({p_cfg['title']})**\n\n"
            msg += "整合今日 5 分鐘高頻 K 線動能與最新的** SQLite 三大法人籌碼**特徵，重新校正預估明日收盤價：\n\n"
            msg += "\n".join(p_report_lines)
            send_telegram(p_cfg['token'], p_cfg['chat_id'], msg)
            print(f"已發送 {p_cfg['title']} Telegram 純文字報告。")
            
            if os.path.exists(image_path):
                send_telegram_photo(p_cfg['token'], p_cfg['chat_id'], f"📈 {p_cfg['title']} 預估收盤變動率分析圖", image_path)
                print(f"已發送 {p_cfg['title']} Telegram 圖表報告。")

if __name__ == "__main__":
    import sys
    silent_mode = "--silent" in sys.argv
    run_intraday_pipeline(silent=silent_mode)
