import requests

url = "https://www.twse.com.tw/fund/T86?response=json&date=20260515&selectType=ALL"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
r = requests.get(url, headers=headers)
print("Status Code:", r.status_code)
print("Response:", r.text[:500])
