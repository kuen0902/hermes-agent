import os

FILE_PATH = "/Users/bookid/.hermes/scripts/ml/rolling_ml_orchestrator.py"

with open(FILE_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if "def extract_features_for_day(today, prev_pred_prob, error_val=0.0):" in line:
        start_idx = i
    if "model_reg.fit(rolling_X, rolling_y_reg)" in line and "idx % 10 == 0:" in lines[i-2]:
        end_idx = i

if start_idx == -1 or end_idx == -1:
    print("Could not find boundaries!")
    print(start_idx, end_idx)
    exit(1)

new_code = """    def extract_features_for_all_ticks_in_day(today, prev_pred_prob, error_val=0.0):
        # 1. Today TAIEX features
        taiex_feats = taiex_features_by_date.get(today, [0.0]*5)
        
        day_data = grouped[grouped['date'] == today].sort_values('5m_bin')
        if len(day_data) < 5:
            return []
            
        prices = day_data['Close'].values
        vols = day_data['Volume'].values
        
        # Institutional (8 Dimensions) - Retrieve from O(1) memory cache!
        today_str = today.strftime("%Y-%m-%d") if hasattr(today, 'strftime') else str(today)
        d_feats = daily_features_cache.get((today_str, code), None)
        if d_feats:
            f_buy, t_buy, d_buy, f_ratio = d_feats["foreign_buy"], d_feats["trust_buy"], d_feats["dealer_buy"], d_feats["foreign_ratio"]
            t_5d, t_20d, d_5d, d_20d = d_feats["t_5d"], d_feats["t_20d"], d_feats["d_5d"], d_feats["d_20d"]
            chip_concentration = d_feats["chip_concentration"]
            large_holder_5d_diff = d_feats["large_holder_5d_diff"]
            margin_balance = d_feats["margin_balance"]
            short_margin_ratio = d_feats["short_margin_ratio"]
            major_net = d_feats["major_net"]
            major_net_5d_sum = d_feats["major_net_5d_sum"]
            revenue_yoy, revenue_mom = d_feats["revenue_yoy"], d_feats["revenue_mom"]
        else:
            f_buy = t_buy = d_buy = f_ratio = t_5d = t_20d = d_5d = d_20d = 0.0
            chip_concentration, large_holder_5d_diff, margin_balance, short_margin_ratio = 30.0, 0.0, 0.0, 0.0
            major_net, major_net_5d_sum = 0.0, 0.0
            revenue_yoy, revenue_mom = 0.0, 0.0
            
        daily_pred_ret = 0.0
        if processed_daily_features is not None:
            df_day = processed_daily_features[processed_daily_features['Date'] == today_str]
            if not df_day.empty:
                df_clean = df_day[DAILY_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0.0)
                try:
                    daily_pred_ret = float(daily_model.predict(df_clean)[0])
                except Exception:
                    pass

        tick_samples = []
        hist_before_today = daily_history[daily_history.index < today_str]
        hist_closes = list(hist_before_today.tail(239).values)
        
        for i in range(5, len(prices) + 1):
            tick_prices = prices[:i]
            tick_vols = vols[:i]
            current_close = tick_prices[-1]
            
            returns = np.diff(tick_prices) / tick_prices[:-1]
            vol_changes = np.diff(tick_vols) / (tick_vols[:-1] + 1e-9)
            
            feats = list(returns[-5:]) + list(vol_changes[-5:])
            
            close_series = pd.Series(tick_prices)
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
            feats.extend([f_buy, t_buy, d_buy, f_ratio])
            feats.extend([t_5d, t_20d, d_5d, d_20d])
            
            closes_240d = hist_closes + [current_close]
            n_days = len(closes_240d)
            
            ma5 = sum(closes_240d[-min(5, n_days):]) / min(5, n_days)
            ma10 = sum(closes_240d[-min(10, n_days):]) / min(10, n_days)
            ma20 = sum(closes_240d[-min(20, n_days):]) / min(20, n_days)
            ma60 = sum(closes_240d[-min(60, n_days):]) / min(60, n_days)
            ma120 = sum(closes_240d[-min(120, n_days):]) / min(120, n_days)
            ma240 = sum(closes_240d) / n_days
            
            bias5 = (current_close - ma5) / ma5 if ma5 else 0.0
            bias10 = (current_close - ma10) / ma10 if ma10 else 0.0
            bias20 = (current_close - ma20) / ma20 if ma20 else 0.0
            bias60 = (current_close - ma60) / ma60 if ma60 else 0.0
            bias120 = (current_close - ma120) / ma120 if ma120 else 0.0
            bias240 = (current_close - ma240) / ma240 if ma240 else 0.0
            
            spread_5_20 = (ma5 - ma20) / ma20 if ma20 else 0.0
            spread_20_60 = (ma20 - ma60) / ma60 if ma60 else 0.0
            spread_60_240 = (ma60 - ma240) / ma240 if ma240 else 0.0
            
            feats.extend([bias5, bias10, bias20, bias60, bias120, bias240, spread_5_20, spread_20_60, spread_60_240])
            feats.extend([current_close, ma5, ma20, ma60])
            feats.extend([chip_concentration, large_holder_5d_diff, margin_balance, short_margin_ratio, major_net, major_net_5d_sum])
            feats.extend([revenue_yoy, revenue_mom])
            feats.append(daily_pred_ret)
            feats.append(error_val)
            
            tick_samples.append((feats, current_close))
            
        return tick_samples

    # Pre-train Intraday Model
    pre_X = []
    pre_y_clf = []
    pre_y_reg = []
    
    prev_pred_prob = 0.5
    
    for idx in range(1, len(pretrain_dates) - 1):
        today = pretrain_dates[idx]
        tomorrow = pretrain_dates[idx+1]
        
        tick_samples = extract_features_for_all_ticks_in_day(today, prev_pred_prob, error_val=0.0)
        if not tick_samples:
            continue
            
        tomorrow_data = grouped[grouped['date'] == tomorrow].sort_values('5m_bin')
        if tomorrow_data.empty:
            continue
        tomorrow_close = tomorrow_data['Close'].values[-1]
        
        for feats, tick_close in tick_samples:
            label = 1 if tomorrow_close > tick_close else 0
            ret_val = (tomorrow_close - tick_close) / tick_close
            
            pre_X.append(feats)
            pre_y_clf.append(label)
            pre_y_reg.append(ret_val)
            
    if len(pre_X) < 10:
        print(f"⚠️ [{code}] Insufficient pre-training features extracted.")
        return False
        
    # Fit initial intraday model
    model_clf = RandomForestClassifier(n_estimators=60, max_depth=8, min_samples_leaf=3, random_state=42, n_jobs=-1)
    model_clf.fit(pre_X, pre_y_clf)
    
    model_reg = RandomForestRegressor(n_estimators=60, max_depth=8, min_samples_leaf=3, random_state=42, n_jobs=-1)
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
    error_val = 0.0  # 📌 Initialize to prevent uninitialized warning if loop doesn't execute
    
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
        
        tick_samples = extract_features_for_all_ticks_in_day(today, prev_pred_prob, error_val=error_val)
        if not tick_samples:
            continue
            
        tomorrow_data = grouped[grouped['date'] == tomorrow].sort_values('5m_bin')
        if tomorrow_data.empty:
            continue
        tomorrow_close = tomorrow_data['Close'].values[-1]
        
        # We only save calibration tracking based on the LAST tick of the day to mirror real-world end-of-day workflow
        last_feats, last_tick_close = tick_samples[-1]
        prob = float(model_clf.predict_proba([last_feats])[0][1])
        pred_ret = float(model_reg.predict([last_feats])[0])
        raw_val = last_tick_close * (1.0 + pred_ret)
        prev_calibrated_val = raw_val + bias_val  # Save for next day correction
        
        for feats, tick_close in tick_samples:
            label = 1 if tomorrow_close > tick_close else 0
            ret_val = (tomorrow_close - tick_close) / tick_close
            
            rolling_X.append(feats)
            rolling_y_clf.append(label)
            rolling_y_reg.append(ret_val)
            
        # Incremental rolling fit update (every 10 days)
        if idx % 10 == 0:
            model_clf.fit(rolling_X, rolling_y_clf)
            model_reg.fit(rolling_X, rolling_y_reg)
"""

lines = lines[:start_idx] + [new_code + "\n"] + lines[end_idx+1:]

with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Patch applied successfully!")
