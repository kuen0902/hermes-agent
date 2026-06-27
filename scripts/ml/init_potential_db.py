#!/Users/bookid/.hermes/.venv/bin/python
import os
import json
import glob
import pandas as pd
import duckdb

# Configuration
DATA_DIR = os.path.expanduser("~/.hermes/data")
SAVE_DIR = os.path.expanduser("~/.hermes/data/StockData_History_5Y")
DB_PATH = os.path.join(DATA_DIR, "potential_analysis.ddb")
ELIGIBLE_JSON_PATH = os.path.join(DATA_DIR, "eligible_5y_stocks.json")
PRED_JSON_PATH = os.path.join(DATA_DIR, "top_50_potential_stocks.json")
MAPPING_JSON_PATH = os.path.join(DATA_DIR, "stock_mapping.json")

os.makedirs(DATA_DIR, exist_ok=True)

def get_db_connection():
    return duckdb.connect(DB_PATH)

def init_tables(conn):
    """Creates tables with clean schemas and appropriate keys."""
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS daily_stock_data")
    
    # 1. Table: eligible_stocks
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eligible_stocks (
            code VARCHAR PRIMARY KEY,
            ticker VARCHAR,
            name VARCHAR,
            market VARCHAR,
            start_date DATE,
            end_date DATE,
            trading_days INT,
            avg_price_20 DOUBLE,
            avg_volume_20 DOUBLE,
            avg_value_20 DOUBLE,
            is_top_500 BOOLEAN,
            liquidity_rank INT
        )
    """)
    
    # 2. Table: daily_stock_data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_stock_data (
            date DATE,
            code VARCHAR,
            ticker VARCHAR,
            name VARCHAR,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            adj_close DOUBLE,
            volume BIGINT,
            foreign_net DOUBLE,
            trust_net DOUBLE,
            dealer_net DOUBLE,
            margin_net DOUBLE,
            major_net DOUBLE,
            short_net DOUBLE,
            short_balance DOUBLE,
            margin_balance DOUBLE,
            short_margin_ratio DOUBLE,
            large_holder_rate DOUBLE,
            retail_holder_rate DOUBLE,
            total_holders DOUBLE,
            PRIMARY KEY (date, code)
        )
    """)
    
    # Create indexes for high-performance quant queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_code ON daily_stock_data(code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_stock_data(date)")
    
    # 3. Table: predictions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            date DATE,
            code VARCHAR,
            ticker VARCHAR,
            name VARCHAR,
            close DOUBLE,
            predicted_return_20d DOUBLE,
            rsi_14 DOUBLE,
            vol_ratio DOUBLE,
            foreign_net_5d DOUBLE,
            trust_net_5d DOUBLE,
            dual_force_5d DOUBLE,
            foreign_net_20d DOUBLE,
            trust_net_20d DOUBLE,
            rank INT,
            risk_penalty DOUBLE,
            raw_ml_pred DOUBLE,
            PRIMARY KEY (date, code)
        )
    """)
    
    conn.commit()
    print("✓ [DuckDB] Database schemas initialized successfully.")

def load_eligible_stocks(conn):
    """Bulk loads the 5-year survivors list into eligible_stocks table."""
    if not os.path.exists(ELIGIBLE_JSON_PATH):
        print("⚠️ [DuckDB] eligible_5y_stocks.json not found. Skipping.")
        return
        
    with open(ELIGIBLE_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    if not data:
        return
        
    # Convert to DataFrame
    df = pd.DataFrame(data)
    df['start_date'] = pd.to_datetime(df['start_date']).dt.date
    df['end_date'] = pd.to_datetime(df['end_date']).dt.date
    
    # Explicitly reorder columns to match eligible_stocks table schema exactly
    df_temp = df[['code', 'ticker', 'name', 'market', 'start_date', 'end_date', 'trading_days', 'avg_price_20', 'avg_volume_20', 'avg_value_20', 'is_top_500', 'liquidity_rank']]
    
    # Bulk load
    conn.execute("INSERT OR REPLACE INTO eligible_stocks SELECT * FROM df_temp")
    print(f"✓ [DuckDB] Loaded {len(df)} stocks into 'eligible_stocks' table.")

def load_daily_stock_data(conn):
    """Bulk loads all merged stock price + institutional flow CSVs into daily_stock_data."""
    final_dir = os.path.expanduser("~/.hermes/data/StockData_History_Final")
    five_y_dir = os.path.expanduser("~/.hermes/data/StockData_History_5Y")
    full_dir = os.path.expanduser("~/.hermes/data/StockData_History_Full")
    
    files_final = glob.glob(os.path.join(final_dir, "*.csv")) if os.path.exists(final_dir) else []
    files_5y = glob.glob(os.path.join(five_y_dir, "*.csv")) if os.path.exists(five_y_dir) else []
    files_full = glob.glob(os.path.join(full_dir, "*.csv")) if os.path.exists(full_dir) else []
    
    unique_tickers = {}
    # Combine lists: prefer final_dir, then five_y_dir, then full_dir
    for f in files_final:
        ticker = os.path.basename(f).split('_')[0]
        unique_tickers[ticker] = f
    for f in files_5y:
        ticker = os.path.basename(f).split('_')[0]
        if ticker not in unique_tickers:
            unique_tickers[ticker] = f
    for f in files_full:
        ticker = os.path.basename(f).split('_')[0]
        if ticker not in unique_tickers:
            unique_tickers[ticker] = f
            
    csv_files = list(unique_tickers.values())
    print(f"Scanning {len(csv_files)} CSV files for DuckDB bulk load...")
    
    # Load mapping for correct CJK names
    code_to_name = {}
    if os.path.exists(MAPPING_JSON_PATH):
        try:
            with open(MAPPING_JSON_PATH, 'r', encoding='utf-8') as f:
                m = json.load(f)
                code_to_name = {v: k for k, v in m.items()}
        except Exception:
            pass
            
    loaded_count = 0
    total_records = 0
    
    # We will process files in batches for maximum speed and memory efficiency
    batch_dfs = []
    
    for idx, f in enumerate(csv_files):
        try:
            df = pd.read_csv(f)
            # Only process if institutional sync has completed for this file
            if 'Foreign_Net' not in df.columns:
                continue
                
            basename = os.path.basename(f)
            ticker = basename.split('_')[0]
            code = ticker.split('.')[0]
            
            # Calibrate name
            name = code_to_name.get(code, basename.replace('.csv', '').split('_')[1] if '_' in basename else "")
            name = name.replace('\ufffd', '').replace('*', '').strip()
            
            # Ensure columns exist, fill with 0.0 if missing
            for col in ['Foreign_Net', 'Trust_Net', 'Dealer_Net', 'Margin_Net', 'Major_Net',
                        'Short_Net', 'Short_Balance', 'Margin_Balance', 'Short_Margin_Ratio',
                        'Large_Holder_Rate', 'Retail_Holder_Rate', 'Total_Holders']:
                if col not in df.columns:
                    df[col] = 0.0
            
            # Map columns
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            df['code'] = code
            df['ticker'] = ticker
            df['name'] = name
            
            # Ensure proper columns and order
            # Handles 'Adj Close' with double quotes or spaces
            adj_col = 'Adj Close' if 'Adj Close' in df.columns else df.columns[5] # Fallback to 5th col
            df_temp = df[['Date', 'code', 'ticker', 'name', 'Open', 'High', 'Low', 'Close', adj_col, 'Volume', 
                           'Foreign_Net', 'Trust_Net', 'Dealer_Net', 'Margin_Net', 'Major_Net',
                           'Short_Net', 'Short_Balance', 'Margin_Balance', 'Short_Margin_Ratio',
                           'Large_Holder_Rate', 'Retail_Holder_Rate', 'Total_Holders']].copy()
            df_temp.columns = ['date', 'code', 'ticker', 'name', 'open', 'high', 'low', 'close', 'adj_close', 'volume', 
                               'foreign_net', 'trust_net', 'dealer_net', 'margin_net', 'major_net',
                               'short_net', 'short_balance', 'margin_balance', 'short_margin_ratio',
                               'large_holder_rate', 'retail_holder_rate', 'total_holders']
            
            batch_dfs.append(df_temp)
            loaded_count += 1
            total_records += len(df_temp)
            
            # Insert in batches of 100 files to optimize memory
            if len(batch_dfs) >= 100:
                combined_df = pd.concat(batch_dfs)
                conn.execute("INSERT OR REPLACE INTO daily_stock_data SELECT * FROM combined_df")
                batch_dfs = []
                
        except Exception as e:
            print(f"Error reading {f} for DuckDB: {e}")
            
    # Load remaining
    if batch_dfs:
        combined_df = pd.concat(batch_dfs)
        conn.execute("INSERT OR REPLACE INTO daily_stock_data SELECT * FROM combined_df")
        
    print(f"✓ [DuckDB] Vectorized bulk load complete: {loaded_count} files loaded ({total_records} daily rows).")

def load_predictions(conn):
    """Bulk loads latest ML predictions into predictions table."""
    if not os.path.exists(PRED_JSON_PATH):
        print("⚠️ [DuckDB] top_50_potential_stocks.json not found. Skipping.")
        return
        
    with open(PRED_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    if not data:
        return
        
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date']).dt.date
    
    # Explicitly reorder columns to match predictions table schema exactly
    df_temp = df[['date', 'code', 'ticker', 'name', 'close', 'predicted_return_20d', 'rsi_14', 'vol_ratio', 'foreign_net_5d', 'trust_net_5d', 'dual_force_5d', 'foreign_net_20d', 'trust_net_20d', 'rank']]
    
    conn.execute("""
        INSERT OR REPLACE INTO predictions (
            date, code, ticker, name, close, predicted_return_20d, 
            rsi_14, vol_ratio, foreign_net_5d, trust_net_5d, 
            dual_force_5d, foreign_net_20d, trust_net_20d, rank
        ) SELECT * FROM df_temp
    """)
    print(f"✓ [DuckDB] Loaded {len(df)} latest predictions into 'predictions' table.")

def main():
    print("=========================================================================")
    print("  🦆 INITIALIZING HERMES POTENTIAL STOCK ANALYTICAL DATABASE")
    print("=========================================================================")
    
    conn = get_db_connection()
    try:
        init_tables(conn)
        load_eligible_stocks(conn)
        load_daily_stock_data(conn)
        load_predictions(conn)
    finally:
        conn.close()
        
    print("=========================================================================")
    print("  🦆 DUCKDB ANALYTICAL DATABASE INITIALIZATION COMPLETE!")
    print(f"  Location: {DB_PATH}")
    print("=========================================================================")

if __name__ == "__main__":
    main()
