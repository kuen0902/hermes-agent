import os
import pandas as pd
import numpy as np
import yfinance as yf
import sqlite3
import duckdb
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score
import joblib

DATA_DIR = os.path.expanduser("~/.hermes/data")
MODEL_DIR = os.path.expanduser("~/.hermes/models")
MODEL_FILE = os.path.join(MODEL_DIR, "intraday_model.pkl")
MODEL_REG_FILE = os.path.join(MODEL_DIR, "intraday_model_reg.pkl")

# Core target symbols for generic training (20 key stocks)
CORE_SYMBOLS = [
    "2330.TW", "2454.TW", "3037.TW", "2382.TW", "2327.TW",
    "8996.TW", "5289.TWO", "4966.TWO", "3583.TW", "8210.TW",
    "5347.TWO", "6510.TWO", "3211.TWO", "6290.TWO", "6669.TW",
    "1513.TW", "2049.TW", "2408.TW", "2313.TW", "6285.TW", "^TWII"
]

def load_symbol_daily_history(symbol):
    """
    載入指定商品（如 2330.TW）的日線歷史關閉價格，
    回傳以 Date 為 Index 的 pandas Series。
    """
    code_norm = symbol.split(".")[0]
    workspace_dir = os.path.expanduser("~/.hermes/data/StockData_History_Final")
    documents_dir = os.path.expanduser("~/Documents/StockData_History_Final")
    
    if os.path.exists(workspace_dir) and len(os.listdir(workspace_dir)) > 0:
        data_dir = workspace_dir
    else:
        data_dir = documents_dir
        
    if not os.path.exists(data_dir):
        return pd.Series(dtype='float64')
        
    match_file = None
    for f in os.listdir(data_dir):
        if f.startswith(f"{code_norm}."):
            match_file = f
            break
            
    if not match_file:
        return pd.Series(dtype='float64')
        
    try:
        df = pd.read_csv(os.path.join(data_dir, match_file))
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df = df.dropna(subset=['Close', 'Date'])
        return pd.Series(df['Close'].values, index=df['Date'])
    except Exception as e:
        print(f"載入歷史日線資料失敗 ({symbol}): {e}")
        return pd.Series(dtype='float64')

def load_latest_institutional_data(iso_date, code_normalized):
    """從 DuckDB 讀取指定日期與代號的最新三大法人數據 (張數及外資持股比)"""
    db_path = os.path.join(DATA_DIR, "portfolio.ddb")
    if not os.path.exists(db_path):
        return 0, 0, 0, 0.0
    try:
        conn = duckdb.connect(db_path)
        cursor = conn.cursor()
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
        pass
    return 0, 0, 0, 0.0

def load_rolling_institutional_data(iso_date, code_normalized):
    """計算指定日期過去 5 日與 20 日的投信與自營商累計買超"""
    db_path = os.path.join(DATA_DIR, "portfolio.ddb")
    if not os.path.exists(db_path):
        return 0, 0, 0, 0
    try:
        conn = duckdb.connect(db_path)
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
        pass
    return 0, 0, 0, 0

def train_model():
    print("--- 啟動歷史 5 分鐘 K 線預訓練引擎 (Pre-training) ---")
    print(f"目標股票數量：{len(CORE_SYMBOLS)}")
    
    # 預先抓取大盤資料
    print("正在抓取大盤 (^TWII) 過去 60 天的 5 分鐘高頻資料...")
    try:
        taiex_df = yf.download("^TWII", period="60d", interval="5m", progress=False)
        if isinstance(taiex_df.columns, pd.MultiIndex):
            taiex_df.columns = taiex_df.columns.get_level_values(0)
        taiex_df = taiex_df[['Close']].dropna().reset_index()
        taiex_df.rename(columns={'Datetime': 'timestamp'}, inplace=True)
        if taiex_df['timestamp'].dt.tz is not None:
            taiex_df['timestamp'] = taiex_df['timestamp'].dt.tz_convert('Asia/Taipei').dt.tz_localize(None)
        taiex_df['5m_bin'] = taiex_df['timestamp'].dt.floor('5min')
        taiex_df['date'] = taiex_df['timestamp'].dt.date
        taiex_grouped = taiex_df.groupby(['date', '5m_bin']).agg({'Close': 'last'}).reset_index()
    except Exception as e:
        print(f"大盤資料抓取失敗: {e}")
        taiex_grouped = pd.DataFrame(columns=['date', '5m_bin', 'Close'])
    
    all_X = []
    all_y_clf = []
    all_y_reg = []
    
    import pandas_ta_classic as ta
    
    for symbol in CORE_SYMBOLS:
        if symbol == "^TWII": continue
        code_norm = symbol.split(".")[0]
        print(f"正在抓取 {symbol} 過去 60 天的 5 分鐘高頻資料...")
        try:
            # Download 60 days of 5-minute data
            df = yf.download(symbol, period="60d", interval="5m", progress=False)
            if df.empty:
                continue
                
            # If yf returns MultiIndex columns, flatten it
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            df = df[['Close', 'Volume']].dropna()
            
            # Reset index to get Datetime as a column
            df = df.reset_index()
            df.rename(columns={'Datetime': 'timestamp'}, inplace=True)
            
            # Ensure timezone-naive for easier processing
            if df['timestamp'].dt.tz is not None:
                df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Taipei').dt.tz_localize(None)
                
            # Group into 5-minute bins for Stocks
            df['5m_bin'] = df['timestamp'].dt.floor('5min')
            df['date'] = df['timestamp'].dt.date
            
            grouped = df.groupby(['date', '5m_bin']).agg({
                'Close': 'last',
                'Volume': 'sum'
            }).reset_index()
            
            # 載入該商品的日線歷史記錄
            daily_history = load_symbol_daily_history(symbol)
            
            # Iterate through days to simulate rolling prediction & variance
            dates = sorted(grouped['date'].unique())
            
            prev_pred_prob = 0.5
            
            for i in range(1, len(dates) - 1):
                today = dates[i]
                tomorrow = dates[i+1]
                
                # 1. 取得今日大盤特徵
                taiex_features = [0.0] * 5
                taiex_day_data = taiex_grouped[taiex_grouped['date'] == today].sort_values('5m_bin')
                if len(taiex_day_data) >= 6:
                    t_prices = taiex_day_data['Close'].values
                    t_returns = np.diff(t_prices) / t_prices[:-1]
                    if len(t_returns) >= 5:
                        taiex_features = list(t_returns[-5:])
                        
                day_data = grouped[grouped['date'] == today].sort_values('5m_bin')
                tomorrow_data = grouped[grouped['date'] == tomorrow].sort_values('5m_bin')
                
                if len(day_data) < 5 or len(tomorrow_data) < 1:
                    continue
                    
                prices = day_data['Close'].values
                vols = day_data['Volume'].values
                
                # 5-min returns & vol changes
                returns = np.diff(prices) / prices[:-1]
                vol_changes = np.diff(vols) / (vols[:-1] + 1e-9)
                
                if len(returns) < 5:
                    continue
                    
                # Feature extraction (last 5 intervals)
                features = list(returns[-5:]) + list(vol_changes[-5:])
                
                # Calculate Technical Indicators
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
                
                # Append TAIEX features
                features.extend(taiex_features)
                
                # 2. 獲取今日最新法人籌碼特徵與外資持股比 (4 維)
                f_buy, t_buy, d_buy, f_ratio = load_latest_institutional_data(today.isoformat(), code_norm)
                features.extend([f_buy, t_buy, d_buy, f_ratio])
                
                # 3. 獲取滾動累計三大法人籌碼特徵 (4 維)
                t_5d, t_20d, d_5d, d_20d = load_rolling_institutional_data(today.isoformat(), code_norm)
                features.extend([t_5d, t_20d, d_5d, d_20d])
                
                # 4. 獲取歷史日線 MA 乖離率與間距 (5MA/10MA/月線/季線/半年線/年線及結構間距)
                hist_before_today = daily_history[daily_history.index < today.isoformat()]
                hist_closes = list(hist_before_today.tail(239).values)
                closes_240d = hist_closes + [prices[-1]]
                n_days = len(closes_240d)
                
                if n_days > 0:
                    ma5 = sum(closes_240d[-min(5, n_days):]) / min(5, n_days)
                    ma10 = sum(closes_240d[-min(10, n_days):]) / min(10, n_days)
                    ma20 = sum(closes_240d[-min(20, n_days):]) / min(20, n_days)
                    ma60 = sum(closes_240d[-min(60, n_days):]) / min(60, n_days)
                    ma120 = sum(closes_240d[-min(120, n_days):]) / min(120, n_days)
                    ma240 = sum(closes_240d) / n_days
                    
                    bias5 = (prices[-1] - ma5) / ma5 if ma5 else 0.0
                    bias10 = (prices[-1] - ma10) / ma10 if ma10 else 0.0
                    bias20 = (prices[-1] - ma20) / ma20 if ma20 else 0.0
                    bias60 = (prices[-1] - ma60) / ma60 if ma60 else 0.0
                    bias120 = (prices[-1] - ma120) / ma120 if ma120 else 0.0
                    bias240 = (prices[-1] - ma240) / ma240 if ma240 else 0.0
                    
                    spread_5_20 = (ma5 - ma20) / ma20 if ma20 else 0.0
                    spread_20_60 = (ma20 - ma60) / ma60 if ma60 else 0.0
                    spread_60_240 = (ma60 - ma240) / ma240 if ma240 else 0.0
                else:
                    bias5 = bias10 = bias20 = bias60 = bias120 = bias240 = 0.0
                    spread_5_20 = spread_20_60 = spread_60_240 = 0.0
                    ma5 = ma20 = ma60 = 0.0
                    
                features.extend([bias5, bias10, bias20, bias60, bias120, bias240, spread_5_20, spread_20_60, spread_60_240])
                
                # 4b. 增加新的絕對價格與均線維度 (4 維)
                features.extend([prices[-1], ma5, ma20, ma60])
                
                # 5. 變異與誤差項計算 (1 維)
                actual_today_pct = (prices[-1] - prices[0]) / prices[0]
                predicted_today_pct = (prev_pred_prob - 0.5) * 2.0
                var = actual_today_pct - predicted_today_pct
                features.append(var)
                
                # 預估目標:
                # 分類器目標: 明日收盤價是否高於今日收盤價
                tomorrow_close = tomorrow_data['Close'].values[-1]
                label = 1 if tomorrow_close > prices[-1] else 0
                
                # 迴歸器目標: 明日收盤價的變動率
                tomorrow_return = (tomorrow_close - prices[-1]) / prices[-1]
                
                all_X.append(features)
                all_y_clf.append(label)
                all_y_reg.append(tomorrow_return)
                
                # 為下一個交易日的變異模擬預測機率
                prev_pred_prob = 0.55 if label == 1 else 0.45

        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue

    if not all_X:
        print("未成功萃取到任何特徵！")
        return
        
    print(f"特徵萃取完成，總樣本數：{len(all_X)}，特徵維度：{len(all_X[0])}")
    
    # 訓練分類器
    print("正在訓練 RandomForest 分類器 (40維)...")
    model_clf = RandomForestClassifier(n_estimators=150, max_depth=10, min_samples_leaf=3, random_state=42)
    model_clf.fit(all_X, all_y_clf)
    
    # 計算分類器訓練集準確率
    preds_clf = model_clf.predict(all_X)
    acc = accuracy_score(all_y_clf, preds_clf)
    print(f"分類器訓練完成！訓練集準確率 (Accuracy): {acc*100:.2f}%")
    
    # 訓練迴歸器
    print("正在訓練 RandomForest 迴歸器 (40維)...")
    model_reg = RandomForestRegressor(n_estimators=150, max_depth=10, min_samples_leaf=3, random_state=42)
    model_reg.fit(all_X, all_y_reg)
    print("迴歸器訓練完成！")
    
    # 儲存雙模型
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model_clf, MODEL_FILE)
    joblib.dump(model_reg, MODEL_REG_FILE)
    print(f"分類器已匯出至 {MODEL_FILE}")
    print(f"迴歸器已匯出至 {MODEL_REG_FILE}")

if __name__ == "__main__":
    train_model()
