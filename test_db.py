import duckdb

conn = duckdb.connect('/Users/bookid/.hermes/data/potential_analysis.ddb', read_only=True)
try:
    print("Tables:", conn.execute('SHOW TABLES;').fetchall())
    res = conn.execute("SELECT count(*) FROM financial_statements").fetchone()
    print("financial_statements count:", res[0])
except Exception as e:
    print(e)
conn.close()
