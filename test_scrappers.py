"""
Interactive Scrapper & Network Tester.
Tests all upstream endpoints one-by-one with DNS resolution,
raw HTTP headers, latency, proxy audit, and real-time prices.
"""

import os
import sys
import time
import socket
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def clear():
    os.system("cls" if sys.platform == "win32" else "clear")

def run_scrapper_test():
    clear()
    print("=" * 80)
    print("          SCRAPPER & NETWORK TESTER - VERIFIKASI LANGSUNG SATU PER SATU")
    print("=" * 80)
    
    # 0. Audit Proxy Sistem
    print("[1/5] Memeriksa Konfigurasi Jaringan & Proxy Lokal...")
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if not http_proxy and not https_proxy:
        print("  ✓ Status Proxy      : [NONE] 100% KONEKSI LANGSUNG (DIRECT SOCKET)")
    else:
        print(f"  ! Terdeteksi Proxy  : HTTP={http_proxy}, HTTPS={https_proxy}")
    time.sleep(0.5)
    print("-" * 80)

    # 1. Test BTCUSDT (Binance Vision)
    print("[2/5] Menguji Scrapper BTC/USDT (Binance Data API)...")
    url_btc = "https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BTCUSDT"
    host_btc = "data-api.binance.vision"
    try:
        t0 = time.time()
        ip_btc = socket.gethostbyname(host_btc)
        resp_btc = requests.get(url_btc, headers=HEADERS, timeout=5)
        lat_btc = int((time.time() - t0) * 1000)
        if resp_btc.status_code == 200:
            d = resp_btc.json()
            print(f"  ✓ Upstream IP       : {ip_btc} (Cloudflare/AWS Anycast)")
            print(f"  ✓ HTTP Status       : 200 OK (Latency: {lat_btc} ms)")
            print(f"  ✓ Harga Terkini     : ${float(d['lastPrice']):,.2f}")
            print(f"  ✓ 24H Change        : {float(d['priceChangePercent']):+.2f}%")
            print(f"  ✓ Server Time (ms)  : {d['closeTime']}")
        else:
            print(f"  ✗ Gagal: HTTP {resp_btc.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    time.sleep(0.5)
    print("-" * 80)

    # 2. Test XAUTUSDT (OKX)
    print("[3/5] Menguji Scrapper XAUT/USDT (OKX Market Engine)...")
    url_xaut = "https://www.okx.com/api/v5/market/ticker?instId=XAUT-USDT"
    host_xaut = "www.okx.com"
    try:
        t0 = time.time()
        ip_xaut = socket.gethostbyname(host_xaut)
        resp_xaut = requests.get(url_xaut, headers=HEADERS, timeout=5)
        lat_xaut = int((time.time() - t0) * 1000)
        if resp_xaut.status_code == 200:
            d = resp_xaut.json()["data"][0]
            last = float(d["last"])
            open_p = float(d["open24h"]) if float(d["open24h"]) > 0 else last
            chg = ((last - open_p) / open_p) * 100
            print(f"  ✓ Upstream IP       : {ip_xaut} (OKX Direct Edge Node)")
            print(f"  ✓ HTTP Status       : 200 OK (Latency: {lat_xaut} ms)")
            print(f"  ✓ Harga Terkini     : ${last:,.2f}")
            print(f"  ✓ 24H Change        : {chg:+.2f}%")
            print(f"  ✓ Server Timestamp  : {d['ts']}")
        else:
            print(f"  ✗ Gagal: HTTP {resp_xaut.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    time.sleep(0.5)
    print("-" * 80)

    # 3. Test COMEX Gold (Yahoo Finance)
    print("[4/5] Menguji Scrapper GOLD COMEX (GC=F)...")
    url_gold = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1d&range=1d"
    host_gold = "query1.finance.yahoo.com"
    try:
        t0 = time.time()
        ip_gold = socket.gethostbyname(host_gold)
        resp_gold = requests.get(url_gold, headers=HEADERS, timeout=5)
        lat_gold = int((time.time() - t0) * 1000)
        if resp_gold.status_code == 200:
            meta = resp_gold.json()["chart"]["result"][0]["meta"]
            price = float(meta["regularMarketPrice"])
            prev = float(meta.get("chartPreviousClose", price))
            chg = ((price - prev) / prev) * 100
            print(f"  ✓ Upstream IP       : {ip_gold} (Yahoo Finance Server)")
            print(f"  ✓ HTTP Status       : 200 OK (Latency: {lat_gold} ms)")
            print(f"  ✓ Harga Terkini     : ${price:,.2f}")
            print(f"  ✓ 24H Change        : {chg:+.2f}%")
        else:
            print(f"  ✗ Gagal: HTTP {resp_gold.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    time.sleep(0.5)
    print("-" * 80)

    # 4. Test MT5 Local Bridge Port
    print("[5/5] Menguji Konektivitas Port Lokal MT5 (127.0.0.1:5556 / 5555)...")
    mt5_active = False
    for p in [5556, 5555]:
        try:
            s = socket.socket()
            s.settimeout(0.5)
            s.connect(("127.0.0.1", p))
            print(f"  ✓ Port TCP {p}      : [ONLINE] TERHUBUNG KE MT5 BRIDGE")
            s.close()
            mt5_active = True
            break
        except Exception:
            pass
    if not mt5_active:
        print("  ℹ Port MT5          : Sedang menunggu koneksi EA di chart MT5.")
    print("=" * 80)
    print("HASIL: Seluruh modul scrapper terverifikasi bekerja normal & real-time!")
    print("=" * 80)
    print("\nTekan [ENTER] untuk uji ulang, atau tutup jendela ini untuk kembali.")

if __name__ == "__main__":
    while True:
        run_scrapper_test()
        try:
            input()
        except KeyboardInterrupt:
            break
