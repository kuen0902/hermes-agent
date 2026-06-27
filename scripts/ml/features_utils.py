# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
import time
import duckdb

class DuckDBConnection:
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
                if "lock" in err_msg or "locked" in err_msg:
                    time.sleep(delay)
                    delay *= 2
                else: raise e
        self.conn = duckdb.connect(self.db_path, read_only=self.read_only)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn: self.conn.close()

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
    'EPS', 'Gross_Profit_Margin', 'Operating_Profit_Margin', 'Net_Profit_Margin',
    'Ret_Accelerate_5', 'Max_DD_5', 'Inst_Flow_Ratio_5D', 'Bull_Trap_Signal', 'Volatility_20D'
]

def prepare_daily_features(df):
    if len(df) < 80: return None
    df = df.copy()
    for col in ['Open', 'High', 'Low', 'Close', 'Volume', 'Foreign_Net', 'Trust_Net', 'Dealer_Net']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    for col in ['Monthly_Revenue', 'Revenue_YoY', 'Revenue_MoM', 'EPS', 'Gross_Profit_Margin', 'Operating_Profit_Margin', 'Net_Profit_Margin']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    
    df = df.dropna(subset=['Close', 'Volume'])
    df['SMA_5'] = ta.sma(df['Close'], length=5)
    df['SMA_20'] = ta.sma(df['Close'], length=20)
    df['SMA_60'] = ta.sma(df['Close'], length=60)
    df['EMA_12'] = ta.ema(df['Close'], length=12)
    df['EMA_26'] = ta.ema(df['Close'], length=26)
    df['RSI_14'] = ta.rsi(df['Close'], length=14)
    macd = ta.macd(df['Close'])
    if macd is not None: df = pd.concat([df, macd], axis=1)
    df['ATR_14'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    vol_sma = ta.sma(df['Volume'], length=20)
    df['Vol_Ratio'] = df['Volume'] / pd.Series(vol_sma, index=df.index).replace(0, 1)
    
    df['Ret_1'] = df['Close'].pct_change(1)
    df['Ret_5'] = df['Close'].pct_change(5)
    df['Ret_20'] = df['Close'].pct_change(20)
    
    df['Volatility_20D'] = df['Ret_1'].rolling(20).std()
    
    df['Foreign_Net_Ratio'] = (df['Foreign_Net'] * 1000) / df['Volume'].replace(0, 1)
    df['Foreign_Cum_5'] = df['Foreign_Net'].rolling(5).sum()
    df['Foreign_Cum_20'] = df['Foreign_Net'].rolling(20).sum()
    df['Foreign_Cum_60'] = df['Foreign_Net'].rolling(60).sum()
    df['Trust_Cum_5'] = df['Trust_Net'].rolling(5).sum()
    df['Trust_Net_Ratio'] = (df['Trust_Net'] * 1000) / df['Volume'].replace(0, 1)
    df['Dealer_Net_Ratio'] = (df['Dealer_Net'] * 1000) / df['Volume'].replace(0, 1)
    df['Trust_Cum_20'] = df['Trust_Net'].rolling(20).sum()
    df['Trust_Cum_60'] = df['Trust_Net'].rolling(60).sum()
    df['Dual_Force_5'] = df['Foreign_Cum_5'] + df['Trust_Cum_5']
    df['Dual_Force_20'] = df['Foreign_Cum_20'] + df['Trust_Cum_20']
    df['Foreign_Buy_Days_5'] = (df['Foreign_Net'] > 0).rolling(5).sum()
    df['Trust_Buy_Days_5'] = (df['Trust_Net'] > 0).rolling(5).sum()

    # --- Algorithmic Safety Updates: Falling Knife & Momentum Risk ---
    # 1. Price Momentum Acceleration (Detecting structural crashes vs healthy pullbacks)
    df['Ret_Accelerate_5'] = df['Ret_1'] - df['Ret_1'].shift(5)
    
    # 2. Downside Volatility & Drawdown (Capture risk of continuous limit-downs)
    df['Max_DD_5'] = (df['Close'] / df['High'].rolling(5).max()) - 1.0
    
    # 3. Volume-Price Synergy (Real-time Liquidity Audit)
    # High Volume + Negative Return = Distribution/Drowning
    # We compare recent 5D buying pressure vs total volume
    inst_buy_5d = df['Foreign_Net'].rolling(5).sum() + df['Trust_Net'].rolling(5).sum()
    vol_sum_5d = df['Volume'].rolling(5).sum().replace(0, 1)
    df['Inst_Flow_Ratio_5D'] = (inst_buy_5d * 1000) / vol_sum_5d
    
    # 4. Synergy Filter: If prediction is UP but institutions are EXITING, it's a structural trap
    df['Bull_Trap_Signal'] = np.where((df['Ret_5'] < -0.05) & (inst_buy_5d < 0), 1.0, 0.0)
    
    # 5. Proximity to Yearly Lows (Distressed Asset Detection)
    yearly_low = df['Low'].rolling(window=240, min_periods=60).min()
    df['Dist_Yearly_Low'] = (df['Close'] / yearly_low) - 1.0
    
    df['Target_Ret_20'] = df['Close'].shift(-20) / df['Close'] - 1.0
    return df
