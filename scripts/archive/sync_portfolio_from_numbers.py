import sys
import os
import json
import subprocess

def run_swift_script():
    script_path = os.path.expanduser("~/.hermes/scripts/extract_numbers.swift")
    if not os.path.exists(script_path):
        print(f"Error: {script_path} not found.")
        sys.exit(1)
        
    print("Running Swift script to extract data from Numbers (this may prompt for permissions)...")
    result = subprocess.run(["swift", script_path], capture_output=True, text=True)
    if result.returncode != 0:
        print("Failed to execute Swift script:")
        print(result.stderr)
        sys.exit(1)
        
    return result.stdout

def main():
    stdout = run_swift_script()
    lines = stdout.strip().split('\n')
    
    new_portfolio = {}
    
    for line in lines:
        parts = line.split('|~|')
        if len(parts) < 4:
            continue
            
        code_raw = parts[0].strip()
        # skip header
        if code_raw.lower() == 'id':
            continue
            
        # strip leading single quotes if any (common in spreadsheet text formatting)
        code = code_raw.lstrip("'")
        
        name = parts[1].strip()
        
        try:
            qty = float(parts[2].strip())
        except ValueError:
            continue
            
        try:
            price = float(parts[3].strip())
        except ValueError:
            price = 0.0
            
        if qty > 0:
            new_portfolio[code] = {
                "name": name,
                "qty": qty,
                "avg": price
            }
            
    print(f"Successfully extracted {len(new_portfolio)} stocks from Numbers.")
    
    # Update central_stock_data.json
    data_file = os.path.expanduser('~/.hermes/data/central_stock_data.json')
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to load JSON data: {e}")
        data = {"personal_data": {}}
        
    # We replace the entire personal_data to keep it strictly synced with Numbers
    old_count = len(data.get("personal_data", {}))
    data["personal_data"] = new_portfolio
    
    # Ensure stock_private_flag is preserved, if not set, default to True
    if "stock_private_flag" not in data:
        data["stock_private_flag"] = True
        
    try:
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ Portfolio synced successfully. (Previous entries: {old_count}, New entries: {len(new_portfolio)})")
    except Exception as e:
        print(f"❌ Failed to save JSON data: {e}")

if __name__ == "__main__":
    main()
