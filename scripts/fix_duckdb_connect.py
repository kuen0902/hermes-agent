import re

FILE_PATH = "/Users/bookid/.hermes/scripts/ml/rolling_ml_orchestrator.py"

with open(FILE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Target patterns like: conn = duckdb.connect(DUCK_PATH)
content = re.sub(r'conn = duckdb\.connect\(DUCK_PATH\)', r'conn = duckdb.connect(DUCK_PATH, read_only=True)', content)

with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied successfully.")
