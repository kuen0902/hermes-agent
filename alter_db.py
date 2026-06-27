import duckdb

conn = duckdb.connect('/Users/bookid/.hermes/data/potential_analysis.ddb')
try:
    conn.execute('ALTER TABLE predictions ADD COLUMN risk_penalty DOUBLE;')
    print("Added risk_penalty")
except Exception as e:
    print(e)

try:
    conn.execute('ALTER TABLE predictions ADD COLUMN raw_ml_pred DOUBLE;')
    print("Added raw_ml_pred")
except Exception as e:
    print(e)

try:
    conn.execute('ALTER TABLE predictions ADD COLUMN prediction_error DOUBLE;')
    print("Added prediction_error")
except Exception as e:
    print(e)
    
conn.close()
