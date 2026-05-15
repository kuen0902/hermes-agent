import os
import numpy as np
import pandas as pd
import yfinance as yf
import joblib
import matplotlib.pyplot as plt
import pandas_ta_classic as ta

# 設定 matplotlib 支援中文 (macOS)
plt.rcParams['font.sans-serif'] = ['PingFang TC', 'Arial Unicode MS', 'Heiti TC']
plt.rcParams['axes.unicode_minus'] = False

DATA_DIR = os.path.expanduser("~/.hermes/data")
MODEL_FILE = os.path.expanduser("~/.hermes/models/intraday_model.pkl")
REPORT_IMAGE = os.path.join(DATA_DIR, "ml_backtest_report.png")

CORE_SYMBOLS = [
    "2330.TW", "2454.TW", "3037.TW", "2382.TW", "2327.TW",
    "8996.TW", "5289.TWO", "4966.TWO", "3583.TW", "8210.TW",
    "5347.TWO", "6510.TWO", "3211.TWO", "6290.TWO", "6669.TW",
    "1513.TW", "2049.TW", "2408.TW", "2313.TW", "6285.TW"
]

LONG_TP = 0.03
LONG_SL = -0.02
SHORT_TP = -0.03
SHORT_SL = 0.02

def run_backtest():
    if not os.path.exists(MODEL_FILE):
        print("找不到訓練好的模型檔案！請先執行訓練。")
        return
        
    print("--- 啟動 60 天盤中真實獲利 (P&L) 回測引擎 ---")
    model = joblib.load(MODEL_FILE)
    
    # 預先抓取大盤資料
    print("正在抓取大盤 (^TWII) 歷史 5 分鐘高頻資料...")
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

    trades = []
    
    for symbol in CORE_SYMBOLS:
        print(f"正在模擬 {symbol} 回測...")
        try:
            df = yf.download(symbol, period="60d", interval="5m", progress=False)
            if df.empty: continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df[['Close', 'Volume']].dropna().reset_index()
            df.rename(columns={'Datetime': 'timestamp'}, inplace=True)
            if df['timestamp'].dt.tz is not None:
                df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Taipei').dt.tz_localize(None)
            df['5m_bin'] = df['timestamp'].dt.floor('5min')
            df['date'] = df['timestamp'].dt.date
            
            grouped = df.groupby(['date', '5m_bin']).agg({'Close': 'last', 'Volume': 'sum'}).reset_index()
            dates = sorted(grouped['date'].unique())
            
            prev_pred_prob = 0.5
            
            for i in range(len(dates) - 1):
                today = dates[i]
                tomorrow = dates[i+1]
                
                # 萃取大盤特徵
                taiex_features = [0.0] * 5
                t_day = taiex_grouped[taiex_grouped['date'] == today].sort_values('5m_bin')
                if len(t_day) >= 6:
                    t_prices = t_day['Close'].values
                    t_returns = np.diff(t_prices) / t_prices[:-1]
                    if len(t_returns) >= 5: taiex_features = list(t_returns[-5:])
                        
                day_data = grouped[grouped['date'] == today].sort_values('5m_bin')
                tomorrow_data = grouped[grouped['date'] == tomorrow].sort_values('5m_bin')
                if len(day_data) < 5 or len(tomorrow_data) < 1: continue
                    
                prices = day_data['Close'].values
                vols = day_data['Volume'].values
                returns = np.diff(prices) / prices[:-1]
                vol_changes = np.diff(vols) / (vols[:-1] + 1e-9)
                if len(returns) < 5: continue
                
                features = list(returns[-5:]) + list(vol_changes[-5:])
                
                close_series = pd.Series(prices)
                rsi_val = 50.0
                if len(close_series) > 14:
                    rsi_series = ta.rsi(close_series, length=14)
                    if rsi_series is not None and not rsi_series.empty:
                        val = rsi_series.iloc[-1]
                        if not pd.isna(val): rsi_val = val
                        
                macd_line, macd_hist = 0.0, 0.0
                if len(close_series) > 26:
                    macd_df = ta.macd(close_series, fast=12, slow=26, signal=9)
                    if macd_df is not None and not macd_df.empty:
                        m_line = macd_df.iloc[-1, 0]
                        m_hist = macd_df.iloc[-1, 1]
                        if not pd.isna(m_line): macd_line = m_line
                        if not pd.isna(m_hist): macd_hist = m_hist
                        
                features.extend([rsi_val, macd_line, macd_hist])
                features.extend(taiex_features)
                
                actual_today_pct = (prices[-1] - prices[0]) / prices[0]
                predicted_today_pct = (prev_pred_prob - 0.5) * 2.0
                var = actual_today_pct - predicted_today_pct
                features.append(var)
                
                # 預測明日
                prob = model.predict_proba([features])[0][1]
                prev_pred_prob = prob
                
                # 盤中交易模擬 (Tomorrow)
                t_prices = tomorrow_data['Close'].values
                entry_price = t_prices[0]
                trade_return = 0.0
                
                if prob > 0.55: # 做多
                    for p in t_prices[1:]:
                        r = (p - entry_price) / entry_price
                        if r >= LONG_TP:
                            trade_return = LONG_TP
                            break
                        if r <= LONG_SL:
                            trade_return = LONG_SL
                            break
                    if trade_return == 0.0:
                        trade_return = (t_prices[-1] - entry_price) / entry_price
                        
                elif prob < 0.45: # 做空
                    for p in t_prices[1:]:
                        r = (p - entry_price) / entry_price
                        if r <= SHORT_TP: # 跌了，空單獲利
                            trade_return = abs(SHORT_TP) # 空單獲利是正的
                            break
                        if r >= SHORT_SL: # 漲了，空單虧損
                            trade_return = -SHORT_SL # 空單虧損是負的
                            break
                    if trade_return == 0.0:
                        trade_return = -(t_prices[-1] - entry_price) / entry_price
                else:
                    continue # 不交易
                    
                trades.append({'date': tomorrow, 'symbol': symbol, 'return': trade_return})
                
        except Exception as e:
            print(f"Error {symbol}: {e}")

    if not trades:
        print("沒有足夠的交易訊號進行回測。")
        return
        
    df_trades = pd.DataFrame(trades)
    daily_returns = df_trades.groupby('date')['return'].mean().reset_index()
    daily_returns['equity_curve'] = (1 + daily_returns['return']).cumprod()
    
    total_trades = len(df_trades)
    win_rate = (df_trades['return'] > 0).mean()
    total_return = daily_returns['equity_curve'].iloc[-1] - 1
    
    # 計算最大回撤 (Max Drawdown)
    cum_max = daily_returns['equity_curve'].cummax()
    drawdown = (daily_returns['equity_curve'] - cum_max) / cum_max
    max_drawdown = drawdown.min()
    
    print("\n========== 實戰回測績效報告 ==========")
    print(f"交易期間：{daily_returns['date'].iloc[0]} ~ {daily_returns['date'].iloc[-1]}")
    print(f"總交易次數：{total_trades} 次")
    print(f"真實勝率：{win_rate*100:.2f}%")
    print(f"總累積報酬率：{total_return*100:.2f}%")
    print(f"最大回撤 (MDD)：{max_drawdown*100:.2f}%")
    print("======================================\n")
    
    # 繪圖
    plt.figure(figsize=(12, 6))
    plt.plot(daily_returns['date'], daily_returns['equity_curve'], label='累積資產 (Equity Curve)', color='blue', linewidth=2)
    plt.fill_between(daily_returns['date'], 1.0, daily_returns['equity_curve'], alpha=0.1, color='blue')
    plt.axhline(y=1.0, color='red', linestyle='--', alpha=0.5)
    plt.title(f"Hermes ML 高頻策略 60 天實戰回測\n總報酬: {total_return*100:.2f}% | 勝率: {win_rate*100:.2f}% | MDD: {max_drawdown*100:.2f}%")
    plt.xlabel("日期")
    plt.ylabel("資產淨值 (1.0 = 起始本金)")
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig(REPORT_IMAGE)
    print(f"已生成累積資產圖表：{REPORT_IMAGE}")

if __name__ == "__main__":
    run_backtest()
