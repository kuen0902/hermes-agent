import os
import pandas as pd
import pandas_ta as ta
import joblib
import json
from datetime import datetime

# Configuration
DATA_DIR = os.path.expanduser("~/Documents/StockData_History_Final")
MODEL_DIR = os.path.expanduser("~/.hermes/models")
OUTPUT_FILE = os.path.expanduser("~/.hermes/data/ml_signals.json")

def generate_signals():
    print("--- AI Architect: ML Signal Inference ---")
    
    # Load Models
    try:
        model_buy = joblib.load(os.path.join(MODEL_DIR, "buy_signal_v1.pkl"))
        model_sell = joblib.load(os.path.join(MODEL_DIR, "sell_signal_v1.pkl"))
        with open(os.path.join(MODEL_DIR, "model_meta.json"), 'r') as f:
            meta = json.load(f)
            feature_cols = meta["features"]
    except Exception as e:
        print(f"Failed to load models: {e}")
        return

    all_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    signals = {"buy": [], "sell": [], "generated_at": datetime.now().isoformat()}

    for filename in all_files:
        path = os.path.join(DATA_DIR, filename)
        try:
            df = pd.read_csv(path)
            if len(df) < 70: continue
            
            # Prepare latest data point
            # 1. Indicators
            df['SMA_20'] = ta.sma(df['Close'], length=20)
            df['SMA_60'] = ta.sma(df['Close'], length=60)
            df['EMA_12'] = ta.ema(df['Close'], length=12)
            df['EMA_26'] = ta.ema(df['Close'], length=26)
            df['RSI_14'] = ta.rsi(df['Close'], length=14)
            macd = ta.macd(df['Close'])
            if macd is not None:
                df = pd.concat([df, macd], axis=1)
            df['ATR_14'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            df['VOL_SMA_20'] = ta.sma(df['Volume'], length=20)
            df['Vol_Ratio'] = df['Volume'] / (df['VOL_SMA_20'] + 1e-9)
            df['Ret_1'] = df['Close'].pct_change(1)
            df['Ret_5'] = df['Close'].pct_change(5)
            
            latest = df.iloc[[-1]]
            X = latest[feature_cols]
            
            # Prediction
            prob_buy = model_buy.predict_proba(X)[0][1]
            prob_sell = model_sell.predict_proba(X)[0][1]
            
            # Signal Detection threshold (70%)
            ticker_info = filename.replace(".csv", "").split("_")
            symbol = ticker_info[0]
            name = ticker_info[1] if len(ticker_info) > 1 else symbol
            
            if prob_buy > 0.75:
                signals["buy"].append({
                    "symbol": symbol, "name": name, 
                    "confidence": f"{prob_buy*100:.1f}%",
                    "price": float(latest['Close'].iloc[0])
                })
            elif prob_sell > 0.75:
                signals["sell"].append({
                    "symbol": symbol, "name": name, 
                    "confidence": f"{prob_sell*100:.1f}%",
                    "price": float(latest['Close'].iloc[0])
                })
                
        except Exception as e:
            continue

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(signals, f, indent=2, ensure_ascii=False)
    
    print(f"Signal inference complete. Buy: {len(signals['buy'])}, Sell: {len(signals['sell'])}")

if __name__ == "__main__":
    generate_signals()
