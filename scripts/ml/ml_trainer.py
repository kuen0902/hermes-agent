import os
import pandas as pd
import pandas_ta_classic as ta
import numpy as np
import xgboost as xgb
import joblib
from datetime import datetime

# Configuration
DATA_DIR = os.path.expanduser("~/Documents/StockData_History_Final")
MODEL_DIR = os.path.expanduser("~/.hermes/models")
os.makedirs(MODEL_DIR, exist_ok=True)

def prepare_features(df):
    """Generate technical indicators using pandas-ta."""
    if len(df) < 60: return None
    
    # Copy to avoid warnings
    df = df.copy()
    
    # 1. Trend Indicators
    df['SMA_20'] = ta.sma(df['Close'], length=20)
    df['SMA_60'] = ta.sma(df['Close'], length=60)
    df['EMA_12'] = ta.ema(df['Close'], length=12)
    df['EMA_26'] = ta.ema(df['Close'], length=26)
    
    # 2. Momentum Indicators
    df['RSI_14'] = ta.rsi(df['Close'], length=14)
    # MACD
    macd = ta.macd(df['Close'])
    if macd is not None:
        df = pd.concat([df, macd], axis=1)  # type: ignore
    
    # 3. Volatility & Volume
    df['ATR_14'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    df['VOL_SMA_20'] = ta.sma(df['Volume'], length=20)
    df['Vol_Ratio'] = df['Volume'] / df['VOL_SMA_20']
    
    # 4. Custom Returns
    df['Ret_1'] = df['Close'].pct_change(1)
    df['Ret_5'] = df['Close'].pct_change(5)
    
    # Target: 5-day Forward Return > 3%
    df['Target_Buy'] = (df['Close'].shift(-5) > df['Close'] * 1.03).astype(int)
    # Target: 5-day Forward Return < -3%
    df['Target_Sell'] = (df['Close'].shift(-5) < df['Close'] * 0.97).astype(int)
    
    return df.dropna()

def train_global_model():
    print("--- AI Architect: ML Model Training Sync ---")
    all_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    
    # Training on a representative sample to build a 'Global Signal Engine'
    # Focused on popular stocks for higher signal quality
    seed_tickers = ["2330", "2454", "3037", "2317", "2382", "2603", "2609", "2408", "3231", "1513"]
    train_files = []
    for f in all_files:
        if any(s in f for s in seed_tickers):
            train_files.append(f)
    
    full_data = []
    for filename in train_files:
        path = os.path.join(DATA_DIR, filename)
        df = pd.read_csv(path)
        feat_df = prepare_features(df)
        if feat_df is not None:
            full_data.append(feat_df)
    
    if not full_data:
        print("Insufficient data for training.")
        return
        
    training_set = pd.concat(full_data)
    
    feature_cols = [
        'SMA_20', 'SMA_60', 'EMA_12', 'EMA_26', 'RSI_14', 
        'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9',
        'ATR_14', 'Vol_Ratio', 'Ret_1', 'Ret_5'
    ]
    
    # Ensure all columns exist
    feature_cols = [c for c in feature_cols if c in training_set.columns]
    
    X = training_set[feature_cols]
    y_buy = training_set['Target_Buy']
    y_sell = training_set['Target_Sell']
    
    print(f"Training on {len(training_set)} samples with {len(feature_cols)} features...")
    
    # Train Buy Model
    model_buy = xgb.XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42)
    model_buy.fit(X, y_buy)
    joblib.dump(model_buy, os.path.join(MODEL_DIR, "buy_signal_v1.pkl"))
    
    # Train Sell Model
    model_sell = xgb.XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42)
    model_sell.fit(X, y_sell)
    joblib.dump(model_sell, os.path.join(MODEL_DIR, "sell_signal_v1.pkl"))
    
    with open(os.path.join(MODEL_DIR, "model_meta.json"), 'w') as f:
        json.dump({"features": feature_cols, "updated_at": datetime.now().isoformat()}, f)
    
    print("Models trained and saved to ~/.hermes/models/")

if __name__ == "__main__":
    import json
    train_global_model()
