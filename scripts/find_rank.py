import os, sys, joblib, numpy as np
sys.path.append("/Users/bookid/.hermes/scripts/ml")
from find_top_30_potentials import load_all_data_optimized, prepare_daily_features_local
from rolling_ml_orchestrator import MODEL_DIR, DAILY_FEATURES

df_all, code_to_name = load_all_data_optimized()
grouped = df_all.groupby('Code')
results = []
for code, group in grouped:
    model_path = os.path.join(MODEL_DIR, f"daily_model_{code}.pkl")
    if not os.path.exists(model_path): continue
    try:
        df_feat = prepare_daily_features_local(group)
        if df_feat is None or df_feat.empty: continue
        feats_clean = df_feat.tail(1)[DAILY_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        model = joblib.load(model_path)
        pred_ret = float(model.predict(feats_clean)[0])
        results.append({'code': code, 'name': code_to_name.get(code, code), 'pred': pred_ret})
    except: pass

results = sorted(results, key=lambda x: x['pred'], reverse=True)
for i, r in enumerate(results):
    if r['code'] == '2344':
        print(f"Rank for 2344: {i+1}, pred_return: {r['pred']:.4f}, total_processed: {len(results)}")
        break
else:
    print("2344 not found or not modeled")
