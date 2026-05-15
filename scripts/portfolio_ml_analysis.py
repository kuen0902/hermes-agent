import pandas as pd
import pandas_ta_classic as ta
import joblib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

# Configuration
DATA_DIR = Path("~/Documents/StockData_History_Final").expanduser()
MODEL_DIR = Path("~/.hermes/models").expanduser()
PORTFOLIO_JSON = Path("~/.hermes/data/central_stock_data.json").expanduser()

def analyze_portfolio() -> None:
    print("--- AI Architect: Portfolio ML Deep Dive ---")
    
    # 1. Load Models
    try:
        model_buy = joblib.load(MODEL_DIR / "buy_signal_v1.pkl")
        model_sell = joblib.load(MODEL_DIR / "sell_signal_v1.pkl")
        meta = json.loads((MODEL_DIR / "model_meta.json").read_text())
        feature_cols = meta["features"]
    except Exception as e:
        print(f"Failed to load models: {e}")
        return

    # 2. Load Portfolio
    try:
        portfolio_data = json.loads(PORTFOLIO_JSON.read_text())
        holdings = portfolio_data.get("personal_data", {})
    except Exception as e:
        print(f"Failed to load portfolio: {e}")
        return

    all_files = [f.name for f in DATA_DIR.glob('*.csv')]
    results: list[dict[str, Any]] = []

    for code, info in holdings.items():
        match_f = None
        # code is "2330", filename is "2330.TW_NAME.csv"
        for f in all_files:
            if f.startswith(code + "."):
                match_f = f
                break
        
        if not match_f: 
            continue
        
        path = DATA_DIR / match_f
        try:
            df = pd.read_csv(path)
            
            # Ensure numeric types for price/volume
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df.dropna(subset=['High', 'Low', 'Close', 'Volume'])
            
            if len(df) < 70: continue
            
            # Technical Indicators
            df['SMA_20'] = ta.sma(df['Close'], length=20)
            df['SMA_60'] = ta.sma(df['Close'], length=60)
            df['EMA_12'] = ta.ema(df['Close'], length=12)
            df['EMA_26'] = ta.ema(df['Close'], length=26)
            df['RSI_14'] = ta.rsi(df['Close'], length=14)
            macd = ta.macd(df['Close'])
            if macd is not None:
                df = pd.concat([df, macd], axis=1)  # type: ignore
            df['ATR_14'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            df['VOL_SMA_20'] = ta.sma(df['Volume'], length=20)
            df['Vol_Ratio'] = df['Volume'] / (df['VOL_SMA_20'] + 1e-9)  # type: ignore
            df['Ret_1'] = df['Close'].pct_change(1)
            df['Ret_5'] = df['Close'].pct_change(5)
            
            latest = df.iloc[[-1]]
            X = latest[feature_cols]
            
            # ML Probs
            prob_buy = float(model_buy.predict_proba(X)[0][1])
            prob_sell = float(model_sell.predict_proba(X)[0][1])
            
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
        except Exception as e:
            continue

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
