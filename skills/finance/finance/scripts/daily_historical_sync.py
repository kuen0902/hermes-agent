import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import json
import requests
from bs4 import BeautifulSoup
import urllib3
import time

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
DATA_DIR = os.path.expanduser("~/Documents/StockData_History_Final")
os.makedirs(DATA_DIR, exist_ok=True)

def get_tw_stock_list():
    stocks = {}
    for mode in [2, 4]:
        url = f"https://isin.twse.com.tw/isin/C_public.jsp?strMode={mode}"
        try:
            response = requests.get(url, timeout=15, verify=False)
            response.encoding = 'big5'
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'class': 'h4'})
            for row in table.find_all('tr')[1:]:
                tds = row.find_all('td')
                if len(tds) < 1: continue
                text = tds[0].text.strip()
                parts = text.split('\u3000')
                if len(parts) == 2:
                    code, name = parts
                    if len(code) == 4 and code.isdigit():
                        suffix = ".TW" if mode == 2 else ".TWO"
                        stocks[code + suffix] = name
        except: continue
    return stocks

def sync_all():
    print(f"--- Starting Daily Historical Sync ---")
    symbols_map = get_tw_stock_list()
    all_symbols = list(symbols_map.keys())
    existing_files = {f.split('_')[0]: f for f in os.listdir(DATA_DIR) if f.endswith('.csv')}
    
    to_update = [s for s in all_symbols if s in existing_files]
    end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
    
    chunk_size = 100
    for i in range(0, len(to_update), chunk_size):
        chunk = to_update[i:i+chunk_size]
        try:
            # treads=False to avoid SQLite lock errors
            data = yf.download(chunk, start=start_date, end=end_date, group_by='ticker', threads=False, progress=False)
            for ticker in chunk:
                try:
                    new_rows = data[ticker].dropna() if len(chunk) > 1 else data.dropna()
                    if new_rows.empty: continue
                    file_path = os.path.join(DATA_DIR, existing_files[ticker])
                    old_df = pd.read_csv(file_path)
                    combined = pd.concat([old_df, new_rows.reset_index()])
                    combined['Date'] = pd.to_datetime(combined['Date']).dt.strftime('%Y-%m-%d')
                    combined = combined.drop_duplicates(subset=['Date']).sort_values('Date')
                    combined.to_csv(file_path, index=False)
                except: continue
        except: continue
    print(f"--- Sync Complete ---")

if __name__ == "__main__":
    sync_all()
