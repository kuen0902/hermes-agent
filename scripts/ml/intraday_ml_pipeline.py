#!/Users/bookid/.hermes/.venv/bin/python
import os
import sys
import sqlite3
import duckdb
# 📌 內建指數型退避防鎖管理器 (DuckDB Resilient Lock Manager)
original_duckdb_connect = duckdb.connect
def resilient_duckdb_connect(*args, **kwargs):
    import time
    delay = 0.1
    max_retries = 5
    database = args[0] if len(args) > 0 else (kwargs.get("database", ":memory:"))
    for i in range(max_retries):
        try:
            return original_duckdb_connect(*args, **kwargs)
        except Exception as e:
            err_msg = str(e).lower()
            if "lock" in err_msg or "locked" in err_msg or "resource temporarily unavailable" in err_msg:
                print(f"⚠️ [DuckDB Lock] Database {database} is locked, retrying in {delay:.2f}s... (Attempt {i+1}/{max_retries})")
                time.sleep(delay)
                delay *= 2
            else:
                raise e
    return original_duckdb_connect(*args, **kwargs)
duckdb.connect = resilient_duckdb_connect  # type: ignore
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import urllib.request
import urllib.parse
import ssl
import requests
import matplotlib.pyplot as plt
import matplotlib
import yfinance as yf
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
import joblib
import pandas_ta_classic as ta

# 設定 matplotlib 支援中文 (macOS)
plt.rcParams['font.sans-serif'] = ['PingFang TC', 'Arial Unicode MS', 'Heiti TC']
plt.rcParams['axes.unicode_minus'] = False

DATA_DIR = os.path.expanduser("~/.hermes/data")
INTRADAY_LOG = os.path.join(DATA_DIR, "intraday_data_log.csv")
PREDICTIONS_FILE = os.path.join(DATA_DIR, "intraday_predictions.json")
VALUATIONS_FILE = os.path.join(DATA_DIR, "holdings_ml_valuations.json")

MODEL_FILE = os.path.expanduser("~/.hermes/models/intraday_model.pkl")
MODEL_REG_FILE = os.path.expanduser("~/.hermes/models/intraday_model_reg.pkl")

# Profiles Configuration (Telegram 傳送設定)
PROFILES = {
    "personal": {
        "token": "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU", # Star Platinum
        "chat_id": "6326497055",
        "data_key": "personal_data",
        "title": "個人持股"
    },
    "group": {
        "token": "8737129549:AAFtYsiaCacK9YaUP5Jd_RDw95ZpkW5ZRbU", # Star Platinum
        "chat_id": "-1003744330314",
        "data_key": "group_codes",
        "title": "高潮不斷群組"
    },
    "william": {
        "token": "8678817340:AAHLd6ObYqUUTfygY-fPf57Rw6SfOO2WEGQ", # William Bot
        "chat_id": "8695583357",
        "data_key": "william_codes",
        "title": "小智"
    }
}

def send_telegram(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    ctx = ssl._create_unverified_context()
    data = urllib.parse.urlencode({
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }).encode('utf-8')
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, context=ctx, timeout=10)
    except Exception as e:
        print(f"Telegram failed: {e}")

def send_telegram_photo(token, chat_id, caption, image_path):
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        with open(image_path, 'rb') as f:
            files = {'photo': f}
            data = {'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'}
            requests.post(url, data=data, files=files, timeout=15)
    except Exception as e:
        print(f"Telegram Photo failed: {e}")

def load_predictions():
    if os.path.exists(PREDICTIONS_FILE):
        try:
            with open(PREDICTIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_predictions(preds):
    with open(PREDICTIONS_FILE, 'w') as f:
        json.dump(preds, f, indent=2, ensure_ascii=False)

def normalize_code(code_str):
    """將代碼正規化，移除 .TW / .TWO 等後綴"""
    return str(code_str).replace(".TWO", "").replace(".TW", "").strip()

def load_current_holdings():
    """從 SQLite 載入當前真實持股代號與名稱"""
    db_path = os.path.join(DATA_DIR, "portfolio.db")
    if not os.path.exists(db_path):
        return {}
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT code, name FROM current_holdings")
        holdings = {}
        for row in cursor.fetchall():
            code = row[0]
            name = row[1]
            # 如果股名與代碼相同或是純數字，套用自動修正
            if name == code or (name and name.isdigit()):
                fixes = {
                    "3481": "群創",
                    "2330": "台積電",
                    "2317": "鴻海",
                    "2454": "聯發科",
                    "2382": "廣達",
                    "2409": "友達",
                    "2408": "南亞科",
                    "2327": "國巨",
                    "1513": "中興電",
                    "2049": "上銀",
                    "5347": "世界",
                    "4543": "萬在",
                    "3709": "鑫聯大投控",
                    "3260": "威剛",
                    "6770": "力積電",
                    "5443": "均豪",
                    "2368": "金像電",
                    "2344": "華邦電",
                    "1802": "台玻",
                    "0050": "元大台灣50",
                    "00965": "元大航太防衛科技",
                    "00981A": "主動統一台股增長",
                    "0052": "富邦科技",
                }
                name = fixes.get(code, name)
            holdings[code] = name
        conn.close()
        return holdings
    except Exception as e:
        print(f"無法讀取 SQLite 持股資訊: {e}")
        return {}

def load_latest_institutional_data(iso_date, code_normalized):
    """從 DuckDB 讀取指定日期與代號的最新三大法人數據 (張數及外資持股比)"""
    db_path = os.path.join(DATA_DIR, "portfolio.ddb")
    if not os.path.exists(db_path):
        return 0, 0, 0, 0.0
    try:
        conn = duckdb.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT foreign_buy, trust_buy, dealer_buy, foreign_ratio 
            FROM institutional_data 
            WHERE date = ? AND code = ?
        ''', (iso_date, code_normalized))
        row = cursor.fetchone()
        conn.close()
        if row:
            f_ratio = row[3] if row[3] is not None else 0.0
            return row[0], row[1], row[2], f_ratio
    except Exception as e:
        print(f"讀取 DuckDB 三大法人籌碼失敗 ({code_normalized}): {e}")
    return 0, 0, 0, 0.0

def load_rolling_institutional_data(iso_date, code_normalized):
    """計算指定日期過去 5 日與 20 日的投信與自營商累計買超"""
    db_path = os.path.join(DATA_DIR, "portfolio.ddb")
    if not os.path.exists(db_path):
        return 0, 0, 0, 0
    try:
        conn = duckdb.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT trust_buy, dealer_buy 
            FROM institutional_data 
            WHERE code = ? AND date <= ? 
            ORDER BY date DESC LIMIT 20
        ''', (code_normalized, iso_date))
        rows = cursor.fetchall()
        conn.close()
        
        trust_5d = sum(r[0] for r in rows[:5]) if rows else 0
        trust_20d = sum(r[0] for r in rows) if rows else 0
        dealer_5d = sum(r[1] for r in rows[:5]) if rows else 0
        dealer_20d = sum(r[1] for r in rows) if rows else 0
        
        return trust_5d, trust_20d, dealer_5d, dealer_20d
    except Exception as e:
        print(f"計算滾動籌碼特徵失敗 ({code_normalized}): {e}")
    return 0, 0, 0, 0

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
            pass
            
        conn.close()
        
        if df_daily.empty:
            return cache
            
        # 將 date 欄位統一轉為字串 YYYY-MM-DD
        df_daily['date_str'] = pd.to_datetime(df_daily['date']).dt.strftime('%Y-%m-%d')  # type: ignore
        
        # 建立月營收的記憶體快取，方便滾動 ASOF 查詢
        rev_cache = {}
        if not df_revenue.empty:
            df_revenue['date_str'] = pd.to_datetime(df_revenue['date']).dt.strftime('%Y-%m-%d')  # type: ignore
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
            
        df.loc[df.index[-1], 'Close'] = today_actual_close
        
        # Call shared feature generator
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from features_utils import prepare_daily_features, DAILY_FEATURES  # type: ignore
        
        df_feat = prepare_daily_features(df)
        if df_feat is None:
            return 0.0
            
        df_clean = df_feat[DAILY_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        
        daily_model = joblib.load(model_path)
        return float(daily_model.predict(df_clean.tail(1))[0])
    except Exception as e:
        return 0.0



def load_historical_ma_features(code_normalized, today_actual_close):
    """
    從 ~/Documents/StockData_History_Full 載入歷史日線資料，
    計算 5MA、10MA、20MA (月線)、60MA (季線)、120MA (半年線)、240MA (年線) 乖離率與間距。
    """
    import os
    import pandas as pd
    
    workspace_dir = os.path.expanduser("~/.hermes/data/StockData_History_Full")
    documents_dir = os.path.expanduser("~/Documents/StockData_History_Full")
    
    if os.path.exists(workspace_dir) and len(os.listdir(workspace_dir)) > 0:
        data_dir = workspace_dir
    else:
        data_dir = documents_dir
        
    if not os.path.exists(data_dir):
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        
    match_file = None
    for f in os.listdir(data_dir):
        if f.startswith(f"{code_normalized}."):
            match_file = f
            break
            
    if not match_file:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        
    try:
        df = pd.read_csv(os.path.join(data_dir, match_file))
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df = df.dropna(subset=['Close'])
        
        hist_closes = list(df['Close'].tail(239).values)
        closes_240d = hist_closes + [today_actual_close]
        
        n_days = len(closes_240d)
        if n_days == 0:
            return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
            
        ma5 = sum(closes_240d[-min(5, n_days):]) / min(5, n_days)
        ma10 = sum(closes_240d[-min(10, n_days):]) / min(10, n_days)
        ma20 = sum(closes_240d[-min(20, n_days):]) / min(20, n_days)
        ma60 = sum(closes_240d[-min(60, n_days):]) / min(60, n_days)
        ma120 = sum(closes_240d[-min(120, n_days):]) / min(120, n_days)
        ma240 = sum(closes_240d) / n_days
        
        bias5 = (today_actual_close - ma5) / ma5 if ma5 else 0.0
        bias10 = (today_actual_close - ma10) / ma10 if ma10 else 0.0
        bias20 = (today_actual_close - ma20) / ma20 if ma20 else 0.0
        bias60 = (today_actual_close - ma60) / ma60 if ma60 else 0.0
        bias120 = (today_actual_close - ma120) / ma120 if ma120 else 0.0
        bias240 = (today_actual_close - ma240) / ma240 if ma240 else 0.0
        
        spread_5_20 = (ma5 - ma20) / ma20 if ma20 else 0.0
        spread_20_60 = (ma20 - ma60) / ma60 if ma60 else 0.0
        spread_60_240 = (ma60 - ma240) / ma240 if ma240 else 0.0
        
        return bias5, bias10, bias20, bias60, bias120, bias240, spread_5_20, spread_20_60, spread_60_240, ma5, ma20, ma60
    except Exception as e:
        print(f"載入歷史均線特徵失敗 ({code_normalized}): {e}")
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0


def init_ml_db():
    db_path = os.path.join(DATA_DIR, "portfolio.ddb")
    try:
        conn = duckdb.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ml_valuation_history (
                date VARCHAR,
                code VARCHAR,
                price DOUBLE,
                prob DOUBLE,
                pred_return DOUBLE,
                raw_val DOUBLE,
                calibrated_val DOUBLE,
                bias DOUBLE,
                error DOUBLE,
                actual_price DOUBLE DEFAULT 0.0,
                PRIMARY KEY (date, code)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ml_val_code ON ml_valuation_history(code)')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"初始化 ML 估值資料庫表失敗: {e}")

def load_previous_kalman_record(code_norm, today_iso_str):
    db_path = os.path.join(DATA_DIR, "portfolio.ddb")
    try:
        conn = duckdb.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT date, calibrated_val, bias 
            FROM ml_valuation_history 
            WHERE code = ? AND date < ? 
            ORDER BY date DESC LIMIT 1
        ''', (code_norm, today_iso_str))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "date": row[0],
                "calibrated_val": row[1],
                "bias": row[2]
            }
    except Exception as e:
        print(f"讀取 DuckDB 歷史卡爾曼狀態失敗 ({code_norm}): {e}")
    return None

def update_previous_kalman_error(code_norm, prev_date_str, actual_price, error_val):
    db_path = os.path.join(DATA_DIR, "portfolio.ddb")
    try:
        conn = duckdb.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE ml_valuation_history 
            SET actual_price = ?, error = ? 
            WHERE date = ? AND code = ?
        ''', (actual_price, error_val, prev_date_str, code_norm))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"回寫 DuckDB 卡爾曼誤差失敗 ({code_norm}): {e}")

def save_current_kalman_record(date_str, code_norm, price, prob, pred_return, raw_val, calibrated_val, bias, error):
    db_path = os.path.join(DATA_DIR, "portfolio.ddb")
    try:
        conn = duckdb.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ml_valuation_history (date, code, price, prob, pred_return, raw_val, calibrated_val, bias, error, actual_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0)
            ON CONFLICT(date, code) DO UPDATE SET
                price = excluded.price,
                prob = excluded.prob,
                pred_return = excluded.pred_return,
                raw_val = excluded.raw_val,
                calibrated_val = excluded.calibrated_val,
                bias = excluded.bias,
                error = excluded.error
        ''', (date_str, code_norm, price, prob, pred_return, raw_val, calibrated_val, bias, error))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"寫入 DuckDB 今日卡爾曼紀錄失敗 ({code_norm}): {e}")

def get_adaptive_alpha(code_norm, today_iso_str, default_alpha=0.2):
    """
    基於最近 5 日的預估誤差變異數，動態計算卡爾曼自適應平滑因子 alpha。
    當最近預估誤差波動度小，信任模型，增益加大；波動度大，信任度低，降低增益過濾雜訊。
    """
    db_path = os.path.join(DATA_DIR, "portfolio.ddb")
    if not os.path.exists(db_path):
        return default_alpha
    try:
        conn = duckdb.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT error, calibrated_val 
            FROM ml_valuation_history 
            WHERE code = ? AND date < ? AND error IS NOT NULL AND error != 0.0
            ORDER BY date DESC LIMIT 5
        ''', (code_norm, today_iso_str))
        rows = cursor.fetchall()
        conn.close()
        
        if len(rows) >= 3:
            pct_errors = [r[0] / r[1] for r in rows if r[1] is not None and r[1] != 0.0]
            if len(pct_errors) >= 3:
                var_err = float(np.var(pct_errors))
                # 基準雜訊變異數設定為 1.5% 每日波動率的平方 (0.015^2 = 0.000225)
                var_noise = 0.000225
                alpha = var_err / (var_err + var_noise)
                # 限制 alpha 在安全區間 [0.05, 0.40] 之間，防止增益鎖死或極端震盪
                alpha = max(0.05, min(0.40, alpha))
                return alpha
    except Exception as e:
        print(f"⚠️ 計算自適應卡爾曼增益失敗 ({code_norm}): {e}")
    return default_alpha

def run_intraday_pipeline(silent=False, target_date=None):
    print("--- 啟動持股專屬 ML 雙指標（方向與估值）盤後預判系統 ---")
    if not os.path.exists(INTRADAY_LOG):
        print("未找到盤中資料日誌 (intraday_data_log.csv)")
        return

    # 載入當前真實持股
    holdings = load_current_holdings()
    
    # 載入訂閱/監控名單
    group_codes = []
    william_codes = []
    central_data_path = os.path.join(DATA_DIR, "central_stock_data.json")
    if os.path.exists(central_data_path):
        try:
            with open(central_data_path, 'r') as f:
                central_data = json.load(f)
                group_codes = central_data.get("group_codes", [])
                william_codes = central_data.get("william_codes", [])
        except Exception as e:
            print(f"載入監控清單失敗: {e}")
            
    # 將所有代號統一 normalize 並取聯集
    target_set = set(normalize_code(c) for c in holdings.keys())
    target_set.update(normalize_code(c) for c in group_codes)
    target_set.update(normalize_code(c) for c in william_codes)
    
    if not target_set:
        print("查無任何執行目標商品（持股與訂閱清單皆為空），跳過執行。")
        return
    print(f"商品過濾已啟用，目標商品總數 (聯集)：{len(target_set)}")

    df = pd.read_csv(INTRADAY_LOG)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    if target_date is not None:
        if isinstance(target_date, str):
            today = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            today = target_date
    else:
        today = datetime.now().date()
        
    df_today = df[df['timestamp'].dt.date == today].copy()
    
    # 判斷是否需要自動退回至最新有足夠數據 (>= 200 筆) 的交易日
    if df_today.empty or len(df_today) < 200:
        if target_date is None:
            counts = df.groupby(df['timestamp'].dt.date).size()
            valid_dates = counts[counts >= 200].index
            if len(valid_dates) > 0:
                latest_date_in_log = max(valid_dates)
                print(f"今日 ({today}) 無足夠高頻交易紀錄 (僅 {len(df_today)} 筆)，自動退回至最新有完整數據的日期 ({latest_date_in_log}) 進行預測。")
                today = latest_date_in_log
                df_today = df[df['timestamp'].dt.date == today].copy()
            else:
                print("今日無足夠高頻交易紀錄，且日誌中無任何具有足夠數據的有效日期，跳過 ML 運算。")
                return
        else:
            if df_today.empty:
                print(f"指定日期 ({today}) 無高頻交易紀錄，跳過 ML 運算。")
                return

    # 將時間序列切分為 5 分鐘級別 (Bins)
    df_today['5m_bin'] = df_today['timestamp'].dt.floor('5min')
    
    # 根據代碼與 5 分鐘區間進行分組聚合
    grouped = df_today.groupby(['code', '5m_bin']).agg({
        'price': 'last', 
        'volume': 'sum',
        'name': 'first'
    }).reset_index()
    
    # 抓取今日大盤 (TAIEX) 5 分鐘線
    taiex_features = [0.0] * 5
    try:
        taiex_data = yf.download("^TWII", period="5d", interval="5m", progress=False)
        if not taiex_data.empty:
            if taiex_data.index.tz is not None:
                taiex_data.index = taiex_data.index.tz_convert('Asia/Taipei').tz_localize(None)
            
            taiex_today = taiex_data[taiex_data.index.date == today]
            if len(taiex_today) >= 6:
                taiex_prices = taiex_today['Close'].values
                if len(taiex_prices.shape) > 1:
                    taiex_prices = taiex_prices[:, 0]
                taiex_returns = np.diff(taiex_prices) / taiex_prices[:-1]
                if len(taiex_returns) >= 5:
                    taiex_features = list(taiex_returns[-5:])
    except Exception as e:
        print(f"無法抓取大盤資料: {e}")
        
    # 載入與初始化偏差自適應資料庫表
    init_ml_db()
    
    # 預先一次性快取載入所有代碼的今日籌碼與營收特徵 (O(1) 效能優化)
    print("  ⏳ 正在為所有監控代碼批次載入日線籌碼與基本面特徵至記憶體快取...")
    daily_features_cache = load_all_daily_features_cache(list(target_set))
    print(f"  ✓ 成功快取了 {len(daily_features_cache)} 個「日期-代號」組合的特徵。")
    
    # 建立一個單一的共享 DuckDB 唯讀連接，供 get_daily_model_prediction 在迴圈中重複調用，極速查詢
    db_path = os.path.join(DATA_DIR, "potential_analysis.ddb")
    conn_pot = None
    if os.path.exists(db_path):
        try:
            conn_pot = duckdb.connect(db_path, read_only=True)
            print("  ✓ 建立共享 DuckDB 唯讀資料連接，加速每日模型預估特徵提取。")
        except Exception as conn_err:
            print(f"  ⚠️ 無法建立共享 DuckDB 連接: {conn_err}")
            
    X_infer = []
    codes_infer = []
    
    # 建立多層防禦的代碼對稱漢字股名對照字典
    code_to_name = {}
    
    # 1. 載入 SQLite 的 holdings
    for c, n in holdings.items():
        code_to_name[normalize_code(c)] = n
        
    # 2. 載入 central_stock_data.json 的 full_mapping
    full_mapping = {}
    if os.path.exists(central_data_path):
        try:
            with open(central_data_path, 'r') as f:
                central_data = json.load(f)
                full_mapping = central_data.get("full_mapping", {})
        except:
            pass
    for c, n in full_mapping.items():
        c_norm = normalize_code(c)
        if c_norm not in code_to_name:
            code_to_name[c_norm] = n
            
    # 3. 強大的 fixes 常用台灣個股對照 Fallback 字典
    fixes = {
        "3481": "群創",
        "2330": "台積電",
        "2317": "鴻海",
        "2454": "聯發科",
        "2382": "廣達",
        "2409": "友達",
        "2408": "南亞科",
        "2327": "國巨",
        "1513": "中興電",
        "2049": "上銀",
        "5347": "世界",
        "4543": "萬在",
        "3709": "鑫聯大投控",
        "3260": "威剛",
        "6770": "力積電",
        "5443": "均豪",
        "2368": "金像電",
        "2344": "華邦電",
        "1802": "台玻",
        "0050": "元大台灣50",
        "00965": "元大航太防衛科技",
        "00981A": "主動統一台股增長",
        "0052": "富邦科技",
    }
    
    import pandas_ta_classic as ta
    
    for code, group in grouped.groupby('code'):
        # 1. 商品過濾判定 (持股 + 訂閱清單)
        code_norm = normalize_code(code)
        if code_norm not in target_set:
            continue
            
        group = group.sort_values('5m_bin')
        if len(group) < 5: 
            continue
        
        prices = group['price'].values
        vols = group['volume'].values
        
        # 2. 獲取漢字股名 (多層防禦)
        name = code_to_name.get(code_norm)
        if not name or name == code_norm or name.isdigit():
            name = fixes.get(code_norm, group['name'].values[0])
        
        # 計算 5 分鐘區間漲跌幅與成交量變化
        returns = np.diff(prices) / prices[:-1]
        vol_changes = np.diff(vols) / (vols[:-1] + 1e-9)
        
        if len(returns) < 5: 
            continue
        
        # 擷取最後 5 個 5 分鐘區間作為短期動能特徵
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
        today_str = today.isoformat()
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
        
        # 3. 歷史日線 MA 乖離率與間距及原始 MA 數值
        bias5, bias10, bias20, bias60, bias120, bias240, spread_5_20, spread_20_60, spread_60_240, ma5, ma20, ma60 = load_historical_ma_features(code_norm, prices[-1])
        features.extend([bias5, bias10, bias20, bias60, bias120, bias240, spread_5_20, spread_20_60, spread_60_240])
        features.extend([prices[-1], ma5, ma20, ma60])
        
        # 4. 注入新進階籌碼與基本面特徵 (8維)
        features.extend([chip_concentration, large_holder_5d_diff, margin_balance, short_margin_ratio, major_net, major_net_5d_sum])
        features.extend([revenue_yoy, revenue_mom])
        
        # 5. 獲取日線 XGBoost 模型的 predicted return (共享 DuckDB 連線，實現極速 $O(1)$)
        daily_pred_ret_20d = get_daily_model_prediction(code_norm, today_str, prices[-1], conn=conn_pot)
        features.append(daily_pred_ret_20d)
        
        # 3. 卡爾曼式誤差反饋 (Feedback control loop) 與偏差計算
        error_val = 0.0
        bias_val = 0.0
        error_str = "今日新納入估值"
        
        # 嘗試載入個股自適應優化後的預置 rolling bias 值
        opt_bias = 0.0
        meta_path = os.path.expanduser(f"~/.hermes/models/rolling_state_{code_norm}.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    opt_bias = json.load(f).get("optimized_bias", 0.0)
            except Exception:
                pass
        
        # 自適應卡爾曼增益平滑因子 alpha 計算 (動態適應市場波動)
        alpha = get_adaptive_alpha(code_norm, today.isoformat())
        
        # 從 SQLite 載入該商品前一交易日紀錄
        prev_record = load_previous_kalman_record(code_norm, today.isoformat())
        
        if prev_record:
            prev_date = prev_record["date"]
            # 昨估今日價格 (校正後)
            prev_calibrated_val = prev_record.get("calibrated_val", prices[-1])
            prev_bias = prev_record.get("bias", 0.0)
            
            # 如果存在個股預置優化 bias，優先繼承
            if opt_bias != 0.0:
                prev_bias = opt_bias
            
            # 今日實際价格
            current_actual_price = prices[-1]
            
            # 計算昨日估值今日的誤差
            error_val = current_actual_price - prev_calibrated_val
            
            # 卡爾曼一階自適應更新長期誤差偏差偏置 (Bias)
            bias_val = prev_bias * (1.0 - alpha) + error_val * alpha
            
            error_pct = (error_val / prev_calibrated_val) * 100.0 if prev_calibrated_val else 0.0
            error_str = f"誤差: {error_val:+.2f} ({error_pct:+.2f}%) | 偏置修正: {bias_val:+.2f} (動態增益: {alpha:.3f})"
            
            # 回寫上一交易日記錄的真實誤差，方便日後稽核
            update_previous_kalman_error(code_norm, prev_date, current_actual_price, error_val)
        else:
            if opt_bias != 0.0:
                bias_val = opt_bias
                error_str = f"已套用個股預置滾動優化偏置: {bias_val:+.2f}"
        
        features.append(error_val) # 將前一日誤差本身作為反饋特徵注入 ML 特徵集
        
        X_infer.append(features)
        codes_infer.append({
            "code_norm": code_norm,
            "code_raw": str(code),
            "name": name,
            "price": prices[-1],
            "bias": bias_val,
            "error_str": error_str,
            "f_buy": f_buy,
            "t_buy": t_buy,
            "d_buy": d_buy,
            "f_ratio": f_ratio
        })

    if conn_pot:
        try:
            conn_pot.close()
        except:
            pass

    if not X_infer:
        print("持股特徵萃取數量不足。")
        return

    # 4. 機器學習雙模型（Classifier + Regressor）載入或初始化
    model_clf = None
    if os.path.exists(MODEL_FILE):
        try:
            model_clf = joblib.load(MODEL_FILE)
            if hasattr(model_clf, "n_features_in_") and model_clf.n_features_in_ != len(X_infer[0]):
                print(f"偵測到 Classifier 特徵維度不匹配 ({model_clf.n_features_in_} != {len(X_infer[0])})，將重建模型。")
                model_clf = None
        except:
            model_clf = None
        
    if model_clf is None:
        print("初始化全新 RandomForest 分類器模型...")
        model_clf = RandomForestClassifier(n_estimators=50, random_state=42)
        dummy_y = [np.random.randint(0, 2) for _ in X_infer]
        model_clf.fit(X_infer, dummy_y)
        joblib.dump(model_clf, MODEL_FILE)
        
    model_reg = None
    if os.path.exists(MODEL_REG_FILE):
        try:
            model_reg = joblib.load(MODEL_REG_FILE)
            if hasattr(model_reg, "n_features_in_") and model_reg.n_features_in_ != len(X_infer[0]):
                print(f"偵測到 Regressor 特徵維度不匹配 ({model_reg.n_features_in_} != {len(X_infer[0])})，將重建模型。")
                model_reg = None
        except:
            model_reg = None
        
    if model_reg is None:
        print("初始化全新 RandomForest 迴歸器模型...")
        model_reg = RandomForestRegressor(n_estimators=50, random_state=42)
        # 迴歸器預測明日價格變動率 (%)
        dummy_y_reg = [np.random.uniform(-0.02, 0.02) for _ in X_infer]
        model_reg.fit(X_infer, dummy_y_reg)
        joblib.dump(model_reg, MODEL_REG_FILE)

    # 5. 雙模型推理 (個股專屬模型優先載入，無則 fallback 至全局模型)
    preds_clf = []
    preds_reg = []
    
    for i, item in enumerate(codes_infer):
        code_norm = item["code_norm"]
        feats = X_infer[i]
        
        path_clf = os.path.expanduser(f"~/.hermes/models/intraday_model_{code_norm}.pkl")
        path_reg = os.path.expanduser(f"~/.hermes/models/intraday_model_reg_{code_norm}.pkl")
        
        model_clf_local = None
        if os.path.exists(path_clf):
            try:
                model_clf_local = joblib.load(path_clf)
            except:
                pass
        if model_clf_local is None:
            model_clf_local = model_clf
            
        model_reg_local = None
        if os.path.exists(path_reg):
            try:
                model_reg_local = joblib.load(path_reg)
            except:
                pass
        if model_reg_local is None:
            model_reg_local = model_reg
            
        try:
            prob = float(model_clf_local.predict_proba([feats])[0][1])
            pred_ret = float(model_reg_local.predict([feats])[0])
        except Exception as e:
            print(f"⚠️ 個股本地模型 {code_norm} 預測失敗或維度 mismatch，將 fallback 至全域模型。Error: {e}")
            prob = float(model_clf.predict_proba([feats])[0][1])
            pred_ret = float(model_reg.predict([feats])[0])
            
        preds_clf.append(prob)
        preds_reg.append(pred_ret)

    # 6. 計算收斂後估值並寫入誤差歷史
    new_predictions = {}
    trade_signals = []
    
    for i, item in enumerate(codes_infer):
        code_norm = item["code_norm"]
        price = item["price"]
        bias = item["bias"]
        
        prob = float(preds_clf[i])
        pred_return = float(preds_reg[i])
        
        # 預估明日價格 (原始值)
        raw_val = price * (1.0 + pred_return)
        
        # 預估明日價格 (收斂平滑後)
        calibrated_val = raw_val + bias
        
        # 寫入今日最新的卡爾曼預估結果 (SQLite 增量 Upsert)
        save_current_kalman_record(
            today.isoformat(),
            code_norm,
            price,
            prob,
            pred_return,
            raw_val,
            calibrated_val,
            bias,
            0.0
        )
        
        item["prob"] = prob
        item["pred_return"] = pred_return
        item["raw_val"] = raw_val
        item["calibrated_val"] = calibrated_val
        
        # 同步回舊的 predictions 結構，相容其他系統
        new_predictions[item["code_raw"]] = {
            "date": today.isoformat(),
            "price": price,
            "prob": prob
        }
        
        # 生成自動交易信號（使用雙模型強信心過濾）
        action = None
        if prob >= 0.85 and pred_return > 0.015:
            action = "add"
        elif prob <= 0.15 and pred_return < -0.015:
            action = "reduce"
            
        if action:
            trade_signals.append({
                "action": action,
                "code": item["code_raw"],
                "name": item["name"],
                "price": price,
                "qty": 1.0,
                "prob": prob,
                "pred_return": pred_return,
                "timestamp": today.isoformat()
            })
            
    save_predictions(new_predictions)
    
    if trade_signals:
        signals_file = os.path.join(DATA_DIR, "trade_signals.json")
        with open(signals_file, 'w') as f:
            json.dump({"signals": trade_signals, "generated_at": datetime.now().isoformat()}, f, indent=2, ensure_ascii=False)
        print(f"✅ 生成 {len(trade_signals)} 筆持股強信心 ML 交易信號")

    # 7. 為各 profile 生成與發送報告 (限於持股)
    for p_key, p_cfg in PROFILES.items():
        if p_key == "personal":
            profile_stocks = list(holdings.keys())
        else:
            central_data = {}
            if os.path.exists(os.path.join(DATA_DIR, "central_stock_data.json")):
                try:
                    with open(os.path.join(DATA_DIR, "central_stock_data.json"), 'r') as f:
                        central_data = json.load(f)
                except: pass
            data_val = central_data.get(p_cfg['data_key'])
            if isinstance(data_val, dict):
                profile_stocks = [normalize_code(c) for c in data_val.keys()]
            elif isinstance(data_val, list):
                profile_stocks = [normalize_code(c) for c in data_val]
            else:
                profile_stocks = []
                
        if not profile_stocks:
            continue
            
        p_report_lines = []
        p_probs = []
        p_returns = []
        p_y_labels = []
        p_f_buys = []
        p_t_buys = []
        p_d_buys = []
        p_f_ratios = []
        
        for item in codes_infer:
            code_norm = item["code_norm"]
            if code_norm not in profile_stocks:
                continue
                
            prob = item["prob"]
            pred_return = item["pred_return"]
            calibrated_val = item["calibrated_val"]
            error_str = item["error_str"]
            name = item["name"]
            
            p_probs.append(prob * 100.0)
            p_returns.append(pred_return * 100.0)
            
            # 計算多空預測方向與絕對信心指數 (以 50% 為基準)
            prob_pct = prob * 100.0
            if prob >= 0.55:
                direction_str = "偏多"
                confidence = prob_pct
            elif prob <= 0.45:
                direction_str = "偏空"
                confidence = 100.0 - prob_pct
            else:
                direction_str = "盤整"
                confidence = prob_pct if prob >= 0.5 else (100.0 - prob_pct)
            
            # Y 軸標籤大進化：融合股名、方向與信心指數、今日收盤與收斂估值
            price_now = item["price"]
            p_y_labels.append(f"{name} ({code_norm}) | {direction_str}({confidence:.0f}%)\n現價:{price_now:.1f} → 估值:{calibrated_val:.1f}")
            
            p_f_buys.append(item.get("f_buy", 0))
            p_t_buys.append(item.get("t_buy", 0))
            p_d_buys.append(item.get("d_buy", 0))
            p_f_ratios.append(item.get("f_ratio", 0.0))
            
            clean_name = name.replace("*", "\\*").replace("_", "\\_")
            signal = "🔴 偏多" if prob > 0.55 else ("🟢 偏空" if prob < 0.45 else "⚪ 盤整")
            
            # 美化條目，包含股價估值與誤差自適應修正歷程
            line_str = (
                f"▸ **{clean_name}** (`{code_norm}`): 明日 {signal}\n"
                f"  └ 方向機率: *{prob*100:.1f}%*\n"
                f"  └ 今日收盤: `${price_now:.2f}`\n"
                f"  └ 誤差校正: `{error_str}`\n"
                f"  └ 明日估值: **`${calibrated_val:.2f}`** *(誤差已自適應收斂)*\n"
            )
            p_report_lines.append(line_str)
            
        if not p_report_lines:
            continue
            
        # 🚀 繪圖展示明天的股價估計變動率 (%)、方向機率 (%) 與今日三大法人籌碼分析 (極致深色科技質感儀表板) 🚀
        plt.style.use('dark_background')
        num_items = len(p_y_labels)
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, max(5.5, num_items * 0.7)), dpi=200)
        
        # 背景配色調整：Slate 900
        fig.patch.set_facecolor('#0f172a')
        for ax in [ax1, ax2, ax3]:
            ax.set_facecolor('#0f172a')
            
        y_pos = np.arange(num_items)
        
        # --- 子圖 1：預估明日收盤漲跌幅 (%) [Regressor] ---
        colors_ret = ['#ff7675' if r > 0 else '#55efc4' for r in p_returns] # 高級珊瑚紅與薄荷綠
        bars1 = ax1.barh(y_pos, p_returns, color=colors_ret, alpha=0.85, edgecolor='#1e293b', height=0.55)
        ax1.set_xlabel("預估明日收盤漲跌幅 (%)", fontsize=11, fontweight='bold', color='#f1f5f9')
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(p_y_labels, fontsize=10, fontweight='bold', color='#cbd5e1')
        ax1.axvline(x=0.0, color='#475569', linestyle='-', alpha=0.8, linewidth=1.2)
        ax1.grid(axis='x', linestyle=':', alpha=0.5, color='#334155')
        
        # 動態調整 xlim 防止標籤溢出重疊 Y 軸
        max_ret = max([abs(r) for r in p_returns] + [0.5])
        ax1.set_xlim(-max_ret * 1.35, max_ret * 1.35)
        
        # 加上漲跌幅標籤
        for bar in bars1:
            width = bar.get_width()
            offset = max_ret * 0.05
            if width >= 0:
                ax1.text(width + offset, bar.get_y() + bar.get_height()/2, 
                         f"{width:+.2f}%", va='center', ha='left', fontweight='bold', color='#ff7675', fontsize=9)
            else:
                ax1.text(width - offset, bar.get_y() + bar.get_height()/2, 
                         f"{width:+.2f}%", va='center', ha='right', fontweight='bold', color='#55efc4', fontsize=9)
        ax1.set_title("漲跌估值預測 (Regressor)", fontsize=12, fontweight='bold', pad=10, color='#f8fafc')
        
        # --- 子圖 2：多空方向信心指數 (%) [Classifier] ---
        colors_prob = []
        for p in p_probs:
            if p >= 55.0:
                colors_prob.append('#ff7675') # 偏多：珊瑚紅
            elif p <= 45.0:
                colors_prob.append('#55efc4') # 偏空：薄荷綠
            else:
                colors_prob.append('#64748b') # 盤整：中性灰
                
        # 計算相對於 50% 的偏差值
        p_probs_deviations = [p - 50.0 for p in p_probs]
        
        # 使用 left=50.0 參數繪製對稱條形圖
        bars2 = ax2.barh(y_pos, p_probs_deviations, left=50.0, color=colors_prob, alpha=0.85, edgecolor='#1e293b', height=0.55)
        ax2.set_xlabel("多空預測與絕對信心指數 (%)", fontsize=11, fontweight='bold', color='#f1f5f9')
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels([]) # 右側不重複顯示 Y 軸標籤，維持清爽
        ax2.axvline(x=50.0, color='#94a3b8', linestyle='-', alpha=0.8, linewidth=1.5, label="多空分界 (50%)")
        ax2.set_xlim(0, 115) # 保留空間放置左右側的信心標籤
        ax2.grid(axis='x', linestyle=':', alpha=0.5, color='#334155')
        ax2.legend(loc='lower right', framealpha=0.9, facecolor='#1e293b', edgecolor='#334155', fontsize=9)
        
        # 加上多空信心標籤，偏多顯示在條形圖右側，偏空顯示在左側
        for bar, p in zip(bars2, p_probs):
            if p >= 55.0:
                lbl = f"偏多 {p:.0f}%"
                color_text = '#ff7675'
                ax2.text(p + 2, bar.get_y() + bar.get_height()/2, 
                         lbl, va='center', ha='left', fontweight='bold', color=color_text, fontsize=9)
            elif p <= 45.0:
                lbl = f"偏空 {100.0 - p:.0f}%"
                color_text = '#55efc4'
                ax2.text(p - 2, bar.get_y() + bar.get_height()/2, 
                         lbl, va='center', ha='right', fontweight='bold', color=color_text, fontsize=9)
            else:
                # 接近 50% 盤整
                lbl = f"盤整 {p:.0f}%"
                color_text = '#94a3b8'
                ax2.text(p + 2 if p >= 50 else p - 2, bar.get_y() + bar.get_height()/2, 
                         lbl, va='center', ha='left' if p >= 50 else 'right', fontweight='bold', color=color_text, fontsize=9)
                          
        ax2.set_title("多空方向信心指數 (Classifier)", fontsize=12, fontweight='bold', pad=10, color='#f8fafc')
        
        # --- 子圖 3：今日三大法人籌碼分析 (張) ---
        p_total_inst = [f + t + d for f, t, d in zip(p_f_buys, p_t_buys, p_d_buys)]
        colors_inst = ['#38bdf8' if tot > 0 else ('#818cf8' if tot < 0 else '#64748b') for tot in p_total_inst] # 合計買超為亮藍，賣超為優雅紫，無買賣為灰色
        
        bars3 = ax3.barh(y_pos, p_total_inst, color=colors_inst, alpha=0.85, edgecolor='#1e293b', height=0.55)
        ax3.set_xlabel("今日三大法人合計淨買超 (張)", fontsize=11, fontweight='bold', color='#f1f5f9')
        ax3.set_yticks(y_pos)
        ax3.set_yticklabels([]) # 維持清爽
        ax3.axvline(x=0.0, color='#475569', linestyle='-', alpha=0.8, linewidth=1.2)
        ax3.grid(axis='x', linestyle=':', alpha=0.5, color='#334155')
        
        # 計算 X 軸極限，防止標籤溢出
        max_inst = max([abs(tot) for tot in p_total_inst] + [100])
        ax3.set_xlim(-max_inst * 1.45, max_inst * 1.45)
        
        # 加上籌碼標籤
        for idx, bar in enumerate(bars3):
            width = bar.get_width()
            f_b = p_f_buys[idx]
            t_b = p_t_buys[idx]
            d_b = p_d_buys[idx]
            f_r = p_f_ratios[idx]
            
            lbl_str = f"外:{f_b:+} 投:{t_b:+} 自:{d_b:+} ({f_r:.1f}%)"
            offset = max_inst * 0.05
            if width >= 0:
                ax3.text(width + offset, bar.get_y() + bar.get_height()/2, 
                         f"+{width:.0f}張\n{lbl_str}", va='center', ha='left', fontweight='bold', color='#38bdf8', fontsize=7.5)
            else:
                ax3.text(width - offset, bar.get_y() + bar.get_height()/2, 
                         f"{width:.0f}張\n{lbl_str}", va='center', ha='right', fontweight='bold', color='#818cf8', fontsize=7.5)
                          
        ax3.set_title("今日三大法人籌碼 (張) & 外資持股比", fontsize=12, fontweight='bold', pad=10, color='#f8fafc')
        
        # 統一處理子圖邊框美化
        for ax in [ax1, ax2, ax3]:
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#334155')
            ax.spines['bottom'].set_color('#334155')
            ax.tick_params(colors='#94a3b8')
        
        # 總標題
        title_prefix = "持股" if p_key == "personal" else "監控商品"
        plt.suptitle(f"{title_prefix} ML 雙指標 & 三大法人籌碼分析圖 - {p_cfg['title']}\n數據日期: {today.strftime('%Y-%m-%d')}", 
                     fontsize=14, fontweight='bold', y=0.97, color='#f1f5f9')
        
        # 調整邊距與間距，徹底解決 Y 軸長股名與標籤的 overlap 缺陷，並保留足夠欄寬
        plt.subplots_adjust(left=0.22, right=0.96, top=0.86, bottom=0.12, wspace=0.25)
        
        image_path = os.path.join(DATA_DIR, f"daily_ml_prediction_{p_key}.png")
        plt.savefig(image_path, facecolor='#0f172a', edgecolor='none', bbox_inches='tight', dpi=200) # 提升至 200 DPI 確保高清晰度
        plt.close()
        
        # 發送 Telegram
        if p_report_lines and not silent:
            report_title = "Holdings ML 雙指標" if p_key == "personal" else "監控商品 ML 雙指標"
            msg = f"🤖 **{report_title}（方向與估值）自適應誤差收斂預測報告 ({p_cfg['title']})**\n\n"
            msg += "整合今日 5 分鐘高頻 K 線動能與最新的** SQLite 三大法人籌碼**特徵，重新校正預估明日收盤價：\n\n"
            msg += "\n".join(p_report_lines)
            send_telegram(p_cfg['token'], p_cfg['chat_id'], msg)
            print(f"已發送 {p_cfg['title']} Telegram 純文字報告。")
            
            if os.path.exists(image_path):
                send_telegram_photo(p_cfg['token'], p_cfg['chat_id'], f"📈 {p_cfg['title']} 預估收盤變動率分析圖", image_path)
                print(f"已發送 {p_cfg['title']} Telegram 圖表報告。")

if __name__ == "__main__":
    import sys
    silent_mode = "--silent" in sys.argv
    target_date = None
    for arg in sys.argv:
        if arg.startswith("--date="):
            target_date = arg.split("=")[1]
    run_intraday_pipeline(silent=silent_mode, target_date=target_date)
