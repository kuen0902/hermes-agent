#!/Users/bookid/.hermes/.venv/bin/python
# -*- coding: utf-8 -*-
import os
import pandas as pd
import numpy as np
import yfinance as yf
import sqlite3
import duckdb
import pandas_ta_classic as ta
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score
import joblib

DATA_DIR = os.path.expanduser("~/.hermes/data")
MODEL_DIR = os.path.expanduser("~/.hermes/models")
MODEL_FILE = os.path.join(MODEL_DIR, "intraday_model.pkl")
MODEL_REG_FILE = os.path.join(MODEL_DIR, "intraday_model_reg.pkl")

# Core target symbols for generic training (20 key stocks)
CORE_SYMBOLS = [
    "2330.TW", "2454.TW", "3037.TW", "2382.TW", "2327.TW",
    "8996.TW", "5289.TWO", "4966.TWO", "3583.TW", "8210.TW",
    "5347.TWO", "6510.TWO", "3211.TWO", "6290.TWO", "6669.TW",
    "1513.TW", "2049.TW", "2408.TW", "2313.TW", "6285.TW", "^TWII"
]

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

def load_symbol_daily_history(symbol):
    """
    載入指定商品（如 2330.TW）的日線歷史關閉價格，
    回傳以 Date 為 Index 的 pandas Series。
    """
    code_norm = symbol.split(".")[0]
    workspace_dir = os.path.expanduser("~/.hermes/data/StockData_History_Final")
    documents_dir = os.path.expanduser("~/Documents/StockData_History_Final")
    
    if os.path.exists(workspace_dir) and len(os.listdir(workspace_dir)) > 0:
        data_dir = workspace_dir
    else:
        data_dir = documents_dir
        
    if not os.path.exists(data_dir):
        return pd.Series(dtype='float64', index=pd.Index([], dtype='object'))
        
    match_file = None
    for f in os.listdir(data_dir):
        if f.startswith(f"{code_norm}."):
            match_file = f
            break
            
    if not match_file:
        return pd.Series(dtype='float64', index=pd.Index([], dtype='object'))
        
    try:
        df = pd.read_csv(os.path.join(data_dir, match_file))
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df = df.dropna(subset=['Close', 'Date'])
        # 📌 強制轉換日期欄位為字串 YYYY-MM-DD 格式，避免 int64 比較錯誤
        df['Date'] = pd.to_datetime(df['Date'].values).strftime('%Y-%m-%d')
        return pd.Series(df['Close'].values, index=df['Date'])
    except Exception as e:
        print(f"載入歷史日線資料失敗 ({symbol}): {e}")
        return pd.Series(dtype='float64', index=pd.Index([], dtype='object'))

def load_all_daily_features_cache(active_codes):
    """
    一次性自 DuckDB 批次載入所有個股的日線籌碼與基本面特徵，快取於記憶體中，
    消除迴圈內高頻開啟資料庫的效能黑洞 (O(1) 效能優化)。
    """
    cache = {}
    db_path = os.path.join(DATA_DIR, "potential_analysis.ddb")
    port_path = os.path.join(DATA_DIR, "portfolio.ddb")
    
    if not os.path.exists(db_path):
        return cache
        
    try:
        conn = duckdb.connect(db_path, read_only=True)
        if os.path.exists(port_path):
            conn.execute(f"ATTACH '{port_path}' AS port")
            
        codes_placeholder = ", ".join([f"'{c}'" for c in active_codes])
        
        query = f"""
            SELECT 
                d.date, d.code,
                d.foreign_net, d.trust_net, d.dealer_net,
                COALESCE(i.foreign_ratio, 0.0) AS foreign_ratio,
                d.large_holder_rate, d.retail_holder_rate, d.margin_balance, 
                d.short_margin_ratio, d.major_net
            FROM daily_stock_data d
            LEFT JOIN port.institutional_data i
              ON d.date = CAST(i.date AS DATE) AND d.code = i.code
            WHERE d.code IN ({codes_placeholder})
        """
        df_daily = conn.execute(query).fetchdf()
        
        # 讀取月營收
        df_revenue = pd.DataFrame()
        try:
            df_revenue = conn.execute(f"""
                SELECT date, code, yoy, mom 
                FROM monthly_revenue 
                WHERE code IN ({codes_placeholder})
            """).fetchdf()
        except Exception as rev_err:
            print(f"  ⚠️ 無法讀取月營收資料表: {rev_err}")
            
        conn.close()
        
        if df_daily.empty:
            return cache
            
        # 將 date 欄位統一轉為字串 YYYY-MM-DD
        df_daily['date_str'] = df_daily['date'].astype(str).str.slice(0, 10)
        
        # 建立月營收的記憶體快取，方便滾動 ASOF 查詢
        rev_cache = {}
        if not df_revenue.empty:
            df_revenue['date_str'] = df_revenue['date'].astype(str).str.slice(0, 10)
            # 按代號分組，排序日期
            for code, grp in df_revenue.groupby('code'):
                grp_sorted = grp.sort_values('date_str')
                rev_cache[code] = {
                    "dates": grp_sorted['date_str'].tolist(),
                    "yoy": grp_sorted['yoy'].tolist(),
                    "mom": grp_sorted['mom'].tolist()
                }
                
        # 排序並計算滾動特徵
        df_daily = df_daily.sort_values(['code', 'date_str'])
        
        # 集保大戶 5日 變動與主力 5日 滾動累計
        df_daily['large_holder_5d_diff'] = df_daily.groupby('code')['large_holder_rate'].diff(5).fillna(0.0)
        df_daily['major_net_5d_sum'] = df_daily.groupby('code')['major_net'].rolling(5).sum().reset_index(0, drop=True).fillna(0.0)
        
        # 投信與自營商滾動累計買賣超
        df_daily['trust_buy_5d'] = df_daily.groupby('code')['trust_net'].rolling(5).sum().reset_index(0, drop=True).fillna(0.0)
        df_daily['trust_buy_20d'] = df_daily.groupby('code')['trust_net'].rolling(20).sum().reset_index(0, drop=True).fillna(0.0)
        df_daily['dealer_buy_5d'] = df_daily.groupby('code')['dealer_net'].rolling(5).sum().reset_index(0, drop=True).fillna(0.0)
        df_daily['dealer_buy_20d'] = df_daily.groupby('code')['dealer_net'].rolling(20).sum().reset_index(0, drop=True).fillna(0.0)
        
        # 構建快取字典
        for _, row in df_daily.iterrows():
            c = str(row['code'])
            d_str = str(row['date_str'])
            
            # 尋找月營收
            yoy = 0.0
            mom = 0.0
            if c in rev_cache:
                rev_dates = rev_cache[c]["dates"]
                idx = -1
                for k, rd in enumerate(rev_dates):
                    if rd <= d_str:
                        idx = k
                    else:
                        break
                if idx != -1:
                    yoy = rev_cache[c]["yoy"][idx]
                    mom = rev_cache[c]["mom"][idx]
            
            # 計算大戶與散戶對峙比
            large_rate = row['large_holder_rate'] if row['large_holder_rate'] is not None else 50.0
            retail_rate = row['retail_holder_rate'] if row['retail_holder_rate'] is not None else 20.0
            concentration = large_rate - retail_rate
            
            cache[(d_str, c)] = {
                "foreign_buy": row['foreign_net'] if row['foreign_net'] is not None else 0.0,
                "trust_buy": row['trust_net'] if row['trust_net'] is not None else 0.0,
                "dealer_buy": row['dealer_net'] if row['dealer_net'] is not None else 0.0,
                "foreign_ratio": row['foreign_ratio'] if row['foreign_ratio'] is not None else 0.0,
                "t_5d": row['trust_buy_5d'],
                "t_20d": row['trust_buy_20d'],
                "d_5d": row['dealer_buy_5d'],
                "d_20d": row['dealer_buy_20d'],
                "large_holder_rate": large_rate,
                "retail_holder_rate": retail_rate,
                "chip_concentration": concentration,
                "large_holder_5d_diff": row['large_holder_5d_diff'],
                "margin_balance": row['margin_balance'] if row['margin_balance'] is not None else 0.0,
                "short_margin_ratio": row['short_margin_ratio'] if row['short_margin_ratio'] is not None else 0.0,
                "major_net": row['major_net'] if row['major_net'] is not None else 0.0,
                "major_net_5d_sum": row['major_net_5d_sum'],
                "revenue_yoy": yoy,
                "revenue_mom": mom
            }
    except Exception as e:
        print(f"⚠️ 載入日線與月營收特徵快取時發生錯誤: {e}")
        
    return cache

def get_daily_model_prediction(code_normalized, today_str, today_actual_close, conn=None):
    """
    調用日線 XGBoost 模型預測今日的 20d 變動率。
    支援外部傳入共享的 DuckDB 連接，徹底避免在迴圈中開啟資料庫 (O(1) 效能提升)。
    """
    model_path = os.path.expanduser(f"~/.hermes/models/daily_model_{code_normalized}.pkl")
    if not os.path.exists(model_path):
        return 0.0
    try:
        close_conn = False
        if conn is None:
            db_path = os.path.join(DATA_DIR, "potential_analysis.ddb")
            conn = duckdb.connect(db_path, read_only=True)
            close_conn = True
            
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
            WHERE d.code = ? AND d.date <= ?
            ORDER BY d.date ASC
        """, (code_normalized, today_str)).fetchdf()
        
        if close_conn:
            conn.close()
            
        if df.empty or len(df) < 20:
            return 0.0
            
        close_col_idx = int(df.columns.get_indexer(pd.Index(['Close']))[0])  # type: ignore
        df.iat[len(df) - 1, close_col_idx] = today_actual_close
        
        df = df.copy()
        df['SMA_5'] = ta.sma(df['Close'], length=5)
        df['SMA_20'] = ta.sma(df['Close'], length=20)
        df['SMA_60'] = ta.sma(df['Close'], length=60)
        df['EMA_12'] = ta.ema(df['Close'], length=12)
        df['EMA_26'] = ta.ema(df['Close'], length=26)
        df['RSI_14'] = ta.rsi(df['Close'], length=14)
        
        macd = ta.macd(df['Close'])
        if macd is not None:
            df = df.join(pd.DataFrame(macd))  # type: ignore
            
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
        
        df_clean = df[DAILY_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        
        daily_model = joblib.load(model_path)
        return float(daily_model.predict(df_clean.tail(1))[0])
    except Exception as e:
        return 0.0

def train_model():
    print("--- 啟動歷史 5 分鐘 K 線預訓練引擎 (Pre-training) ---")
    print(f"目標股票數量：{len(CORE_SYMBOLS)}")
    
    # 預先一次性快取載入所有代碼的歷史日線與基本面特徵 (O(1) 優化)
    active_codes = [s.split(".")[0] for s in CORE_SYMBOLS if s != "^TWII"]
    print("  ⏳ 正在為所有監控代碼批次載入日線籌碼與基本面特徵至記憶體快取...")
    daily_features_cache = load_all_daily_features_cache(active_codes)
    print(f"  ✓ 成功快取了 {len(daily_features_cache)} 個「日期-代號」組合的特徵。")
    
    # 預先抓取大盤資料
    print("正在抓取大盤 (^TWII) 過去 60 天的 5 分鐘高頻資料...")
    try:
        taiex_df = yf.download("^TWII", period="60d", interval="5m", progress=False)
        if isinstance(taiex_df.columns, pd.MultiIndex):
            taiex_df.columns = taiex_df.columns.get_level_values(0)
        taiex_df = taiex_df[['Close']].dropna().reset_index()
        taiex_df.rename(columns={'Datetime': 'timestamp'}, inplace=True)
        if taiex_df['timestamp'].dt.tz is not None:
            taiex_df['timestamp'] = taiex_df['timestamp'].dt.tz_convert('Asia/Taipei').dt.tz_localize(None)
        taiex_df['5m_bin'] = taiex_df['timestamp'].dt.floor('5min')
        taiex_df['date'] = taiex_df['timestamp'].dt.date
        taiex_grouped = taiex_df.groupby(['date', '5m_bin']).agg({'Close': 'last'}).reset_index()
    except Exception as e:
        print(f"大盤資料抓取失敗: {e}")
        taiex_grouped = pd.DataFrame(columns=['date', '5m_bin', 'Close'])
    
    all_X = []
    all_y_clf = []
    all_y_reg = []
    
    # 建立一個單一的共享 DuckDB 唯讀連接，供 get_daily_model_prediction 在迴圈中重複調用，極速查詢
    db_path = os.path.join(DATA_DIR, "potential_analysis.ddb")
    conn_pot = None
    if os.path.exists(db_path):
        try:
            conn_pot = duckdb.connect(db_path, read_only=True)
            print("  ✓ 建立共享 DuckDB 唯讀資料連接，加速每日模型預估特徵提取。")
        except Exception as conn_err:
            print(f"  ⚠️ 無法建立共享 DuckDB 連接: {conn_err}")
            
    for symbol in CORE_SYMBOLS:
        if symbol == "^TWII": continue
        code_norm = symbol.split(".")[0]
        print(f"正在抓取 {symbol} 過去 60 天的 5 分鐘高頻資料...")
        try:
            # Download 60 days of 5-minute data
            df = yf.download(symbol, period="60d", interval="5m", progress=False)
            if df.empty:
                continue
                
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            df = df[['Close', 'Volume']].dropna()
            df = df.reset_index()
            df.rename(columns={'Datetime': 'timestamp'}, inplace=True)
            
            if df['timestamp'].dt.tz is not None:
                df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Taipei').dt.tz_localize(None)
                
            df['5m_bin'] = df['timestamp'].dt.floor('5min')
            df['date'] = df['timestamp'].dt.date
            
            grouped = df.groupby(['date', '5m_bin']).agg({
                'Close': 'last',
                'Volume': 'sum'
            }).reset_index()
            
            daily_history = load_symbol_daily_history(symbol)
            dates = sorted(grouped['date'].unique())
            prev_pred_prob = 0.5
            
            for i in range(1, len(dates) - 1):
                today = dates[i]
                tomorrow = dates[i+1]
                today_str = today.isoformat()
                
                # 1. 大盤特徵
                taiex_features = [0.0] * 5
                taiex_day_data = taiex_grouped[taiex_grouped['date'] == today].sort_values('5m_bin')
                if len(taiex_day_data) >= 6:
                    t_prices = taiex_day_data['Close'].values
                    t_returns = np.diff(t_prices) / t_prices[:-1]
                    if len(t_returns) >= 5:
                        taiex_features = list(t_returns[-5:])
                        
                day_data = grouped[grouped['date'] == today].sort_values('5m_bin')
                tomorrow_data = grouped[grouped['date'] == tomorrow].sort_values('5m_bin')
                
                if len(day_data) < 5 or len(tomorrow_data) < 1:
                    continue
                    
                prices = day_data['Close'].values
                vols = day_data['Volume'].values
                
                returns = np.diff(prices) / prices[:-1]
                vol_changes = np.diff(vols) / (vols[:-1] + 1e-9)
                
                if len(returns) < 5:
                    continue
                    
                # 擷取最後 5 期區間高頻特徵
                features = list(returns[-5:]) + list(vol_changes[-5:])
                
                # 計算技術指標
                close_series = pd.Series(prices)
                
                # RSI(14)
                if len(close_series) > 14:
                    rsi_series = ta.rsi(close_series, length=14)  # type: ignore
                    if rsi_series is not None and not rsi_series.empty:
                        rsi_val = rsi_series.iloc[-1]
                        if pd.isna(rsi_val): rsi_val = 50.0
                    else:
                        rsi_val = 50.0
                else:
                    rsi_val = 50.0
                    
                # MACD(12, 26, 9)
                if len(close_series) > 26:
                    macd_df = ta.macd(close_series, fast=12, slow=26, signal=9)  # type: ignore
                    if macd_df is not None and not macd_df.empty:
                        macd_line = macd_df.iloc[-1, 0]
                        macd_hist = macd_df.iloc[-1, 1]
                        if pd.isna(macd_line): macd_line = 0.0
                        if pd.isna(macd_hist): macd_hist = 0.0
                    else:
                        macd_line, macd_hist = 0.0, 0.0
                else:
                    macd_line, macd_hist = 0.0, 0.0
                    
                features.extend([rsi_val, macd_line, macd_hist])
                features.extend(taiex_features)
                
                # 2. 記憶體 O(1) 獲取今日最新籌碼與營收特徵
                d_feats = daily_features_cache.get((today_str, code_norm), None)
                if d_feats:
                    f_buy = d_feats["foreign_buy"]
                    t_buy = d_feats["trust_buy"]
                    d_buy = d_feats["dealer_buy"]
                    f_ratio = d_feats["foreign_ratio"]
                    
                    t_5d = d_feats["t_5d"]
                    t_20d = d_feats["t_20d"]
                    d_5d = d_feats["d_5d"]
                    d_20d = d_feats["d_20d"]
                    
                    chip_concentration = d_feats["chip_concentration"]
                    large_holder_5d_diff = d_feats["large_holder_5d_diff"]
                    margin_balance = d_feats["margin_balance"]
                    short_margin_ratio = d_feats["short_margin_ratio"]
                    major_net = d_feats["major_net"]
                    major_net_5d_sum = d_feats["major_net_5d_sum"]
                    
                    revenue_yoy = d_feats["revenue_yoy"]
                    revenue_mom = d_feats["revenue_mom"]
                else:
                    f_buy = t_buy = d_buy = f_ratio = 0.0
                    t_5d = t_20d = d_5d = d_20d = 0.0
                    chip_concentration = 30.0
                    large_holder_5d_diff = 0.0
                    margin_balance = 0.0
                    short_margin_ratio = 0.0
                    major_net = 0.0
                    major_net_5d_sum = 0.0
                    revenue_yoy = 0.0
                    revenue_mom = 0.0
                    
                features.extend([f_buy, t_buy, d_buy, f_ratio])
                features.extend([t_5d, t_20d, d_5d, d_20d])
                
                # 3. 歷史日線 MA 乖離率與間距
                hist_before_today = daily_history[daily_history.index < today_str]
                hist_closes = list(hist_before_today.tail(239).values)
                closes_240d = hist_closes + [prices[-1]]
                n_days = len(closes_240d)
                
                if n_days > 0:
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
                else:
                    bias5 = bias10 = bias20 = bias60 = bias120 = bias240 = 0.0
                    spread_5_20 = spread_20_60 = spread_60_240 = 0.0
                    ma5 = ma20 = ma60 = 0.0
                    
                features.extend([bias5, bias10, bias20, bias60, bias120, bias240, spread_5_20, spread_20_60, spread_60_240])
                features.extend([prices[-1], ma5, ma20, ma60])
                
                # 4. 注入新進階籌碼與基本面特徵 (8維)
                features.extend([chip_concentration, large_holder_5d_diff, margin_balance, short_margin_ratio, major_net, major_net_5d_sum])
                features.extend([revenue_yoy, revenue_mom])
                
                # 5. 獲取日線 XGBoost 模型的 predicted return (共享 DuckDB 連線，實現極速 $O(1)$)
                daily_pred_ret_20d = get_daily_model_prediction(code_norm, today_str, prices[-1], conn=conn_pot)
                features.append(daily_pred_ret_20d)
                
                # 6. 卡爾曼誤差反饋
                actual_today_pct = (prices[-1] - prices[0]) / prices[0]
                predicted_today_pct = (prev_pred_prob - 0.5) * 2.0
                var = actual_today_pct - predicted_today_pct
                features.append(var)
                
                # 預估目標
                tomorrow_close = tomorrow_data['Close'].values[-1]
                label = 1 if tomorrow_close > prices[-1] else 0
                tomorrow_return = (tomorrow_close - prices[-1]) / prices[-1]
                
                all_X.append(features)
                all_y_clf.append(label)
                all_y_reg.append(tomorrow_return)
                
                prev_pred_prob = 0.55 if label == 1 else 0.45

        except Exception as e:
            import traceback
            print(f"Error processing {symbol}: {e}")
            traceback.print_exc()
            continue

    if conn_pot:
        try:
            conn_pot.close()
        except:
            pass

    if not all_X:
        print("未成功萃取到任何特徵！")
        return
        
    print(f"特徵萃取完成，總樣本數：{len(all_X)}，特徵維度：{len(all_X[0])}")
    
    # 訓練分類器 (49維)
    print("正在訓練 RandomForest 分類器 (49維)...")
    model_clf = RandomForestClassifier(n_estimators=150, max_depth=10, min_samples_leaf=3, random_state=42)
    model_clf.fit(all_X, all_y_clf)
    
    # 計算分類器訓練集準確率
    preds_clf = model_clf.predict(all_X)
    acc = accuracy_score(all_y_clf, preds_clf)
    print(f"分類器訓練完成！訓練集準確率 (Accuracy): {acc*100:.2f}%")
    
    # 訓練迴歸器 (49維)
    print("正在訓練 RandomForest 迴歸器 (49維)...")
    model_reg = RandomForestRegressor(n_estimators=150, max_depth=10, min_samples_leaf=3, random_state=42)
    model_reg.fit(all_X, all_y_reg)
    print("迴歸器訓練完成！")
    
    # 儲存雙模型
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model_clf, MODEL_FILE)
    joblib.dump(model_reg, MODEL_REG_FILE)
    print(f"分類器已匯出至 {MODEL_FILE}")
    print(f"迴歸器已匯出至 {MODEL_REG_FILE}")

if __name__ == "__main__":
    train_model()
