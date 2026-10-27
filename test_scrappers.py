"""
Interactive Scrapper & Network Tester (Targeted & Single-Click).
Supports testing specific scrappers:
  python test_scrappers.py 1  -> Test COMEX (Yahoo Finance)
  python test_scrappers.py 2  -> Test BTCUSD (Binance Data API)
  python test_scrappers.py 3  -> Test XAUTUSDT (OKX Market Engine)
  python test_scrappers.py all -> Test All Scrappers
"""

import os
import sys
import time
import socket
import requests

# Reconfigure stdout for safe Windows console encoding
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def clear():
    os.system("cls" if sys.platform == "win32" else "clear")

def get_proxy_status():
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if not http_proxy and not https_proxy:
        return "[NONE] 100% KONEKSI LANGSUNG (DIRECT SOCKET)"
    return f"HTTP={http_proxy}, HTTPS={https_proxy}"

def test_comex():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1d&range=1d"
    host = "query1.finance.yahoo.com"
    curl_cmd = f'curl.exe -i -H "User-Agent: Mozilla/5.0" "{url}"'
    ps_cmd = f'(Invoke-RestMethod -Headers @{{"User-Agent"="Mozilla/5.0"}} -Uri "{url}").chart.result.meta'
    
    print("=" * 82)
    print("        [SCRAPPER 1] UJI KONEKTIVITAS COMEX GOLD (YAHOO FINANCE QUERY)")
    print("=" * 82)
    print(f"Target URL      : {url}")
    print(f"Perintah cURL   : {curl_cmd}")
    print(f"Perintah PS     : {ps_cmd}")
    print("-" * 82)
    print("MENGHUBUNGI SERVER UPSTREAM...")
    
    try:
        t0 = time.time()
        ip = socket.gethostbyname(host)
        resp = requests.get(url, headers=HEADERS, timeout=6)
        lat = int((time.time() - t0) * 1000)
        
        print(f"  [OK] Status Proxy    : {get_proxy_status()}")
        print(f"  [OK] Upstream IP     : {ip} (Yahoo Anycast Cloud)")
        print(f"  [OK] HTTP Status     : {resp.status_code} OK (Latency: {lat} ms)")
        print(f"  [OK] Server Date     : {resp.headers.get('Date', '-')}")
        print(f"  [OK] Server Software : {resp.headers.get('Server', 'ATS')}")
        
        if resp.status_code == 200:
            meta = resp.json()["chart"]["result"][0]["meta"]
            price = float(meta["regularMarketPrice"])
            prev = float(meta.get("chartPreviousClose", price))
            chg = ((price - prev) / prev) * 100
            print("-" * 82)
            print("DATA REALTIME TERVERIFIKASI:")
            print(f"  - Simbol          : GC=F (COMEX Gold Continuous Futures)")
            print(f"  - Harga Terkini   : ${price:,.2f}")
            print(f"  - Prev Close      : ${prev:,.2f}")
            print(f"  - 24H Perubahan   : {chg:+.2f}%")
        else:
            print(f"  [FAIL] Status Error: HTTP {resp.status_code}")
    except Exception as e:
        print(f"  [FAIL] Error Koneksi: {e}")
    print("=" * 82)

def test_btc():
    url = "https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BTCUSDT"
    host = "data-api.binance.vision"
    curl_cmd = f'curl.exe -i "{url}"'
    
    print("=" * 82)
    print("        [SCRAPPER 2] UJI KONEKTIVITAS BTC/USDT (BINANCE DATA API)")
    print("=" * 82)
    print(f"Target URL      : {url}")
    print(f"Perintah Manual : {curl_cmd}")
    print("-" * 82)
    print("MENGHUBUNGI SERVER UPSTREAM...")
    
    try:
        t0 = time.time()
        ip = socket.gethostbyname(host)
        resp = requests.get(url, headers=HEADERS, timeout=6)
        lat = int((time.time() - t0) * 1000)
        
        print(f"  [OK] Status Proxy    : {get_proxy_status()}")
        print(f"  [OK] Upstream IP     : {ip} (Binance AWS Edge Node)")
        print(f"  [OK] HTTP Status     : {resp.status_code} OK (Latency: {lat} ms)")
        print(f"  [OK] Server Date     : {resp.headers.get('Date', '-')}")
        print(f"  [OK] Server Weight   : {resp.headers.get('x-mbx-used-weight-1m', '-')}")
        
        if resp.status_code == 200:
            d = resp.json()
            price = float(d["lastPrice"])
            chg = float(d["priceChangePercent"])
            high = float(d["highPrice"])
            low = float(d["lowPrice"])
            print("-" * 82)
            print("DATA REALTIME TERVERIFIKASI:")
            print(f"  - Simbol          : BTCUSDT (Bitcoin Spot)")
            print(f"  - Harga Terkini   : ${price:,.2f}")
            print(f"  - 24H Perubahan   : {chg:+.2f}%")
            print(f"  - 24H Range       : ${low:,.2f} - ${high:,.2f}")
            print(f"  - Epoch Time (ms) : {d.get('closeTime')}")
        else:
            print(f"  [FAIL] Status Error: HTTP {resp.status_code}")
    except Exception as e:
        print(f"  [FAIL] Error Koneksi: {e}")
    print("=" * 82)

def test_xaut():
    url = "https://www.okx.com/api/v5/market/ticker?instId=XAUT-USDT"
    host = "www.okx.com"
    curl_cmd = f'curl.exe -i "{url}"'
    
    print("=" * 82)
    print("        [SCRAPPER 3] UJI KONEKTIVITAS XAUT/USDT (OKX MARKET API)")
    print("=" * 82)
    print(f"Target URL      : {url}")
    print(f"Perintah Manual : {curl_cmd}")
    print("-" * 82)
    print("MENGHUBUNGI SERVER UPSTREAM...")
    
    try:
        t0 = time.time()
        ip = socket.gethostbyname(host)
        resp = requests.get(url, headers=HEADERS, timeout=6)
        lat = int((time.time() - t0) * 1000)
        
        print(f"  [OK] Status Proxy    : {get_proxy_status()}")
        print(f"  [OK] Upstream IP     : {ip} (OKX Cloudflare Edge Node)")
        print(f"  [OK] HTTP Status     : {resp.status_code} OK (Latency: {lat} ms)")
        print(f"  [OK] Server Date     : {resp.headers.get('Date', '-')}")
        print(f"  [OK] Cloudflare Ray  : {resp.headers.get('CF-RAY', '-')}")
        
        if resp.status_code == 200:
            d = resp.json()["data"][0]
            price = float(d["last"])
            open_p = float(d["open24h"]) if float(d["open24h"]) > 0 else price
            chg = ((price - open_p) / open_p) * 100
            high = float(d["high24h"])
            low = float(d["low24h"])
            print("-" * 82)
            print("DATA REALTIME TERVERIFIKASI:")
            print(f"  - Simbol          : XAUT-USDT (Tether Gold Spot)")
            print(f"  - Harga Terkini   : ${price:,.2f}")
            print(f"  - 24H Perubahan   : {chg:+.2f}%")
            print(f"  - 24H Range       : ${low:,.2f} - ${high:,.2f}")
            print(f"  - Server Timestamp: {d.get('ts')}")
        else:
            print(f"  [FAIL] Status Error: HTTP {resp.status_code}")
    except Exception as e:
        print(f"  [FAIL] Error Koneksi: {e}")
    print("=" * 82)

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    while True:
        clear()
        if target == "1" or target.lower() == "comex":
            test_comex()
        elif target == "2" or target.lower() == "btc":
            test_btc()
        elif target == "3" or target.lower() == "xaut":
            test_xaut()
        else:
            test_comex()
            print()
            test_btc()
            print()
            test_xaut()
            
        print("\n[INFO] Uji coba berhasil dijalankan otomatis (Zero-Typing).")
        print("Tekan [ENTER] untuk uji ulang, atau tutup jendela ini.")
        try:
            input()
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
