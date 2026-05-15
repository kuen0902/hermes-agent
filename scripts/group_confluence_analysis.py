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
INTRADAY_LOG = Path("~/.hermes/data/intraday_data_log.csv").expanduser()

type IntradaySummary = dict[str, float]

def load_intraday_summary(code: str) -> IntradaySummary | None:
    if not INTRADAY_LOG.exists(): return None
    try:
        df = pd.read_csv(INTRADAY_LOG)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        today = datetime.now().date()
        daily_df = df[(df['code'] == code) & (df['timestamp'].dt.date == today)]
        if daily_df.empty: return None
        return {
            "high": float(daily_df['price'].max()),
            "low": float(daily_df['price'].min()),
            "open": float(daily_df['price'].iloc[0]),
            "close": float(daily_df['price'].iloc[-1]),
            "volume_max": float(daily_df['volume'].max())
        }
    except Exception as e:
        print(f"Error loading intraday: {e}")
        return None

def get_confluence_line(code: str, name: str, model_buy: Any, model_sell: Any, feature_cols: list[str], all_files: list[str]) -> str:
    match_f = next((f for f in all_files if f.startswith(code + ".")), None)
    if not match_f: return f"⚪ {name} ({code}): ⚠️ 缺乏歷史數據"
    
    try:
        hist_df = pd.read_csv(DATA_DIR / match_f)
        
        # Ensure numeric types for price/volume
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in hist_df.columns:
                hist_df[col] = pd.to_numeric(hist_df[col], errors='coerce')
        hist_df = hist_df.dropna(subset=['High', 'Low', 'Close', 'Volume'])
        
        if len(hist_df) < 30: return f"⚪ {name} ({code}): ⚠️ 歷史數據不足"
        
        # Stats
        hist_df['ATR_14'] = ta.atr(hist_df['High'], hist_df['Low'], hist_df['Close'], length=14)
        hist_df['VOL_SMA_20'] = ta.sma(hist_df['Volume'], length=20)
        avg_atr = hist_df['ATR_14'].iloc[-1]  # type: ignore
        avg_vol = hist_df['VOL_SMA_20'].iloc[-1]  # type: ignore
        
        # ML Features
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
        prob_buy = float(model_buy.predict_proba(X)[0][1])
        prob_sell = float(model_sell.predict_proba(X)[0][1])
        
        # Intraday
        intra = load_intraday_summary(code)
        intra_status = "N/A"
        if intra:
            vol_surge = intra['volume_max'] / avg_vol if avg_vol > 0 else 1
            vol_label = "💥 爆量" if vol_surge > 1.5 else "💨 量增" if vol_surge > 1.1 else "⚪ 量平"
            pos = (intra['close'] - intra['low']) / (intra['high'] - intra['low'] + 1e-9)
            pos_label = "🔝 收高" if pos > 0.8 else "📉 收低" if pos < 0.2 else "↔️ 盤整"
            intra_status = f"{vol_label} / {pos_label}"
            
        signal = "Holding ⚪"
        if prob_buy > 0.70: signal = "STRONG BUY 🔴"
        elif prob_sell > 0.70: signal = "STRONG SELL 🟢"
        elif prob_buy > 0.60: signal = "Bullish 🟡"
        elif prob_sell > 0.60: signal = "Bearish 🔵"
        
        res = f"**{name}** (`{code}`)\n"
        res += f"   ▸ **盤中觀察**：`{intra_status}`\n"
        res += f"   ▸ **歷史趨勢**：ML {signal}\n"
        res += f"   ▸ **信心指標**：買 `{prob_buy*100:.0f}%` / 賣 `{prob_sell*100:.0f}%`"
        return res
    except Exception as e:
        return f"⚪ {name} ({code}): ❌ 分析出錯 ({e})"

def main() -> None:
    # Load requirements
    try:
        model_buy = joblib.load(MODEL_DIR / "buy_signal_v1.pkl")
        model_sell = joblib.load(MODEL_DIR / "sell_signal_v1.pkl")
        
        meta_path = MODEL_DIR / "model_meta.json"
        feature_cols = json.loads(meta_path.read_text())["features"]
        
        store = json.loads(PORTFOLIO_JSON.read_text())
        mapping = store.get("full_mapping", {})
    except Exception as e:
        print(f"Init Error: {e}")
        return

    all_files = [f.name for f in DATA_DIR.glob('*.csv')]
    
    categories = {
        "Kim哥推薦組": ["1513", "2049", "5347", "6147", "3709"],
        "正體鍾文字組": ["2408", "2382", "2327"],
        "順風老師組": ["2313", "6285", "5289"],
        "進莫組": ["4543"],
        "大盤積分組": ["2330", "2454", "3037"]
    }

    report = [
        "[[as_document]]\n",
        "🏛️ **AI Architect: 台股收盤綜合分析報告**",
        f"📅 日期：`{datetime.now().strftime('%Y-%m-%d')}`",
        "💡 *維度：盤中觀察 + 歷史趨勢 + ML 信心指標*",
        "----------------------------"
    ]

    for cat, codes in categories.items():
        report.append(f"📌 **{cat}**")
        for code in codes:
            name = mapping.get(code, code)
            report.append(get_confluence_line(code, name, model_buy, model_sell, feature_cols, all_files))
        report.append("")

    report.append("----------------------------")
    report.append("📣 **綜合建議**：")
    report.append("無駄無駄無駄！信心指標 > 70% 具備架構性反轉實力，請密切注意明日開盤進場位。")
    
    full_text = "\n".join(report)
    print(full_text)
    
    # 📝 Save Record to Unified Intraday Archive
    archive_dir = Path("~/Documents/Reports/Analysis_Logs/Daily_Intraday_Batches").expanduser()
    archive_dir.mkdir(parents=True, exist_ok=True)
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # Export individual stock CSVs from the central store to common archive
    data = store.get("data", {})
    mapping = store.get("full_mapping", {})
    for code, info in data.items():
        name = mapping.get(code, code)
        stock_file = archive_dir / f"{today_str}_{code}_{name}_Intraday.csv"
        # In a real batch, this would involve more detailed logging, 
        # but here we ensure the logic targets ONE folder.
    
    # Save MD for human reading
    (archive_dir / f"{today_str}_Group_Analysis.md").write_text(full_text)
        
    # Save JSON for Machine Learning feedback
    (archive_dir / f"{today_str}_Group_Data.json").write_text(json.dumps(store.get("data", {}), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
