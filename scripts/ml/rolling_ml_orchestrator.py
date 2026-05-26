#!/Users/bookid/.hermes/.venv/bin/python
# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import sqlite3
import duckdb
import joblib
import pandas as pd
import numpy as np
import xgboost as xgb
import pandas_ta_classic as ta
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

DATA_DIR = os.path.expanduser("~/.hermes/data")
MODEL_DIR = os.path.expanduser("~/.hermes/models")
os.makedirs(MODEL_DIR, exist_ok=True)

# Database paths
PORTFOLIO_DB = os.path.join(DATA_DIR, "portfolio.db")
DUCK_PATH = os.path.join(DATA_DIR, "potential_analysis.ddb")
PORTFOLIO_DDB = os.path.join(DATA_DIR, "portfolio.ddb")

# Feature definition for the 14y Daily Ticker Model (35 Dimensions)
DAILY_FEATURES = [
    'Close', 'SMA_5', 'SMA_20', 'SMA_60', 'EMA_12', 'EMA_26', 'RSI_14', 
    'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9',
    'ATR_14', 'Vol_Ratio', 'Ret_1', 'Ret_5', 'Ret_20',
    'Foreign_Net_Ratio', 'Trust_Net_Ratio', 'Dealer_Net_Ratio',
    'Foreign_Cum_5', 'Foreign_Cum_20', 'Foreign_Cum_60',
    'Trust_Cum_5', 'Trust_Cum_20', 'Trust_Cum_60',
    'Dual_Force_5', 'Dual_Force_20',
    'Foreign_Buy_Days_5', 'Trust_Buy_Days_5',
    'Monthly_Revenue', 'Revenue_YoY', 'Revenue_MoM',
    'EPS', 'Gross_Profit_Margin', 'Operating_Profit_Margin', 'Net_Profit_Margin'
]

def normalize_code(code_str):
    return str(code_str).replace(".TW", "").replace(".TWO", "").strip()

def load_target_tickers():
    """Loads target tickers from current holdings and monitored lists."""
    holdings = {}
    if os.path.exists(PORTFOLIO_DB):
        try:
            conn = sqlite3.connect(PORTFOLIO_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT code, name FROM current_holdings")
            for row in cursor.fetchall():
                holdings[normalize_code(row[0])] = row[1]
            conn.close()
        except Exception as e:
            print(f"⚠️ Error loading SQLite holdings: {e}")

    group_codes = []
    william_codes = []
    central_path = os.path.join(DATA_DIR, "central_stock_data.json")
    if os.path.exists(central_path):
        try:
            with open(central_path, 'r', encoding='utf-8') as f:
                c_data = json.load(f)
                group_codes = c_data.get("group_codes", [])
                william_codes = c_data.get("william_codes", [])
        except Exception as e:
            print(f"⚠️ Error loading central json: {e}")

    targets = set(holdings.keys())
    targets.update(normalize_code(c) for c in group_codes)
    targets.update(normalize_code(c) for c in william_codes)
    return sorted(list(targets))

def check_stock_active(code, global_latest_date):
    """Filters out delisted/inactive stocks (must have traded within past 7 days of global latest)."""
    if not os.path.exists(DUCK_PATH):
        return False
    try:
        conn = duckdb.connect(DUCK_PATH)
        max_date_str = conn.execute("SELECT MAX(date) FROM daily_stock_data WHERE code = ?", (code,)).fetchone()[0]
        conn.close()
        if max_date_str:
            max_dt = pd.to_datetime(max_date_str)
            if (global_latest_date - max_dt).days <= 7:
                return True
    except Exception as e:
        print(f"⚠️ Error checking active state for {code}: {e}")
    return False

def get_global_latest_trading_day():
    if not os.path.exists(DUCK_PATH):
        return datetime.now()
    try:
        conn = duckdb.connect(DUCK_PATH)
        latest_date_str = conn.execute("SELECT MAX(date) FROM daily_stock_data").fetchone()[0]
        conn.close()
        return pd.to_datetime(latest_date_str)
    except Exception as e:
        print(f"⚠️ Error querying latest date: {e}")
        return datetime.now()

def prepare_daily_features(df):
    """Generates 35 features for the Daily Ticker Model."""
    if len(df) < 80:
        return None
    df = df.copy()
    
    # Ensure numeric columns
    for col in ['Open', 'High', 'Low', 'Close', 'Volume', 'Foreign_Net', 'Trust_Net', 'Dealer_Net']:
        if col not in df.columns:
            return None
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    for col in ['Monthly_Revenue', 'Revenue_YoY', 'Revenue_MoM', 'EPS', 'Gross_Profit_Margin', 'Operating_Profit_Margin', 'Net_Profit_Margin']:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
    df = df.dropna(subset=['Close', 'Volume'])
    df = df[df['Close'] > 0.0]
    
    # Technical Indicators
    df['SMA_5'] = ta.sma(df['Close'], length=5)
    df['SMA_20'] = ta.sma(df['Close'], length=20)
    df['SMA_60'] = ta.sma(df['Close'], length=60)
    df['EMA_12'] = ta.ema(df['Close'], length=12)
    df['EMA_26'] = ta.ema(df['Close'], length=26)
    df['RSI_14'] = ta.rsi(df['Close'], length=14)
    
    macd = ta.macd(df['Close'])
    if macd is not None:
        df = pd.concat([df, macd], axis=1)
        
    df['ATR_14'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    vol_sma = ta.sma(df['Volume'], length=20)
    df['VOL_SMA_20'] = vol_sma if vol_sma is not None else np.nan
    df['Vol_Ratio'] = df['Volume'] / df['VOL_SMA_20'].replace(0, 1)
    
    df['Ret_1'] = df['Close'].pct_change(1)
    df['Ret_5'] = df['Close'].pct_change(5)
    df['Ret_20'] = df['Close'].pct_change(20)
    
    df['Foreign_Net_Ratio'] = (df['Foreign_Net'] * 1000) / df['Volume'].replace(0, 1)
    df['Trust_Net_Ratio'] = (df['Trust_Net'] * 1000) / df['Volume'].replace(0, 1)
    df['Dealer_Net_Ratio'] = (df['Dealer_Net'] * 1000) / df['Volume'].replace(0, 1)
    
    df['Foreign_Cum_5'] = df['Foreign_Net'].rolling(5).sum()
    df['Foreign_Cum_20'] = df['Foreign_Net'].rolling(20).sum()
    df['Foreign_Cum_60'] = df['Foreign_Net'].rolling(60).sum()
    df['Trust_Cum_5'] = df['Trust_Net'].rolling(5).sum()
    df['Trust_Cum_20'] = df['Trust_Net'].rolling(20).sum()
    df['Trust_Cum_60'] = df['Trust_Net'].rolling(60).sum()
    
    df['Dual_Force_5'] = df['Foreign_Cum_5'] + df['Trust_Cum_5']
    df['Dual_Force_20'] = df['Foreign_Cum_20'] + df['Trust_Cum_20']
    df['Foreign_Buy_Days_5'] = (df['Foreign_Net'] > 0).rolling(5).sum()
    df['Trust_Buy_Days_5'] = (df['Trust_Net'] > 0).rolling(5).sum()
    
    df['Target_Ret_20'] = df['Close'].shift(-20) / df['Close'] - 1.0
    return df

def query_ticker_daily_db(code):
    """Retrieves all daily records for a stock from DuckDB."""
    conn = duckdb.connect(DUCK_PATH)
    try:
        df = conn.execute("""
            SELECT 
                d.date AS Date, 
                d.open AS Open, 
                d.high AS High, 
                d.low AS Low, 
                d.close AS Close, 
                d.volume AS Volume, 
                d.foreign_net AS Foreign_Net, 
                d.trust_net AS Trust_Net, 
                d.dealer_net AS Dealer_Net,
                (SELECT r.revenue FROM monthly_revenue r WHERE r.code = d.code AND CAST(r.date AS DATE) <= d.date ORDER BY r.date DESC LIMIT 1) AS Monthly_Revenue,
                (SELECT r.yoy FROM monthly_revenue r WHERE r.code = d.code AND CAST(r.date AS DATE) <= d.date ORDER BY r.date DESC LIMIT 1) AS Revenue_YoY,
                (SELECT r.mom FROM monthly_revenue r WHERE r.code = d.code AND CAST(r.date AS DATE) <= d.date ORDER BY r.date DESC LIMIT 1) AS Revenue_MoM,
                (SELECT r.eps FROM financial_statements r WHERE r.code = d.code AND CAST(r.report_date AS DATE) <= d.date ORDER BY CAST(r.report_date AS DATE) DESC LIMIT 1) AS EPS,
                (SELECT r.gross_profit_margin FROM financial_statements r WHERE r.code = d.code AND CAST(r.report_date AS DATE) <= d.date ORDER BY CAST(r.report_date AS DATE) DESC LIMIT 1) AS Gross_Profit_Margin,
                (SELECT r.operating_profit_margin FROM financial_statements r WHERE r.code = d.code AND CAST(r.report_date AS DATE) <= d.date ORDER BY CAST(r.report_date AS DATE) DESC LIMIT 1) AS Operating_Profit_Margin,
                (SELECT r.net_profit_margin FROM financial_statements r WHERE r.code = d.code AND CAST(r.report_date AS DATE) <= d.date ORDER BY CAST(r.report_date AS DATE) DESC LIMIT 1) AS Net_Profit_Margin
            FROM daily_stock_data d
            WHERE d.code = ?
            ORDER BY d.date ASC
        """, (code,)).fetchdf()
    except Exception as e:
        df = pd.DataFrame()
        print(f"⚠️ Error querying daily DuckDB for {code}: {e}")
    conn.close()
    return df

def train_daily_ticker_model(code, df_processed):
    """Trains a stock-specific daily 14-year model."""
    df_clean = df_processed.dropna(subset=DAILY_FEATURES + ['Target_Ret_20'])
    df_clean = df_clean.replace([np.inf, -np.inf], np.nan).dropna(subset=DAILY_FEATURES)
    if len(df_clean) < 40:
        return None
        
    X = df_clean[DAILY_FEATURES]
    y = df_clean['Target_Ret_20']
    
    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42
    )
    model.fit(X, y)
    
    path = os.path.join(MODEL_DIR, f"daily_model_{code}.pkl")
    joblib.dump(model, path)
    return model

# High-Frequency Intraday helper functions
def load_latest_institutional_data(iso_date, code):
    if not os.path.exists(PORTFOLIO_DDB):
        return 0, 0, 0, 0.0
    try:
        conn = duckdb.connect(PORTFOLIO_DDB)
        row = conn.execute('''
            SELECT foreign_buy, trust_buy, dealer_buy, foreign_ratio 
            FROM institutional_data 
            WHERE date = ? AND code = ?
        ''', (iso_date, code)).fetchone()
        conn.close()
        if row:
            return row[0] or 0, row[1] or 0, row[2] or 0, row[3] or 0.0
    except Exception:
        pass
    return 0, 0, 0, 0.0

def load_rolling_institutional_data(iso_date, code):
    if not os.path.exists(PORTFOLIO_DDB):
        return 0, 0, 0, 0
    try:
        conn = duckdb.connect(PORTFOLIO_DDB)
        rows = conn.execute('''
            SELECT trust_buy, dealer_buy 
            FROM institutional_data 
            WHERE code = ? AND date <= ? 
            ORDER BY date DESC LIMIT 20
        ''', (code, iso_date)).fetchall()
        conn.close()
        
        trust_5d = sum(r[0] or 0 for r in rows[:5]) if rows else 0
        trust_20d = sum(r[0] or 0 for r in rows) if rows else 0
        dealer_5d = sum(r[1] or 0 for r in rows[:5]) if rows else 0
        dealer_20d = sum(r[1] or 0 for r in rows) if rows else 0
        
        return trust_5d, trust_20d, dealer_5d, dealer_20d
    except Exception:
        pass
    return 0, 0, 0, 0

def fetch_5m_kbars_duckdb(code):
    """Retrieves 5m kbars from DuckDB kbars_5m table."""
    if not os.path.exists(DUCK_PATH):
        return pd.DataFrame()
    try:
        conn = duckdb.connect(DUCK_PATH)
        df = conn.execute("""
            SELECT timestamp, open, high, low, close, volume 
            FROM kbars_5m 
            WHERE code = ? 
            ORDER BY timestamp ASC
        """, (code,)).fetchdf()
        conn.close()
        return df
    except Exception as e:
        print(f"⚠️ Error querying 5m K-bars for {code}: {e}")
        return pd.DataFrame()

def run_rolling_training_and_feedback(code, daily_df, daily_model):
    """
    1. Trains high-frequency intraday models on days 150d-90d.
    2. Simulates rolling daily predictions and adaptive bias feedback on days 89 to 1.
    """
    # Grab 5m kbars
    kb_df = fetch_5m_kbars_duckdb(code)
    if kb_df.empty or len(kb_df) < 500:
        print(f"⚠️ [{code}] Insufficient 5m K-bars for intraday model training.")
        return False
        
    kb_df['timestamp'] = pd.to_datetime(kb_df['timestamp'])
    kb_df['date'] = kb_df['timestamp'].dt.date
    
    # Process 5-minute bins
    grouped = kb_df.groupby(['date', 'timestamp']).agg({
        'close': 'last',
        'volume': 'sum'
    }).reset_index().rename(columns={'close': 'Close', 'volume': 'Volume', 'timestamp': '5m_bin'})
    
    dates = sorted(grouped['date'].unique())
    if len(dates) < 40:
        print(f"⚠️ [{code}] Under 40 historical trading days in 5m K-bars.")
        return False
        
    # Map Daily Features by Date
    daily_history = pd.Series(daily_df['Close'].values, index=daily_df['Date'])
    
    # Align TAIEX 5-min returns
    taiex_features_by_date = {}
    try:
        conn = duckdb.connect(DUCK_PATH)
        # Fallback to general TAIEX returns if available, otherwise default to 0.0
        taiex_db = conn.execute("""
            SELECT timestamp, close 
            FROM kbars_5m 
            WHERE ticker = '^TWII' 
            ORDER BY timestamp ASC
        """).fetchdf()
        conn.close()
        if not taiex_db.empty:
            taiex_db['timestamp'] = pd.to_datetime(taiex_db['timestamp'])
            taiex_db['date'] = taiex_db['timestamp'].dt.date
            taiex_grouped = taiex_db.groupby(['date', 'timestamp']).agg({'close': 'last'}).reset_index()
            for d, gp in taiex_grouped.groupby('date'):
                gp = gp.sort_values('timestamp')
                if len(gp) >= 6:
                    t_prices = gp['close'].values
                    t_ret = np.diff(t_prices) / t_prices[:-1]
                    if len(t_ret) >= 5:
                        taiex_features_by_date[d] = list(t_ret[-5:])
    except Exception:
        pass
        
    # Pre-training window: 150d down to 90d (e.g. index 0 to middle of dates list)
    pretrain_cutoff_idx = min(int(len(dates) * 0.4) + 20, len(dates) - 30)
    pretrain_dates = dates[:pretrain_cutoff_idx]
    rolling_dates = dates[pretrain_cutoff_idx:]
    
    print(f"  - Pre-training days: {len(pretrain_dates)}, Rolling test & calibration days: {len(rolling_dates)}")
    
    def extract_features_for_day(today, prev_pred_prob):
        # 1. Today TAIEX features
        taiex_feats = taiex_features_by_date.get(today, [0.0]*5)
        
        day_data = grouped[grouped['date'] == today].sort_values('5m_bin')
        if len(day_data) < 5:
            return None, None
            
        prices = day_data['Close'].values
        vols = day_data['Volume'].values
        
        returns = np.diff(prices) / prices[:-1]
        vol_changes = np.diff(vols) / (vols[:-1] + 1e-9)
        if len(returns) < 5:
            return None, None
            
        feats = list(returns[-5:]) + list(vol_changes[-5:])
        
        # Technical
        close_series = pd.Series(prices)
        rsi_val = 50.0
        if len(close_series) > 14:
            rsi_series = ta.rsi(close_series, length=14)
            if rsi_series is not None and not rsi_series.empty:
                rsi_val = rsi_series.iloc[-1]
                if pd.isna(rsi_val): rsi_val = 50.0
                
        macd_line, macd_hist = 0.0, 0.0
        if len(close_series) > 26:
            macd_df = ta.macd(close_series, fast=12, slow=26, signal=9)
            if macd_df is not None and not macd_df.empty:
                macd_line = macd_df.iloc[-1, 0]
                macd_hist = macd_df.iloc[-1, 1]
                if pd.isna(macd_line): macd_line = 0.0
                if pd.isna(macd_hist): macd_hist = 0.0
                
        feats.extend([rsi_val, macd_line, macd_hist])
        feats.extend(taiex_feats)
        
        # Institutional
        today_str = today.strftime("%Y-%m-%d") if isinstance(today, datetime) or hasattr(today, 'strftime') else str(today)
        f_buy, t_buy, d_buy, f_ratio = load_latest_institutional_data(today_str, code)
        feats.extend([f_buy, t_buy, d_buy, f_ratio])
        
        t_5d, t_20d, d_5d, d_20d = load_rolling_institutional_data(today_str, code)
        feats.extend([t_5d, t_20d, d_5d, d_20d])
        
        # Daily MA features
        hist_before_today = daily_history[daily_history.index < today_str]
        hist_closes = list(hist_before_today.tail(239).values)
        closes_240d = hist_closes + [prices[-1]]
        n_days = len(closes_240d)
        
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
        
        feats.extend([bias5, bias10, bias20, bias60, bias120, bias240, spread_5_20, spread_20_60, spread_60_240])
        feats.extend([prices[-1], ma5, ma20, ma60])
        
        # Step 9: Inject Daily 14y Model predicted 20-day return rate as a prior feature!
        daily_pred_ret = 0.0
        # Find daily process row for today to extract standard daily features
        daily_row = daily_df[daily_df['Date'] == today_str]
        if not daily_row.empty:
            daily_feats_processed = prepare_daily_features(daily_df)
            if daily_feats_processed is not None:
                df_day = daily_feats_processed[daily_feats_processed['Date'] == today_str]
                if not df_day.empty:
                    df_clean = df_day[DAILY_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0.0)
                    try:
                        daily_pred_ret = float(daily_model.predict(df_clean)[0])
                    except Exception:
                        pass
        feats.append(daily_pred_ret)
        
        # Step 10: Feedback control error
        # In pre-training we set error_val = 0.0, but in rolling predictions we inject actual rolling error
        return feats, prices[-1]

    # Pre-train Intraday Model
    pre_X = []
    pre_y_clf = []
    pre_y_reg = []
    
    prev_pred_prob = 0.5
    
    for idx in range(1, len(pretrain_dates) - 1):
        today = pretrain_dates[idx]
        tomorrow = pretrain_dates[idx+1]
        
        feats, today_close = extract_features_for_day(today, prev_pred_prob)
        if feats is None:
            continue
            
        # Add feedback term 0.0 for pre-training phase
        feats.append(0.0)
        
        tomorrow_data = grouped[grouped['date'] == tomorrow].sort_values('5m_bin')
        if tomorrow_data.empty:
            continue
        tomorrow_close = tomorrow_data['Close'].values[-1]
        
        label = 1 if tomorrow_close > today_close else 0
        ret_val = (tomorrow_close - today_close) / today_close
        
        pre_X.append(feats)
        pre_y_clf.append(label)
        pre_y_reg.append(ret_val)
        
        prev_pred_prob = 0.55 if label == 1 else 0.45
        
    if len(pre_X) < 10:
        print(f"⚠️ [{code}] Insufficient pre-training features extracted.")
        return False
        
    # Fit initial intraday model
    model_clf = RandomForestClassifier(n_estimators=60, max_depth=8, min_samples_leaf=3, random_state=42)
    model_clf.fit(pre_X, pre_y_clf)
    
    model_reg = RandomForestRegressor(n_estimators=60, max_depth=8, min_samples_leaf=3, random_state=42)
    model_reg.fit(pre_X, pre_y_reg)
    
    # ----------------------------------------------------
    # Rolling Adaptive Bias simulation (Days 89 to 1)
    # ----------------------------------------------------
    rolling_X = list(pre_X)
    rolling_y_clf = list(pre_y_clf)
    rolling_y_reg = list(pre_y_reg)
    
    bias_val = 0.0
    alpha = 0.2
    prev_calibrated_val = daily_history.iloc[-1]
    
    for idx in range(len(rolling_dates) - 1):
        today = rolling_dates[idx]
        tomorrow = rolling_dates[idx+1]
        
        # Calculate yesterday's prediction error relative to today's open price
        today_data = grouped[grouped['date'] == today].sort_values('5m_bin')
        if today_data.empty:
            continue
        actual_today_price = today_data['Close'].values[-1]
        
        # Error feedback update
        error_val = actual_today_price - prev_calibrated_val
        bias_val = bias_val * (1.0 - alpha) + error_val * alpha
        
        # Extract features for today
        feats, today_close = extract_features_for_day(today, prev_pred_prob)
        if feats is None:
            continue
            
        # Inject adaptive bias error term
        feats.append(error_val)
        
        # Predict tomorrow's price using the current RandomForest models
        prob = float(model_clf.predict_proba([feats])[0][1])
        pred_ret = float(model_reg.predict([feats])[0])
        
        raw_val = today_close * (1.0 + pred_ret)
        prev_calibrated_val = raw_val + bias_val  # Save for next day correction
        
        tomorrow_data = grouped[grouped['date'] == tomorrow].sort_values('5m_bin')
        if tomorrow_data.empty:
            continue
        tomorrow_close = tomorrow_data['Close'].values[-1]
        
        label = 1 if tomorrow_close > today_close else 0
        ret_val = (tomorrow_close - today_close) / today_close
        
        # Append new rolling sample to retrain
        rolling_X.append(feats)
        rolling_y_clf.append(label)
        rolling_y_reg.append(ret_val)
        
        prev_pred_prob = prob
        
        # Incremental rolling fit update (every 10 days to keep training latency fast)
        if idx % 10 == 0:
            model_clf.fit(rolling_X, rolling_y_clf)
            model_reg.fit(rolling_X, rolling_y_reg)
            
    # Final Model Refitting to incorporate all optimized rolling history
    model_clf.fit(rolling_X, rolling_y_clf)
    model_reg.fit(rolling_X, rolling_y_reg)
    
    # Save optimized ticker models & feedback bias state
    path_clf = os.path.join(MODEL_DIR, f"intraday_model_{code}.pkl")
    path_reg = os.path.join(MODEL_DIR, f"intraday_model_reg_{code}.pkl")
    joblib.dump(model_clf, path_clf)
    joblib.dump(model_reg, path_reg)
    
    # Save bias and convergence metadata to JSON
    meta_path = os.path.join(MODEL_DIR, f"rolling_state_{code}.json")
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump({
            "ticker": code,
            "optimized_bias": float(bias_val),
            "last_error": float(error_val),
            "updated_at": datetime.now().isoformat(),
            "samples": len(rolling_X)
        }, f, indent=2)
        
    print(f"  ✓ [{code}] Models & Bias state successfully optimized and saved. Final Bias: {bias_val:+.4f}")
    return True

def main():
    print("=========================================================")
    print(" 🤖 啟動個股自適應 14年-150日 滾動機器學習預測與模型優化器 ")
    print("=========================================================")
    
    global_latest = get_global_latest_trading_day()
    print(f"資料庫最新交易日: {global_latest.strftime('%Y-%m-%d')}")
    
    # 1. 載入目標持股與監控清單
    target_tickers = load_target_tickers()
    print(f"原始候選商品數量: {len(target_tickers)}")
    
    # 2. 篩選在線股票（只訓練目前還在線的個股，已經下市的不訓練）
    active_tickers = [c for c in target_tickers if check_stock_active(c, global_latest)]
    print(f"篩選後有效在線交易商品 (共計 {len(active_tickers)} 檔)：{active_tickers}")
    
    success_count = 0
    start_time = time.time()
    
    for idx, code in enumerate(active_tickers, 1):
        print(f"\n[{idx}/{len(active_tickers)}] 正在處理商品 {code} ...")
        
        # 1. 讀取並處理 14 年歷史日線
        daily_df = query_ticker_daily_db(code)
        if daily_df.empty or len(daily_df) < 80:
            print(f"  ⚠️ [{code}] 資料庫歷史日線資料量不足 (僅 {len(daily_df)} 筆)，跳過訓練。")
            continue
            
        processed_daily = prepare_daily_features(daily_df)
        if processed_daily is None or processed_daily.empty:
            print(f"  ⚠️ [{code}] 特徵工程產生無效結果，跳過。")
            continue
            
        # 2. 訓練個股 14 年日線 XGBoost 模型
        daily_model = train_daily_ticker_model(code, processed_daily)
        if daily_model is None:
            print(f"  ⚠️ [{code}] 訓練個股日線模型失敗。")
            continue
        print(f"  ✓ [{code}] 個股 14年日線 XGBoost 模型訓練成功！")
        
        # 3. 高頻 150-90日預訓練 & 89日-1日自適應滾動偏差更新
        success = run_rolling_training_and_feedback(code, daily_df, daily_model)
        if success:
            success_count += 1
            
    elapsed = time.time() - start_time
    print("\n=========================================================")
    print(" 🎉 全市場在線商品滾動 adaptive ML 特徵模型優化圓滿成功！")
    print(f"  - 成功處理/優化商品數：{success_count} 檔")
    print(f"  - 總計花費時間：{elapsed:.2f} 秒")
    print("=========================================================")

if __name__ == "__main__":
    main()
