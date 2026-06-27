#!/Users/bookid/.hermes/.venv/bin/python
import os
import json
import joblib
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
import xgboost as xgb
from datetime import datetime

# Configuration
SAVE_DIR = os.path.expanduser("~/Documents/StockData_History_5Y")
MODEL_DIR = os.path.expanduser("~/.hermes/models")
DATA_DIR = os.path.expanduser("~/.hermes/data")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

MODEL_PATH = os.path.join(MODEL_DIR, "potential_stocks_xgb.pkl")
META_PATH = os.path.join(MODEL_DIR, "potential_meta.json")
OUTPUT_JSON_PATH = os.path.join(DATA_DIR, "top_50_potential_stocks.json")

# 35-dimensional features used by individual daily models
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

def prepare_features(df):
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from features_utils import prepare_daily_features 
    return prepare_daily_features(df)

def train_and_predict():
    print("--- ML Core: Potential Stocks Prediction Engine (Individual Models) ---")
            
    import duckdb
    db_path = os.path.join(DATA_DIR, "potential_analysis.ddb")
    if not os.path.exists(db_path):
        print(f"❌ Error: DuckDB database not found at {db_path}.")
        return
        
    conn = duckdb.connect(db_path)
    
    try:
        tickers_df = conn.execute("SELECT DISTINCT ticker, code, name FROM daily_stock_data").fetchdf()
        tickers_df['name_is_num'] = tickers_df['name'].apply(lambda x: 1 if str(x).strip().isdigit() else 0)
        tickers_df = tickers_df.sort_values(by=['ticker', 'name_is_num']).drop_duplicates(subset=['ticker'], keep='first').drop(columns=['name_is_num']).reset_index(drop=True)
    except Exception as e:
        print(f"❌ Error querying DuckDB tickers: {e}")
        conn.close()
        return
        
    try:
        row = conn.execute("SELECT MAX(date) FROM daily_stock_data").fetchone()
        global_max_date = pd.to_datetime(row[0])
        print(f"Latest trading day in DuckDB: {global_max_date.strftime('%Y-%m-%d')}")
    except:
        global_max_date = pd.to_datetime(datetime.now().date())
        
    latest_inference_rows = []
    
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
                last_row = processed.iloc[-1].copy()
                if (global_max_date - pd.to_datetime(last_row['Date'])).days <= 7:
                    last_row['Ticker'], last_row['Name'], last_row['code'] = ticker, name, code
                    latest_inference_rows.append(last_row)
        except Exception as e: print(f"Error processing {ticker}: {e}")
            
    conn.close()
    
    if not latest_inference_rows: 
        print("沒有最新的推論資料。")
        return
        
    inference_df = pd.DataFrame(latest_inference_rows).reset_index(drop=True)
    inference_df['Code_Only'] = inference_df['Ticker'].apply(lambda x: x.split('.')[0])
    
    predictions = []
    skipped_stocks = []
    
    print("⏳ 正在透過個股獨立模型進行預測...")
    
    for idx, row in inference_df.iterrows():
        code = row['code']
        ticker = row['Ticker']
        name = row['Name']
        
        daily_model_path = os.path.join(MODEL_DIR, f"daily_model_{code}.pkl")
        rolling_state_path = os.path.join(MODEL_DIR, f"rolling_state_{code}.json")
        
        if not os.path.exists(daily_model_path):
            skipped_stocks.append(f"{ticker} ({name})")
            predictions.append(np.nan)
            continue
            
        try:
            model = joblib.load(daily_model_path)
            # Ensure row has all DAILY_FEATURES without NaNs
            row_features = row[DAILY_FEATURES].fillna(0.0)
            X_inf = pd.DataFrame([row_features])
            pred_val = float(model.predict(X_inf)[0])
            
            # Apply Bias from Rolling State if available
            if os.path.exists(rolling_state_path):
                try:
                    with open(rolling_state_path, 'r') as f:
                        state_data = json.load(f)
                        bias_val = state_data.get("optimized_bias", 0.0)
                        pred_val += bias_val
                except:
                    pass
                    
            predictions.append(pred_val)
        except Exception as e:
            print(f"  ⚠️ Error predicting for {code}: {e}")
            skipped_stocks.append(f"{ticker} ({name})")
            predictions.append(np.nan)
            
    inference_df['Predicted_Return_20D_Raw'] = predictions
    
    # Drop rows that don't have predictions (skipped ones)
    inference_df = inference_df.dropna(subset=['Predicted_Return_20D_Raw']).reset_index(drop=True)
    
    if skipped_stocks:
        print("\n=================================================")
        print(f"⚠️ 因缺乏個股專屬模型而跳過的個股清單 (共 {len(skipped_stocks)} 檔):")
        # Print grouped in 10 per line for readability
        for i in range(0, len(skipped_stocks), 10):
            print(", ".join(skipped_stocks[i:i+10]))
        print("=================================================\n")
    
    # Risk Refinement
    inference_df['Risk_Penalty'] = 0.0
    if 'Dist_Yearly_Low' in inference_df.columns: inference_df.loc[inference_df['Dist_Yearly_Low'] < 0.03, 'Risk_Penalty'] += 0.05
    if 'Max_DD_5' in inference_df.columns: inference_df.loc[inference_df['Max_DD_5'] < -0.15, 'Risk_Penalty'] += 0.10
    if 'Bull_Trap_Signal' in inference_df.columns: inference_df.loc[inference_df['Bull_Trap_Signal'] > 0.5, 'Risk_Penalty'] += 0.08
    
    inference_df['Predicted_Return_20D_Final'] = inference_df['Predicted_Return_20D_Raw'] - inference_df['Risk_Penalty']
    
    # Multi-Horizon Bias Correction
    bias_path = os.path.join(DATA_DIR, "ml_bias_matrix.json")
    if os.path.exists(bias_path):
        try:
            with open(bias_path, 'r') as bf:
                bias_data = json.load(bf)
                b1, b2, b3 = [bias_data.get(k, 0) or 0 for k in ['bias_1w', 'bias_2w', 'bias_3w']]
                avg_sys = (b1 * 0.5 + b2 * 0.3 + b3 * 0.2)
                if avg_sys > 0.05: inference_df['Predicted_Return_20D_Final'] -= avg_sys
                
                f_codes = bias_data.get("failing_codes", [])
                if not f_codes: f_codes = [t.split('.')[0] for t in bias_data.get("failing_tickers", [])]
                if f_codes: inference_df.loc[inference_df['Code_Only'].isin(f_codes), 'Predicted_Return_20D_Final'] -= 0.50
        except: pass
        
    inference_df['Predicted_Return_20D'] = inference_df['Predicted_Return_20D_Final']
    ranked_df = inference_df.sort_values(by='Predicted_Return_20D', ascending=False).reset_index(drop=True)
    ranked_df.loc[ranked_df['Predicted_Return_20D'] > 0.15, 'Predicted_Return_20D'] = 0.15
    
    top_50_list = []
    for loop_idx, (idx, row) in enumerate(ranked_df.head(50).iterrows()):
        top_50_list.append({
            "rank": loop_idx + 1, "ticker": row['Ticker'], "code": row['Code_Only'], "name": row['Name'], "close": float(row['Close']),
            "predicted_return_20d": float(row['Predicted_Return_20D']), "date": pd.to_datetime(row['Date']).strftime('%Y-%m-%d'),
            "rsi_14": float(row['RSI_14']), "vol_ratio": float(row['Vol_Ratio']), "foreign_net_5d": float(row['Foreign_Cum_5']),
            "trust_net_5d": float(row['Trust_Cum_5']), "dual_force_5d": float(row['Dual_Force_5']), "foreign_net_20d": float(row['Foreign_Cum_20']),
            "trust_net_20d": float(row['Trust_Cum_20']), "eps": float(row['EPS']), "gross_profit_margin": float(row['Gross_Profit_Margin']),
            "operating_profit_margin": float(row['Operating_Profit_Margin']), "net_profit_margin": float(row['Net_Profit_Margin'])
        })
        
    with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f: json.dump(top_50_list, f, indent=2, ensure_ascii=False)
    
    try:
        conn = duckdb.connect(db_path)
        pred_df = pd.DataFrame(top_50_list)
        pred_df['date'] = pd.to_datetime(pred_df['date']).dt.date
        mapping = ranked_df.head(50).set_index('Ticker')[['Predicted_Return_20D_Raw', 'Risk_Penalty']]
        pred_df['raw_ml_pred'] = pred_df['ticker'].map(mapping['Predicted_Return_20D_Raw'])
        pred_df['risk_penalty'] = pred_df['ticker'].map(mapping['Risk_Penalty'])
        temp = pred_df[['date', 'code', 'ticker', 'name', 'close', 'predicted_return_20d', 'rsi_14', 'vol_ratio', 'foreign_net_5d', 'trust_net_5d', 'dual_force_5d', 'foreign_net_20d', 'trust_net_20d', 'rank', 'risk_penalty', 'raw_ml_pred']]
        conn.execute("INSERT OR REPLACE INTO predictions (date, code, ticker, name, close, predicted_return_20d, rsi_14, vol_ratio, foreign_net_5d, trust_net_5d, dual_force_5d, foreign_net_20d, trust_net_20d, rank, risk_penalty, raw_ml_pred) SELECT * FROM temp")
        conn.close()
    except Exception as e: print(f"DB Sync failed: {e}")

    print("\nTop 30 Potential Stocks Preview:")
    for stock in top_50_list[:30]:
        print(f"Rank {stock['rank']}: {stock['ticker']} ({stock['name']}) | Price: {stock['close']:.2f} | Score: {stock['predicted_return_20d']*100:.2f}%")

if __name__ == "__main__":
    train_and_predict()
