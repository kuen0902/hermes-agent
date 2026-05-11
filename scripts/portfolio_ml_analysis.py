import os
import pandas as pd
import pandas_ta as ta
import joblib
import json
from datetime import datetime

# Configuration
DATA_DIR = os.path.expanduser("~/Documents/StockData_History_Final")
MODEL_DIR = os.path.expanduser("~/.hermes/models")
PORTFOLIO_JSON = os.path.expanduser("~/.hermes/data/central_stock_data.json")

def analyze_portfolio():
    print("--- AI Architect: Portfolio ML Deep Dive ---")
    
    # 1. Load Models
    try:
        model_buy = joblib.load(os.path.join(MODEL_DIR, "buy_signal_v1.pkl"))
        model_sell = joblib.load(os.path.join(MODEL_DIR, "sell_signal_v1.pkl"))
        with open(os.path.join(MODEL_DIR, "model_meta.json"), 'r') as f:
            meta = json.load(f)
            feature_cols = meta["features"]
    except Exception as e:
        print(f"Failed to load models: {e}")
        return

    # 2. Load Portfolio
    try:
        with open(PORTFOLIO_JSON, 'r') as f:
            portfolio_data = json.load(f)
        holdings = portfolio_data.get("personal_data", {})
    except Exception as e:
        print(f"Failed to load portfolio: {e}")
        return

    all_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    results = []

    for code, info in holdings.items():
        match_f = None
        # code is "2330", filename is "2330.TW_NAME.csv"
        for f in all_files:
            if f.startswith(code + "."):
                match_f = f
                break
        
        if not match_f: 
            continue
        
        path = os.path.join(DATA_DIR, match_f)
        try:
            df = pd.read_csv(path)
            if len(df) < 70: continue
            
            # Technical Indicators
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
            
            # ML Probs
            prob_buy = model_buy.predict_proba(X)[0][1]
            prob_sell = model_sell.predict_proba(X)[0][1]
            
            current_price = float(latest['Close'].iloc[0])
            avg_cost = float(info.get('avg', 0))
            pnl_pct = ((current_price - avg_cost) / avg_cost) * 100 if avg_cost > 0 else 0
            
            results.append({
                "symbol": code,
                "name": info.get("name", code),
                "price": current_price,
                "cost": avg_cost,
                "pnl": pnl_pct,
                "buy_conf": prob_buy,
                "sell_conf": prob_sell
            })
        except: continue

    # 3. Format Output
    output = [
        f"🎯 **AI Architect: 持股分析報告 (ML Edition)**",
        f"⏰ 分析時間：`{datetime.now().strftime('%Y-%m-%d %H:%M')}`",
        f"----------------------------"
    ]
    
    # Sort results by P/L or Signal? Let's show most critical signals first.
    # We define "Critical" as high buy/sell confidence on current holdings.
    sorted_results = sorted(results, key=lambda x: max(x['buy_conf'], x['sell_conf']), reverse=True)
    
    for r in sorted_results:
        # Determine Signal Label
        signal = "⚪ 持有"
        if r['buy_conf'] > 0.70: signal = "🔴 **加碼/買入**"
        elif r['sell_conf'] > 0.70: signal = "🟢 **減碼/賣出**"
        elif r['buy_conf'] > 0.60: signal = "🟡 偏多"
        elif r['sell_conf'] > 0.60: signal = "🔵 偏空"
        
        pnl_color = "🔴" if r['pnl'] > 0 else "🟢"
        
        output.append(f"**{r['name']} ({r['symbol']})**")
        output.append(f"- 狀態：{signal}")
        output.append(f"- 預測：買 `{r['buy_conf']*100:.1f}%` / 賣 `{r['sell_conf']*100:.1f}%`")
        output.append(f"- 現價 `${r['price']:.1f}` / 成本 `${r['cost']:.1f}` ({pnl_color} `{r['pnl']:+.2f}%`)")
        output.append("")

    output.append("----------------------------")
    output.append("💡 *註：預測基於 5 日動能與技術指標。*")
    
    print("\n".join(output))

if __name__ == "__main__":
    analyze_portfolio()
