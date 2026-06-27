#!/Users/bookid/.hermes/.venv/bin/python
import os
import pandas as pd
import numpy as np
import duckdb
import xgboost as xgb
from datetime import datetime, timedelta

DATA_DIR = os.path.expanduser("~/.hermes/data")
DB_PATH = os.path.join(DATA_DIR, "potential_analysis.ddb")

def prepare_features(df):
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from features_utils import prepare_daily_features
    return prepare_daily_features(df)

def backfill():
    print("=========================================================================")
    print("  ⏳ AI QUANT ARCHITECT: HISTORICAL PREDICTIONS BACKFILL (WALK-FORWARD)")
    print("=========================================================================")
    
    if not os.path.exists(DB_PATH):
        print("❌ Database not found.")
        return

    conn = duckdb.connect(DB_PATH)
    
    # 1. Get tickers
    tickers_df = conn.execute("SELECT DISTINCT ticker, code, name FROM daily_stock_data").fetchdf()
    tickers_df['name_is_num'] = tickers_df['name'].apply(lambda x: 1 if str(x).strip().isdigit() else 0)
    tickers_df = tickers_df.sort_values(by=['ticker', 'name_is_num']).drop_duplicates(subset=['ticker'], keep='first').drop(columns=['name_is_num']).reset_index(drop=True)
    
    # 2. Extract features for ALL data
    print("🔹 Extracting features for all tickers (this takes a moment)...")
    full_data = []
    
    for idx, row in tickers_df.iterrows():
        ticker, code, name = row['ticker'], row['code'], row['name']
        try:
            df = conn.execute("""
                SELECT 
                    d.date AS Date, d.open AS Open, d.high AS High, d.low AS Low, d.close AS Close, d.volume AS Volume, 
                    d.foreign_net AS Foreign_Net, d.trust_net AS Trust_Net, d.dealer_net AS Dealer_Net,
                    (SELECT r.revenue FROM monthly_revenue r WHERE r.code = d.code AND CAST(r.date AS DATE) <= d.date ORDER BY r.date DESC LIMIT 1) AS Monthly_Revenue,
                    (SELECT r.yoy FROM monthly_revenue r WHERE r.code = d.code AND CAST(r.date AS DATE) <= d.date ORDER BY r.date DESC LIMIT 1) AS Revenue_YoY,
                    (SELECT r.mom FROM monthly_revenue r WHERE r.code = d.code AND CAST(r.date AS DATE) <= d.date ORDER BY r.date DESC LIMIT 1) AS Revenue_MoM,
                    (SELECT r.eps FROM financial_statements r WHERE r.code = d.code AND CAST(r.report_date AS DATE) <= d.date ORDER BY r.report_date DESC LIMIT 1) AS EPS,
                    (SELECT r.gross_profit_margin FROM financial_statements r WHERE r.code = d.code AND CAST(r.report_date AS DATE) <= d.date ORDER BY r.report_date DESC LIMIT 1) AS Gross_Profit_Margin,
                    (SELECT r.operating_profit_margin FROM financial_statements r WHERE r.code = d.code AND CAST(r.report_date AS DATE) <= d.date ORDER BY r.report_date DESC LIMIT 1) AS Operating_Profit_Margin,
                    (SELECT r.net_profit_margin FROM financial_statements r WHERE r.code = d.code AND CAST(r.report_date AS DATE) <= d.date ORDER BY r.report_date DESC LIMIT 1) AS Net_Profit_Margin
                FROM daily_stock_data d WHERE d.ticker = ? ORDER BY d.date ASC
            """, (ticker,)).fetchdf()
            
            if df.empty or len(df) < 80: continue
            processed = prepare_features(df)
            if processed is not None and not processed.empty:
                # Keep target_ret_20 even if NaN, because we need to predict on dates where it is NaN
                processed['Ticker'] = ticker
                processed['Name'] = name
                processed['code'] = code
                full_data.append(processed)
        except Exception as e:
            pass
            
    if not full_data:
        print("❌ No data processed.")
        return
        
    master_df = pd.concat(full_data).reset_index(drop=True)
    master_df['Date'] = pd.to_datetime(master_df['Date'])
    
    feature_cols = [
        'Close', 'SMA_5', 'SMA_20', 'SMA_60', 'EMA_12', 'EMA_26', 'RSI_14', 'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9',
        'ATR_14', 'Vol_Ratio', 'Ret_1', 'Ret_5', 'Ret_20', 'Foreign_Net_Ratio', 'Trust_Net_Ratio', 'Dealer_Net_Ratio',
        'Foreign_Cum_5', 'Foreign_Cum_20', 'Foreign_Cum_60', 'Trust_Cum_5', 'Trust_Cum_20', 'Trust_Cum_60',
        'Dual_Force_5', 'Dual_Force_20', 'Foreign_Buy_Days_5', 'Trust_Buy_Days_5', 'Monthly_Revenue', 'Revenue_YoY', 
        'Revenue_MoM', 'EPS', 'Gross_Profit_Margin', 'Operating_Profit_Margin', 'Net_Profit_Margin',
        'Ret_Accelerate_5', 'Max_DD_5', 'Inst_Flow_Ratio_5D', 'Bull_Trap_Signal', 'Dist_Yearly_Low', 'Volatility_20D'
    ]
    feature_cols = [c for c in feature_cols if c in master_df.columns]
    
    # 3. Get dates to simulate (last 50 trading days, excluding today to avoid replacing actual current prediction)
    # We will simulate exactly 50 distinct dates ending 1 day ago.
    dates_df = conn.execute("SELECT DISTINCT date FROM daily_stock_data ORDER BY date DESC LIMIT 52").fetchdf()
    sim_dates = pd.to_datetime(dates_df['date']).sort_values().tolist()
    sim_dates = sim_dates[:-1] # Remove the very last date (today), so we simulate up to yesterday.
    sim_dates = sim_dates[-50:] # Keep exactly 50 days.
    
    print(f"🔹 Starting Walk-Forward Backtesting for {len(sim_dates)} days (from {sim_dates[0].strftime('%Y-%m-%d')} to {sim_dates[-1].strftime('%Y-%m-%d')})...")
    
    # Pre-clean the master dataset for training
    master_train_df = master_df.replace([np.inf, -np.inf], np.nan).dropna(subset=feature_cols + ['Target_Ret_20'])
    master_train_df = master_train_df[master_train_df['Target_Ret_20'].abs() <= 0.40]
    
    for i, sim_date in enumerate(sim_dates):
        # The model standing at sim_date can only train on data where the 20-day return has ALREADY REALIZED.
        # So we filter training data where Date <= sim_date - 30 calendar days (approx 20 trading days)
        cutoff_date = sim_date - timedelta(days=30)
        train_df = master_train_df[master_train_df['Date'] <= cutoff_date]
        
        if len(train_df) < 1000:
            continue
            
        X_train = train_df[feature_cols]
        y_train = train_df['Target_Ret_20']
        
        # We don't have predictions history during backfill, so weight=1.0
        model = xgb.XGBRegressor(n_estimators=150, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, reg_alpha=0.5, reg_lambda=1.0, random_state=42)
        model.fit(X_train, y_train, verbose=False)
        
        # Predict for sim_date
        pred_df = master_df[master_df['Date'] == sim_date].copy()
        pred_df = pred_df.dropna(subset=feature_cols)
        
        if pred_df.empty:
            continue
            
        X_pred = pred_df[feature_cols]
        preds = model.predict(X_pred)
        pred_df['Predicted_Return_20D_Raw'] = preds
        
        # Risk Refinement
        pred_df['Risk_Penalty'] = 0.0
        if 'Dist_Yearly_Low' in pred_df.columns: pred_df.loc[pred_df['Dist_Yearly_Low'] < 0.03, 'Risk_Penalty'] += 0.05
        if 'Max_DD_5' in pred_df.columns: pred_df.loc[pred_df['Max_DD_5'] < -0.15, 'Risk_Penalty'] += 0.10
        if 'Bull_Trap_Signal' in pred_df.columns: pred_df.loc[pred_df['Bull_Trap_Signal'] > 0.5, 'Risk_Penalty'] += 0.08
        
        pred_df['Predicted_Return_20D'] = pred_df['Predicted_Return_20D_Raw'] - pred_df['Risk_Penalty']
        ranked_df = pred_df.sort_values(by='Predicted_Return_20D', ascending=False).reset_index(drop=True)
        
        # Limit to 15% like normal engine
        ranked_df.loc[ranked_df['Predicted_Return_20D'] > 0.15, 'Predicted_Return_20D'] = 0.15
        
        # Format for DB
        top_50 = ranked_df.head(50)
        insert_data = []
        for rank_idx, row in top_50.iterrows():
            insert_data.append({
                "date": sim_date.strftime('%Y-%m-%d'),
                "code": str(row['code']),
                "ticker": str(row['Ticker']),
                "name": str(row['Name']),
                "close": float(row['Close']),
                "predicted_return_20d": float(row['Predicted_Return_20D']),
                "rsi_14": float(row['RSI_14']),
                "vol_ratio": float(row['Vol_Ratio']),
                "foreign_net_5d": float(row['Foreign_Cum_5']),
                "trust_net_5d": float(row['Trust_Cum_5']),
                "dual_force_5d": float(row['Dual_Force_5']),
                "foreign_net_20d": float(row['Foreign_Cum_20']),
                "trust_net_20d": float(row['Trust_Cum_20']),
                "rank": int(rank_idx + 1),
                "risk_penalty": float(row['Risk_Penalty']),
                "raw_ml_pred": float(row['Predicted_Return_20D_Raw'])
            })
            
        # Write to DB
        insert_df = pd.DataFrame(insert_data)
        insert_df['date'] = pd.to_datetime(insert_df['date']).dt.date
        conn.execute("INSERT OR REPLACE INTO predictions (date, code, ticker, name, close, predicted_return_20d, rsi_14, vol_ratio, foreign_net_5d, trust_net_5d, dual_force_5d, foreign_net_20d, trust_net_20d, rank, risk_penalty, raw_ml_pred) SELECT * FROM insert_df")
        
        print(f"  ✓ [{i+1}/50] Simulated and saved top 50 predictions for {sim_date.strftime('%Y-%m-%d')}")
        
    conn.close()
    print("🎉 Historical prediction backfill completed successfully!")

if __name__ == "__main__":
    backfill()
