import os
import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib

MODEL_DIR = os.path.expanduser("~/.hermes/models")
MODEL_FILE = os.path.join(MODEL_DIR, "intraday_model.pkl")

# Core target symbols for generic training (20 key stocks)
CORE_SYMBOLS = [
    "2330.TW", "2454.TW", "3037.TW", "2382.TW", "2327.TW",
    "8996.TW", "5289.TWO", "4966.TWO", "3583.TW", "8210.TW",
    "5347.TWO", "6510.TWO", "3211.TWO", "6290.TWO", "6669.TW",
    "1513.TW", "2049.TW", "2408.TW", "2313.TW", "6285.TW"
]

def train_model():
    print("--- 啟動歷史 10 分鐘 K 線預訓練引擎 (Pre-training) ---")
    print(f"目標股票數量：{len(CORE_SYMBOLS)}")
    
    all_X = []
    all_y = []
    
    for symbol in CORE_SYMBOLS:
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
                
            # Group into 5-minute bins
            df['5m_bin'] = df['timestamp'].dt.floor('5min')
            df['date'] = df['timestamp'].dt.date
            
            grouped = df.groupby(['date', '5m_bin']).agg({
                'Close': 'last',
                'Volume': 'sum'
            }).reset_index()
            
            # Iterate through days to simulate rolling prediction & variance
            dates = sorted(grouped['date'].unique())
            
            prev_pred_prob = 0.5
            import pandas_ta_classic as ta
            
            for i in range(len(dates) - 1):
                today = dates[i]
                tomorrow = dates[i+1]
                
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
                
                # Variance Calculation
                # Actual return today
                actual_today_pct = (prices[-1] - prices[0]) / prices[0]
                predicted_today_pct = (prev_pred_prob - 0.5) * 2.0
                var = actual_today_pct - predicted_today_pct
                
                features.append(var)
                
                # Label formulation: Will tomorrow's close be higher than today's close?
                tomorrow_close = tomorrow_data['Close'].values[-1]
                label = 1 if tomorrow_close > prices[-1] else 0
                
                all_X.append(features)
                all_y.append(label)
                
                # Simulate a simple prediction for the NEXT day's variance
                # In real scenario this would be from model.predict_proba
                # For training simulation, we use label as a strong proxy or just naive 0.5
                prev_pred_prob = 0.55 if label == 1 else 0.45

        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue

    if not all_X:
        print("未成功萃取到任何特徵！")
        return
        
    print(f"特徵萃取完成，總樣本數：{len(all_X)}")
    
    print("正在訓練 Random Forest 分類器...")
    model = RandomForestClassifier(n_estimators=150, max_depth=10, min_samples_leaf=3, random_state=42)
    model.fit(all_X, all_y)
    
    # Calculate Training Accuracy
    preds = model.predict(all_X)
    acc = accuracy_score(all_y, preds)
    print(f"模型訓練完成！訓練集預測準確率 (Accuracy): {acc*100:.2f}%")
    
    # Save Model
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_FILE)
    print(f"模型已成功匯出至 {MODEL_FILE}")

if __name__ == "__main__":
    train_model()
