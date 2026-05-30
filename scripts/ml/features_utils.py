# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
import time
import duckdb

class DuckDBConnection:
    """
    Thread-safe & Process-safe DuckDB connection context manager.
    Implements retry with exponential backoff to handle database file locking gracefully.
    """
    def __init__(self, db_path, read_only=False, max_retries=5, initial_delay=0.1):
        self.db_path = db_path
        self.read_only = read_only
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.conn = None

    def __enter__(self):
        delay = self.initial_delay
        for i in range(self.max_retries):
            try:
                self.conn = duckdb.connect(self.db_path, read_only=self.read_only)
                return self.conn
            except Exception as e:
                err_msg = str(e).lower()
                if "lock" in err_msg or "locked" in err_msg or "resource temporarily unavailable" in err_msg:
                    print(f"⚠️ [DuckDB Lock] Database {self.db_path} is locked, retrying in {delay:.2f}s... (Attempt {i+1}/{self.max_retries})")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    raise e
        # Final attempt
        self.conn = duckdb.connect(self.db_path, read_only=self.read_only)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            try:
                self.conn.close()
            except:
                pass

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

def prepare_daily_features(df):
    """
    Generates 35 features for the Daily Ticker Model.
    Shared across trainer, pipeline, and rolling orchestrators to ensure 100% DRY.
    """
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
        if isinstance(macd, pd.DataFrame):
            df = pd.concat([df, macd], axis=1)
        else:
            df = df.join(pd.DataFrame(macd))
        
    df['ATR_14'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    vol_sma_val = ta.sma(df['Volume'], length=20)
    vol_sma_series = pd.Series(vol_sma_val) if vol_sma_val is not None else pd.Series(np.nan, index=df.index)
    df['VOL_SMA_20'] = vol_sma_series  # type: ignore
    df['Vol_Ratio'] = df['Volume'] / vol_sma_series.where(vol_sma_series != 0, 1.0)
    
    df['Ret_1'] = df['Close'].pct_change(1)
    df['Ret_5'] = df['Close'].pct_change(5)
    df['Ret_20'] = df['Close'].pct_change(20)
    
    df['Foreign_Net_Ratio'] = (df['Foreign_Net'] * 1000) / df['Volume'].where(df['Volume'] != 0, 1.0)
    df['Trust_Net_Ratio'] = (df['Trust_Net'] * 1000) / df['Volume'].where(df['Volume'] != 0, 1.0)
    df['Dealer_Net_Ratio'] = (df['Dealer_Net'] * 1000) / df['Volume'].where(df['Volume'] != 0, 1.0)
    
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
