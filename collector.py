"""
Core Market Data Collector & Network Auditor.
Direct connection to upstream public mirror & financial query endpoints.
Primary: Binance Vision (AWS Mirror), OKX REST Gateway, Yahoo Finance (GC=F Front-Month).
No local proxy, verified server timestamps & remote IP DNS resolution.
"""

import os
import time
import socket
import datetime
import concurrent.futures
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def audit_system_network():
    """Periksa apakah ada proxy sistem yang aktif."""
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    all_proxy = os.environ.get('ALL_PROXY') or os.environ.get('all_proxy')
    
    is_direct = not (http_proxy or https_proxy or all_proxy)
    return {
        "is_direct": is_direct,
        "http_proxy": http_proxy or "NONE (Direct)",
        "https_proxy": https_proxy or "NONE (Direct)",
        "all_proxy": all_proxy or "NONE (Direct)"
    }

def fetch_btc():
    """Tarik data BTC/USDT live dari Binance Vision (AWS Public Mirror cluster) dengan failover ke OKX."""
    t0 = time.time()
    url = "https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BTCUSDT"
    host = "data-api.binance.vision"
    
    try:
        remote_ip = socket.gethostbyname(host)
        resp = requests.get(url, headers=HEADERS, timeout=4)
        lat = int((time.time() - t0) * 1000)
        
        if resp.status_code == 200:
            d = resp.json()
            last_price = float(d["lastPrice"])
            chg_pct = float(d["priceChangePercent"])
            high_price = float(d.get("highPrice", 0))
            low_price = float(d.get("lowPrice", 0))
            server_ts = int(d.get("closeTime", int(time.time() * 1000)))
            
            return {
                "symbol": "BTC/USDT",
                "label": "Bitcoin Spot",
                "price": last_price,
                "change_pct": chg_pct,
                "high": high_price,
                "low": low_price,
                "server_time_ms": server_ts,
                "remote_ip": remote_ip,
                "latency_ms": lat,
                "source": "Binance Data API",
                "status": 200
            }
    except Exception as e:
        # Fallback to OKX
        try:
            url_okx = "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT"
            remote_ip = socket.gethostbyname("www.okx.com")
            resp = requests.get(url_okx, headers=HEADERS, timeout=4)
            lat = int((time.time() - t0) * 1000)
            d = resp.json()["data"][0]
            last = float(d["last"])
            open_p = float(d["open24h"]) if float(d["open24h"]) > 0 else last
            chg = ((last - open_p) / open_p) * 100
            return {
                "symbol": "BTC/USDT",
                "label": "Bitcoin Spot",
                "price": last,
                "change_pct": chg,
                "high": float(d.get("high24h", 0)),
                "low": float(d.get("low24h", 0)),
                "server_time_ms": int(d.get("ts", time.time() * 1000)),
                "remote_ip": remote_ip,
                "latency_ms": lat,
                "source": "OKX Market API",
                "status": 200
            }
        except Exception as e2:
            return {"symbol": "BTC/USDT", "error": str(e2), "status": 500}

def fetch_xaut():
    """Tarik data XAUT/USDT (Tether Gold) live langsung dari OKX."""
    t0 = time.time()
    url = "https://www.okx.com/api/v5/market/ticker?instId=XAUT-USDT"
    host = "www.okx.com"
    
    try:
        remote_ip = socket.gethostbyname(host)
        resp = requests.get(url, headers=HEADERS, timeout=4)
        lat = int((time.time() - t0) * 1000)
        
        if resp.status_code == 200:
            d = resp.json()["data"][0]
            last_price = float(d["last"])
            open_price = float(d["open24h"]) if float(d["open24h"]) > 0 else last_price
            chg_pct = ((last_price - open_price) / open_price) * 100
            high_price = float(d.get("high24h", 0))
            low_price = float(d.get("low24h", 0))
            server_ts = int(d.get("ts", int(time.time() * 1000)))
            
            return {
                "symbol": "XAUT/USDT",
                "label": "Tether Gold",
                "price": last_price,
                "change_pct": chg_pct,
                "high": high_price,
                "low": low_price,
                "server_time_ms": server_ts,
                "remote_ip": remote_ip,
                "latency_ms": lat,
                "source": "OKX Market API",
                "status": 200
            }
    except Exception as e:
        return {"symbol": "XAUT/USDT", "error": str(e), "status": 500}

def fetch_gold_comex():
    """Tarik benchmark Gold Futures front-month (GC=F CME synthetic) dari Yahoo Finance Query Engine."""
    t0 = time.time()
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1d&range=1d"
    host = "query1.finance.yahoo.com"
    
    try:
        remote_ip = socket.gethostbyname(host)
        resp = requests.get(url, headers=HEADERS, timeout=4)
        lat = int((time.time() - t0) * 1000)
        
        if resp.status_code == 200:
            meta = resp.json()["chart"]["result"][0]["meta"]
            price = float(meta["regularMarketPrice"])
            prev_close = float(meta.get("chartPreviousClose", price))
            chg_pct = ((price - prev_close) / prev_close) * 100 if prev_close else 0.0
            high = float(meta.get("regularMarketDayHigh", price))
            low = float(meta.get("regularMarketDayLow", price))
            server_ts = int(meta.get("regularMarketTime", time.time())) * 1000
            
            return {
                "symbol": "GOLD COMEX",
                "label": "COMEX Gold (GC=F)",
                "price": price,
                "change_pct": chg_pct,
                "high": high,
                "low": low,
                "server_time_ms": server_ts,
                "remote_ip": remote_ip,
                "latency_ms": lat,
                "source": "Yahoo Query Engine",
                "status": 200
            }
    except Exception as e:
        return {"symbol": "GOLD COMEX", "error": str(e), "status": 500}

def fetch_usd_dxy():
    """Tarik data US Dollar Index (DX-Y.NYB) live dari Yahoo Finance Query Engine."""
    t0 = time.time()
    url = "https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB?interval=1d&range=1d"
    host = "query1.finance.yahoo.com"
    
    try:
        remote_ip = socket.gethostbyname(host)
        resp = requests.get(url, headers=HEADERS, timeout=4)
        lat = int((time.time() - t0) * 1000)
        
        if resp.status_code == 200:
            meta = resp.json()["chart"]["result"][0]["meta"]
            price = float(meta["regularMarketPrice"])
            prev_close = float(meta.get("chartPreviousClose", price))
            chg_pct = ((price - prev_close) / prev_close) * 100 if prev_close else 0.0
            high = float(meta.get("regularMarketDayHigh", price))
            low = float(meta.get("regularMarketDayLow", price))
            server_ts = int(meta.get("regularMarketTime", time.time())) * 1000
            
            return {
                "symbol": "USD (DXY)",
                "label": "US Dollar Index",
                "price": price,
                "change_pct": chg_pct,
                "high": high,
                "low": low,
                "server_time_ms": server_ts,
                "remote_ip": remote_ip,
                "latency_ms": lat,
                "source": "Yahoo Query Engine",
                "status": 200
            }
    except Exception as e:
        return {"symbol": "USD (DXY)", "error": str(e), "status": 500}

def fetch_all_market_data():
    """Tarik keempat aset secara paralel dan cepat (concurrent threads)."""
    t_start = time.time()
    net_audit = audit_system_network()
    
    tasks = {
        "btc": fetch_btc,
        "xaut": fetch_xaut,
        "gold": fetch_gold_comex,
        "usd": fetch_usd_dxy
    }
    
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_map = {executor.submit(fn): key for key, fn in tasks.items()}
        for future in concurrent.futures.as_completed(future_map):
            key = future_map[future]
            try:
                results[key] = future.result()
            except Exception as ex:
                results[key] = {"error": str(ex), "status": 500}
                
    total_time = int((time.time() - t_start) * 1000)
    
    return {
        "network_audit": net_audit,
        "total_latency_ms": total_time,
        "items": [
            results.get("btc"),
            results.get("xaut"),
            results.get("gold"),
            results.get("usd")
        ]
    }

if __name__ == "__main__":
    print("=" * 78)
    print("DIRECT MARKET DATA COLLECTOR - LIVE TEST (NO PROXY, NO MOCK)")
    print("=" * 78)
    data = fetch_all_market_data()
    print("System Network Audit:")
    print(f"  • Direct Gateway : {'[YES] Direct (No Proxy)' if data['network_audit']['is_direct'] else '[PROXY ACTIVE]'}")
    print(f"  • Total Parallel Time: {data['total_latency_ms']} ms\n")
    
    print(f"{'INSTRUMENT':<14} | {'PRICE':<14} | {'24H CHG':<10} | {'LATENCY':<8} | {'SERVER IP':<16} | {'STATUS'}")
    print("-" * 78)
    for item in data["items"]:
        if "error" in item:
            print(f"{item.get('symbol', 'UNKNOWN'):<14} | ERROR: {item['error']}")
        else:
            chg_str = f"{item['change_pct']:+.2f}%"
            price_str = f"${item['price']:,.2f}" if "DXY" not in item["symbol"] else f"{item['price']:.3f}"
            print(f"{item['symbol']:<14} | {price_str:<14} | {chg_str:<10} | {item['latency_ms']} ms   | {item['remote_ip']:<16} | HTTP {item['status']}")
    print("=" * 78)
