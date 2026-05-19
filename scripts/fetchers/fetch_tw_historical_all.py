import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import time
import requests
import urllib3
from bs4 import BeautifulSoup

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
SAVE_DIR = os.path.expanduser("~/Documents/StockData_History")
os.makedirs(SAVE_DIR, exist_ok=True)

def get_tw_stock_list():
    """Fetches all TWSE/TPEx stock symbols from ISIN page."""
    print("Fetching stock list...")
    stocks = {}
    # Mode 2: Listed, Mode 4: OTC
    for mode in [2, 4]:
        url = f"https://isin.twse.com.tw/isin/C_public.jsp?strMode={mode}"
        try:
            response = requests.get(url, timeout=15, verify=False)
            response.encoding = 'big5'
            # Encoding is usually Big5/MS950
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'class': 'h4'})
            for row in table.find_all('tr')[1:]:
                tds = row.find_all('td')
                if len(tds) < 1: continue
                text = tds[0].text.strip()
                # Pattern: "Code Name" e.g., "2330 台積電"
                parts = text.split('\u3000') # Wide space
                if len(parts) == 2:
                    code, name = parts
                    if len(code) == 4 and code.isdigit():
                        suffix = ".TW" if mode == 2 else ".TWO"
                        stocks[code + suffix] = name
        except Exception as e:
            print(f"Error fetching list for mode {mode}: {e}")
    return stocks

def download_data():
    symbols_map = get_tw_stock_list()
    all_symbols = list(symbols_map.keys())
    print(f"Total symbols to download: {len(all_symbols)}")

    # Time range: past 15 months (approx 456 days + buffer)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=15*30 + 7)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    print(f"Downloading from {start_str} to {end_str}")

    # Process in chunks of 50 to avoid request overhead and handle progress
    chunk_size = 50
    total_downloaded = 0
    
    for i in range(0, len(all_symbols), chunk_size):
        chunk = all_symbols[i:i+chunk_size]
        print(f"Processing chunk {i//chunk_size + 1}: {chunk[0]} - {chunk[-1]}")
        
        try:
            # group_by='ticker' to get clear separation
            data = yf.download(chunk, start=start_str, end=end_str, group_by='ticker', threads=True)
            
            for ticker in chunk:
                try:
                    t_data = data[ticker].dropna() if len(chunk) > 1 else data.dropna()
                    if not t_data.empty:
                        # Add stock name to CSV metadata or filename
                        name = symbols_map.get(ticker, "").replace("/", "_")
                        file_path = os.path.join(SAVE_DIR, f"{ticker}_{name}.csv")
                        t_data.to_csv(file_path)
                        total_downloaded += 1
                except Exception as e:
                    pass # Ticker data might be missing in Yahoo
            
            # Sleep to avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            print(f"Error downloading chunk: {e}")

    print(f"Download complete. Total stocks saved: {total_downloaded}")
    print(f"Data location: {SAVE_DIR}")

if __name__ == "__main__":
    download_data()
