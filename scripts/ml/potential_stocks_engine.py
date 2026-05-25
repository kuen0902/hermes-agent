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

def prepare_features(df):
    """Generates rich technical and institutional (chip flow) features."""
    if len(df) < 80:
        return None
        
    df = df.copy()
    
    # Ensure columns exist and are numeric
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
    
    # 1. Technical Indicators
    df['SMA_20'] = ta.sma(df['Close'], length=20)
    df['SMA_60'] = ta.sma(df['Close'], length=60)
    df['EMA_12'] = ta.ema(df['Close'], length=12)
    df['EMA_26'] = ta.ema(df['Close'], length=26)
    
    # RSI
    df['RSI_14'] = ta.rsi(df['Close'], length=14)
    
    # MACD
    macd = ta.macd(df['Close'])
    if macd is not None:
        df = pd.concat([df, macd], axis=1)  # type: ignore
        
    # ATR & Volume
    df['ATR_14'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    vol_sma = ta.sma(df['Volume'], length=20)
    if vol_sma is not None:
        df['VOL_SMA_20'] = vol_sma
        df['Vol_Ratio'] = df['Volume'] / df['VOL_SMA_20'].replace(0, 1)
    else:
        df['VOL_SMA_20'] = np.nan
        df['Vol_Ratio'] = np.nan
    
    # Price returns
    df['Ret_1'] = df['Close'].pct_change(1)
    df['Ret_5'] = df['Close'].pct_change(5)
    df['Ret_20'] = df['Close'].pct_change(20)
    
    # 2. Institutional Investor (Chip Flow) Features
    # Convert Net Buy (张 / thousand shares) to shares, divide by volume to get ratio
    df['Foreign_Net_Ratio'] = (df['Foreign_Net'] * 1000) / df['Volume'].replace(0, 1)
    df['Trust_Net_Ratio'] = (df['Trust_Net'] * 1000) / df['Volume'].replace(0, 1)
    df['Dealer_Net_Ratio'] = (df['Dealer_Net'] * 1000) / df['Volume'].replace(0, 1)
    
    # Rolling sums of net buys (張)
    df['Foreign_Cum_5'] = df['Foreign_Net'].rolling(5).sum()
    df['Foreign_Cum_20'] = df['Foreign_Net'].rolling(20).sum()
    df['Foreign_Cum_60'] = df['Foreign_Net'].rolling(60).sum()
    
    df['Trust_Cum_5'] = df['Trust_Net'].rolling(5).sum()
    df['Trust_Cum_20'] = df['Trust_Net'].rolling(20).sum()
    df['Trust_Cum_60'] = df['Trust_Net'].rolling(60).sum()
    
    # Cohesion/Dual Force (外資投信聯手)
    df['Dual_Force_5'] = df['Foreign_Cum_5'] + df['Trust_Cum_5']
    df['Dual_Force_20'] = df['Foreign_Cum_20'] + df['Trust_Cum_20']
    
    # Buying streak (days net-bought in last 5 days)
    df['Foreign_Buy_Days_5'] = (df['Foreign_Net'] > 0).rolling(5).sum()
    df['Trust_Buy_Days_5'] = (df['Trust_Net'] > 0).rolling(5).sum()
    
    # 3. Machine Learning TARGET: Future 20-day Return (波段潛力)
    # Target = Close price 20 days in the future / current Close - 1.0
    df['Target_Ret_20'] = df['Close'].shift(-20) / df['Close'] - 1.0
    
    return df

def train_and_predict(inference_only=False):
    print("--- ML Core: Potential Stocks Prediction Engine ---")
    
    # 1. 檢查是否存在現有模型，若 --inference-only 則嘗試直接載入
    model = None
    if inference_only:
        if os.path.exists(MODEL_PATH):
            try:
                model = joblib.load(MODEL_PATH)
                print(f"✓ [Inference Only] 成功載入已存在的 XGBoost 模型: {MODEL_PATH}")
            except Exception as e:
                print(f"⚠️ [Inference Only] 載入模型失敗，將啟動完整重新訓練: {e}")
                inference_only = False
        else:
            print(f"⚠️ [Inference Only] 找不到模型 {MODEL_PATH}，將啟動完整重新訓練。")
            inference_only = False
            
    # Load and process all stock records directly from DuckDB
    import duckdb
    db_path = os.path.join(DATA_DIR, "potential_analysis.ddb")
    if not os.path.exists(db_path):
        print(f"❌ Error: DuckDB database not found at {db_path}.")
        return
        
    print(f"Connecting to DuckDB database: {db_path}")
    conn = duckdb.connect(db_path)
    
    try:
        # Retrieve all unique tickers from daily_stock_data
        tickers_df = conn.execute("SELECT DISTINCT ticker, code, name FROM daily_stock_data").fetchdf()
    except Exception as e:
        print(f"❌ Error querying DuckDB tickers: {e}")
        conn.close()
        return
        
    print(f"Total tickers found in DuckDB: {len(tickers_df)}")
    
    # 獲取資料庫中最新的交易日期，用以過濾因停牌或故障而無最新報價的商品
    try:
        global_max_date = pd.to_datetime(conn.execute("SELECT MAX(date) FROM daily_stock_data").fetchone()[0])
        print(f"Latest trading day in DuckDB: {global_max_date.strftime('%Y-%m-%d')}")
    except Exception as e:
        print(f"⚠️ 無法取得最新交易日期: {e}")
        global_max_date = pd.to_datetime(datetime.now().date())
        
    full_data = []
    latest_inference_rows = []
    
    for idx, row in tickers_df.iterrows():
        ticker = row['ticker']
        code = row['code']
        name = row['name']
        
        try:
            # Query all daily records for this ticker sorted by date ASC
            df = conn.execute("""
                SELECT 
                    d.date AS Date, 
                    d.open AS Open, 
                    d.high AS High, 
                    d.low AS Low, 
                    d.close AS Close, 
                    d.adj_close AS "Adj Close", 
                    d.volume AS Volume, 
                    d.foreign_net AS Foreign_Net, 
                    d.trust_net AS Trust_Net, 
                    d.dealer_net AS Dealer_Net,
                    (
                        SELECT r.revenue 
                        FROM monthly_revenue r 
                        WHERE r.code = d.code AND CAST(r.date AS DATE) <= d.date 
                        ORDER BY r.date DESC 
                        LIMIT 1
                    ) AS Monthly_Revenue,
                    (
                        SELECT r.yoy 
                        FROM monthly_revenue r 
                        WHERE r.code = d.code AND CAST(r.date AS DATE) <= d.date 
                        ORDER BY r.date DESC 
                        LIMIT 1
                    ) AS Revenue_YoY,
                    (
                        SELECT r.mom 
                        FROM monthly_revenue r 
                        WHERE r.code = d.code AND CAST(r.date AS DATE) <= d.date 
                        ORDER BY r.date DESC 
                        LIMIT 1
                    ) AS Revenue_MoM,
                    (
                        SELECT r.eps 
                        FROM financial_statements r 
                        WHERE r.code = d.code AND CAST(r.report_date AS DATE) <= d.date 
                        ORDER BY CAST(r.report_date AS DATE) DESC 
                        LIMIT 1
                    ) AS EPS,
                    (
                        SELECT r.gross_profit_margin 
                        FROM financial_statements r 
                        WHERE r.code = d.code AND CAST(r.report_date AS DATE) <= d.date 
                        ORDER BY CAST(r.report_date AS DATE) DESC 
                        LIMIT 1
                    ) AS Gross_Profit_Margin,
                    (
                        SELECT r.operating_profit_margin 
                        FROM financial_statements r 
                        WHERE r.code = d.code AND CAST(r.report_date AS DATE) <= d.date 
                        ORDER BY CAST(r.report_date AS DATE) DESC 
                        LIMIT 1
                    ) AS Operating_Profit_Margin,
                    (
                        SELECT r.net_profit_margin 
                        FROM financial_statements r 
                        WHERE r.code = d.code AND CAST(r.report_date AS DATE) <= d.date 
                        ORDER BY CAST(r.report_date AS DATE) DESC 
                        LIMIT 1
                    ) AS Net_Profit_Margin
                FROM daily_stock_data d
                WHERE d.ticker = ? 
                ORDER BY d.date ASC
            """, (ticker,)).fetchdf()
            
            if df.empty or len(df) < 80:
                continue
                
            processed = prepare_features(df)
            if processed is not None and not processed.empty:
                assert isinstance(processed, pd.DataFrame)
                # 1. Split out the last row (without a target, used for current inference)
                last_row = processed.iloc[-1].copy()
                last_row_date = pd.to_datetime(last_row['Date'])
                
                # 僅在該商品的最新有效交易日在最新交易日 7 天之內時，才將其納入實時推論（防範長期停牌商品）
                if (global_max_date - last_row_date).days <= 7:
                    last_row['Ticker'] = ticker
                    last_row['Name'] = name
                    latest_inference_rows.append(last_row)
                
                # 2. Keep the historical rows for training (僅在需要訓練時才收集)
                if not inference_only:
                    historical_rows = processed.dropna(subset=['Target_Ret_20'])
                    if not historical_rows.empty:
                        historical_rows = historical_rows.copy()
                        historical_rows['Ticker'] = ticker
                        historical_rows['Name'] = name
                        full_data.append(historical_rows)
        except Exception as e:
            print(f"Error processing {ticker} from DuckDB: {e}")
            
    conn.close()
    
    # Feature columns for training
    feature_cols = [
        'SMA_20', 'SMA_60', 'EMA_12', 'EMA_26', 'RSI_14', 
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
    
    if not inference_only:
        if not full_data:
            print("❌ Error: No training data could be loaded from DuckDB 'daily_stock_data'.")
            return
            
        # Combine training data
        train_val_df = pd.concat(full_data).reset_index(drop=True)
        print(f"Combined historical dataset size: {len(train_val_df)} rows.")
        
        # Ensure all feature columns exist and have no NaNs
        feature_cols = [c for c in feature_cols if c in train_val_df.columns]
        
        # Drop rows that have NaN/Inf in features or target, and filter out extreme outliers in target return
        assert isinstance(train_val_df, pd.DataFrame)
        train_val_df = train_val_df.replace([np.inf, -np.inf], np.nan)
        train_val_df = train_val_df.dropna(subset=feature_cols + ['Target_Ret_20'])
        train_val_df = train_val_df[train_val_df['Target_Ret_20'].abs() <= 10.0]
        print(f"Dataset size after cleaning NaNs, Infs, and extreme outliers: {len(train_val_df)} rows.")
        
        X = train_val_df[feature_cols]
        y = train_val_df['Target_Ret_20']
        
        # Chronological train/validation split to avoid data leakage
        # We will train on data before 2025-11-23, and validate on data after
        train_val_df['Date'] = pd.to_datetime(train_val_df['Date'])
        split_date = pd.to_datetime('2025-11-23')
        
        train_mask = train_val_df['Date'] < split_date
        val_mask = train_val_df['Date'] >= split_date
        
        X_train, y_train = X[train_mask], y[train_mask]
        X_val, y_val = X[val_mask], y[val_mask]
        
        print(f"Train samples: {len(X_train)}, Validation samples: {len(X_val)}")
        
        # 2. Train XGBoost Regressor
        print("Training XGBoost Regressor model...")
        model = xgb.XGBRegressor(
            n_estimators=150, 
            max_depth=5, 
            learning_rate=0.05, 
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        
        # Evaluation
        train_preds = model.predict(X_train)
        val_preds = model.predict(X_val)
        
        train_mae = np.mean(np.abs(train_preds - y_train))
        val_mae = np.mean(np.abs(val_preds - y_val))
        
        print(f"Training Complete. Train MAE: {train_mae:.4f}, Val MAE: {val_mae:.4f}")
        
        # Save the model
        joblib.dump(model, MODEL_PATH)
        with open(META_PATH, 'w') as f:
            json.dump({
                "features": feature_cols,
                "train_mae": float(train_mae),
                "val_mae": float(val_mae),
                "updated_at": datetime.now().isoformat()
            }, f, indent=2)
        print(f"Model saved to {MODEL_PATH}")
    else:
        # 如果是 inference_only，需要載入 meta.json 中的 features，確保特徵順序一致
        if os.path.exists(META_PATH):
            try:
                with open(META_PATH, 'r') as f:
                    meta_data = json.load(f)
                    feature_cols = meta_data.get("features", feature_cols)
                    print(f"✓ 載入 Meta 中定義的特徵欄位，總計: {len(feature_cols)} 個")
            except Exception as e:
                print(f"⚠️ 載入 meta.json 失敗，採用預設特徵: {e}")
                
    # 3. Run Inference on Latest Stock Data
    print("\nRunning ML Inference on latest trading day to score stocks...")
    if not latest_inference_rows:
        print("❌ Error: No inference data generated.")
        return
        
    inference_df = pd.DataFrame(latest_inference_rows).reset_index(drop=True)
    # Ensure all features exist
    inference_df = inference_df.dropna(subset=feature_cols)
    
    X_inf = inference_df[feature_cols]
    
    assert model is not None, "Model must be loaded or trained"
    predictions = model.predict(X_inf)
    
    inference_df['Predicted_Return_20D'] = predictions
    
    # Rank stocks by predicted 20-day return descending
    ranked_df = inference_df.sort_values(by='Predicted_Return_20D', ascending=False).reset_index(drop=True)
    
    # Structure the Top 50 Potential Stocks
    top_50_list = []
    for loop_idx, (idx, row) in enumerate(ranked_df.head(50).iterrows()):
        top_50_list.append({
            "rank": loop_idx + 1,
            "ticker": row['Ticker'],
            "code": row['Ticker'].split('.')[0],
            "name": row['Name'],
            "close": float(row['Close']),
            "predicted_return_20d": float(row['Predicted_Return_20D']),
            "date": pd.to_datetime(row['Date']).strftime('%Y-%m-%d'),
            "rsi_14": float(row['RSI_14']),
            "vol_ratio": float(row['Vol_Ratio']),
            "foreign_net_5d": float(row['Foreign_Cum_5']),
            "trust_net_5d": float(row['Trust_Cum_5']),
            "dual_force_5d": float(row['Dual_Force_5']),
            "foreign_net_20d": float(row['Foreign_Cum_20']),
            "trust_net_20d": float(row['Trust_Cum_20']),
            "eps": float(row['EPS']),
            "gross_profit_margin": float(row['Gross_Profit_Margin']),
            "operating_profit_margin": float(row['Operating_Profit_Margin']),
            "net_profit_margin": float(row['Net_Profit_Margin'])
        })
        
    with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(top_50_list, f, indent=2, ensure_ascii=False)
        
    print(f"🎉 Successfully selected Top 50 potential stocks and saved to {OUTPUT_JSON_PATH}")
    
    # Sync predictions to DuckDB
    try:
        import duckdb
        db_path = os.path.join(DATA_DIR, "potential_analysis.ddb")
        conn = duckdb.connect(db_path)
        
        pred_df = pd.DataFrame(top_50_list)
        pred_df['date'] = pd.to_datetime(pred_df['date']).dt.date
        
        # Explicitly reorder columns to match predictions table schema exactly
        pred_df_temp = pred_df[['date', 'code', 'ticker', 'name', 'close', 'predicted_return_20d', 'rsi_14', 'vol_ratio', 'foreign_net_5d', 'trust_net_5d', 'dual_force_5d', 'foreign_net_20d', 'trust_net_20d', 'rank']]
        
        conn.execute("""
            INSERT OR REPLACE INTO predictions (
                date, code, ticker, name, close, predicted_return_20d, 
                rsi_14, vol_ratio, foreign_net_5d, trust_net_5d, 
                dual_force_5d, foreign_net_20d, trust_net_20d, rank
            ) SELECT * FROM pred_df_temp
        """)
        conn.close()
        print("✓ [DuckDB] Synchronized Top 50 predictions into predictions table.")
    except Exception as d_err:
        print(f"⚠️ [DuckDB] Failed to sync predictions to database: {d_err}")
        
    print("\nTop 10 Potential Stocks Preview:")
    for stock in top_50_list[:10]:
        print(f"Rank {stock['rank']}: {stock['ticker']} ({stock['name']}) | Price: {stock['close']} | Predicted 20D Return: {stock['predicted_return_20d']*100:.2f}% | 5D Foreign: {stock['foreign_net_5d']:.1f}張 | 5D Trust: {stock['trust_net_5d']:.1f}張")

if __name__ == "__main__":
    import sys
    inference_only = "--inference-only" in sys.argv
    train_and_predict(inference_only=inference_only)
