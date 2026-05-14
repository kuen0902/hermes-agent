import os
import sys
import subprocess
import pandas as pd

# Auto-install missing dependencies for cron execution
missing_deps = []
try:
    import pandas_ta_classic
except ImportError:
    # The original pandas-ta is unmaintained and missing versions for Py3.10.
    # 'pandas-ta-classic' is the community-maintained drop-in replacement.
    missing_deps.append("pandas-ta-classic")
try:
    import joblib
except ImportError:
    missing_deps.append("joblib")

if missing_deps:
    print(f"Auto-installing missing dependencies: {', '.join(missing_deps)}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_deps)

import pandas_ta_classic as ta
import joblib
import json
from datetime import datetime

# Configuration
DATA_DIR = os.path.expanduser("~/Documents/StockData_History_Final")
MODEL_DIR = os.path.expanduser("~/.hermes/models")
PORTFOLIO_JSON = os.path.expanduser("~/.hermes/data/central_stock_data.json")
INTRADAY_LOG = os.path.expanduser("~/.hermes/data/intraday_data_log.csv")

def load_intraday_summary(code):
    """Processes the intraday CSV to get high, low, first, last, and max volume for a specific code."""
    if not os.path.exists(INTRADAY_LOG):
        return None
    
    try:
        df = pd.read_csv(INTRADAY_LOG)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        today = datetime.now().date()
        daily_df = df[(df['code'] == str(code)) & (df['timestamp'].dt.date == today)]
        
        if daily_df.empty:
            return None
        
        return {
            "high": daily_df['price'].max(),
            "low": daily_df['price'].min(),
            "open": daily_df['price'].iloc[0],
            "close": daily_df['price'].iloc[-1],
            "volume_max": daily_df['volume'].max(),
            "count": len(daily_df)
        }
    except Exception as e:
        print(f"Intraday Load Error for {code}: {e}")
        return None

def analyze_confluence():
    print("--- AI Architect: Confluence EOD Analysis (Micro + Macro) ---")
    
    # 1. Load ML Models
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
            p_data = json.load(f)
        holdings = p_data.get("personal_data", {})
        if not holdings:
            holdings = p_data.get("full_mapping", {})
    except Exception as e:
        print(f"Failed to load portfolio: {e}")
        return

    all_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    output = [
        "[[as_document]]\n",
        f"🏛️ **AI Architect: 台股收盤綜合分析報告**",
        f"📅 日期：`{datetime.now().strftime('%Y-%m-%d')}`",
        f"💡 *分析維度：盤中量價微觀 + 歷史趨勢宏觀 + ML 訊號*",
        f"----------------------------"
    ]

    for code, item in holdings.items():
        if isinstance(item, str):
            name = item
            avg_c = 0
        else:
            name = item.get('name', 'Unknown')
            avg_c = item.get('avg', 0)
            
        match_f = next((f for f in all_files if f.startswith(code + ".")), None)
        if not match_f: continue

        
        hist_df = pd.read_csv(os.path.join(DATA_DIR, match_f))
        if len(hist_df) < 30: continue
        
        # Historical Stats
        hist_df['ATR_14'] = ta.atr(hist_df['High'], hist_df['Low'], hist_df['Close'], length=14)
        hist_df['VOL_SMA_20'] = ta.sma(hist_df['Volume'], length=20)
        avg_atr = hist_df['ATR_14'].iloc[-1]  # type: ignore
        avg_vol = hist_df['VOL_SMA_20'].iloc[-1]  # type: ignore
        
        # Intraday Summary
        intra = load_intraday_summary(code)
        
        # ML Prediction (Macro)
        # Re-calc indicators for ML
        hist_df['SMA_20'] = ta.sma(hist_df['Close'], length=20)
        hist_df['SMA_60'] = ta.sma(hist_df['Close'], length=60)
        hist_df['EMA_12'] = ta.ema(hist_df['Close'], length=12)
        hist_df['EMA_26'] = ta.ema(hist_df['Close'], length=26)
        hist_df['RSI_14'] = ta.rsi(hist_df['Close'], length=14)
        macd = ta.macd(hist_df['Close'])
        if macd is not None: hist_df = pd.concat([hist_df, macd], axis=1)  # type: ignore
        hist_df['Ret_1'] = hist_df['Close'].pct_change(1)
        hist_df['Ret_5'] = hist_df['Close'].pct_change(5)
        hist_df['Vol_Ratio'] = hist_df['Volume'] / (avg_vol + 1e-9)
        
        X = hist_df.iloc[[-1]][feature_cols]
        prob_buy = model_buy.predict_proba(X)[0][1]
        prob_sell = model_sell.predict_proba(X)[0][1]
        vol_ratio = float(hist_df['Vol_Ratio'].iloc[-1])
        
        # Confluence Logic
        intra_status = "N/A"
        if intra:
            range_val = intra['high'] - intra['low']
            vol_surge = intra['volume_max'] / avg_vol if avg_vol > 0 else 1
            
            vol_label = "💥 爆量" if vol_surge > 1.5 else "💨 量增" if vol_surge > 1.1 else "⚪ 量平"
            range_label = "⚡ 劇烈" if range_val > avg_atr * 1.2 else "🐢 稍悶" if range_val < avg_atr * 0.7 else "⚪ 正常"
            
            # Close Position in Daily Range
            pos = (intra['close'] - intra['low']) / (range_val + 1e-9)
            pos_label = "🔝 收高" if pos > 0.8 else "📉 收低" if pos < 0.2 else "↔️ 盤整"
            
            intra_status = f"{vol_label} | 振幅 {range_label} | {pos_label}"

        # Signal Label
        signal = "Holding ⚪"
        if prob_buy > 0.70: signal = "STRONG BUY 🔴"
        elif prob_sell > 0.70: signal = "STRONG SELL 🟢"
        elif prob_buy > 0.60: signal = "Bullish 🟡"
        elif prob_sell > 0.60: signal = "Bearish 🔵"

        output.append(f"**{name} ({code})**")
        output.append(f"▸ **盤中觀察**：`{intra_status}`")
        output.append(f"▸ **歷史趨勢**：ML {signal}")
        output.append(f"▸ **信心指標**：買 `{prob_buy*100:.0f}%` / 賣 `{prob_sell*100:.0f}%` / 能量 `{vol_ratio:.1f}x`")
        
        # Cost check
        current_p = float(hist_df['Close'].iloc[-1])
        pnl = (current_p - avg_c)/avg_c * 100 if avg_c > 0 else 0
        pnl_emoji = "💰" if pnl > 0 else "💸"
        output.append(f"▸ **盈虧狀態**：{pnl_emoji} `{pnl:+.2f}%` (現價 ${current_p:.1f})")
        output.append("")

    output.append("----------------------------")
    output.append("📣 **綜合建議**：")
    # Simple Logic: If ML Signal matches Intraday "收高" + "量增" -> High Conviction
    # (Simplified for now)
    output.append("無駄無駄無駄！若趨勢與盤中表現一致，則執行力是唯一的真理。")
    
    full_text = "\n".join(output)
    print(full_text)
    
    # 📝 Save Record to Obsidian/Local Log
    log_dir = os.path.expanduser("~/Documents/Reports/Analysis_Logs/Daily_Confluence")
    os.makedirs(log_dir, exist_ok=True)
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # Save MD
    with open(os.path.join(log_dir, f"{today_str}_Personal_Analysis.md"), 'w') as f:
        f.write(full_text)
        
    # Save structured results for feedback (Predictions only)
    # This requires gathering the signal data into a dict - simplified for now
    try:
        # Re-using the logic to create a small JSON of predictions if needed
        pass
    except: pass
    
if __name__ == "__main__":
    analyze_confluence()
