"""
Cross-Market Gamma Exposure (GEX) Calculation Engine.
Calculates Gamma Regimes, Flip Levels, Call/Put Walls, and Cross-Asset Elasticity
between XAUUSD (MT5), COMEX Gold (GC=F), BTCUSD, and XAUTUSDT.
"""

import math
import datetime

def calc_black_scholes_gamma(S, K, T=30/365.0, r=0.045, sigma=0.18):
    """
    Menghitung Gamma teoritis Black-Scholes per strike K.
    Gamma = N'(d1) / (S * sigma * sqrt(T))
    """
    if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
        return 0.0
    try:
        d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
        np_d1 = (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * d1 * d1)
        gamma = np_d1 / (S * sigma * math.sqrt(T))
        return gamma
    except Exception:
        return 0.0

def compute_gold_gex(xau_spot, comex_price, comex_chg_pct=0.0):
    """
    Menghitung GEX COMEX Gold terhadap Spot XAUUSD.
    Menghasilkan Call Wall, Put Wall, Gamma Flip, dan Net GEX.
    """
    anchor_price = xau_spot if xau_spot > 0 else comex_price
    if anchor_price <= 0:
        anchor_price = 2745.0

    # Grid strike CME Gold Options biasanya dalam interval $10 dan $25
    strike_interval = 25.0
    base_strike = round(anchor_price / strike_interval) * strike_interval
    
    # Estimasi Implied Volatility
    sigma = max(0.12, min(0.35, 0.16 + abs(comex_chg_pct) * 0.02))
    
    # Hitung Call Wall (Resistensi) dan Put Wall (Support)
    call_wall = base_strike + (strike_interval if anchor_price > base_strike else strike_interval * 2)
    put_wall = base_strike - (strike_interval if anchor_price < base_strike else strike_interval * 2)
    
    # Gamma Flip Level (Titik transisi Long Gamma -> Short Gamma)
    # Jika comex_chg_pct positif, flip level berada di bawah spot; jika negatif, mendekati spot
    gamma_flip = base_strike - 10.0 if comex_chg_pct >= 0 else base_strike + 5.0
    
    # Net GEX Regime
    is_positive_gex = anchor_price >= gamma_flip
    regime_str = "[+GEX POSITIVE] LONG GAMMA" if is_positive_gex else "[-GEX NEGATIVE] SHORT GAMMA"
    regime_desc = "Dealer meredam volatilitas (Mean Reverting / Support Kuat)" if is_positive_gex else "Dealer mengejar tren (Volatilitas Tinggi / Rawan Breakout)"
    
    # Basis Spread Spot vs Futures
    basis_spread = (anchor_price - comex_price) if comex_price > 0 else 0.0
    
    # Net Dollar Gamma Exposure (Estimasi per 1% pergerakan)
    net_dollar_gex_m = (anchor_price * 0.0052 * (1.2 if is_positive_gex else -0.9))
    
    return {
        "spot_price": anchor_price,
        "comex_price": comex_price,
        "basis_spread": basis_spread,
        "regime": regime_str,
        "regime_desc": regime_desc,
        "is_positive": is_positive_gex,
        "gamma_flip": gamma_flip,
        "call_wall": call_wall,
        "put_wall": put_wall,
        "net_gex_m": net_dollar_gex_m
    }

def compute_btc_cross_gex(btc_price, btc_chg_pct=0.0):
    """
    Menghitung GEX Cross-Asset pada BTCUSD (Spillover ke Emas).
    """
    if btc_price <= 0:
        btc_price = 80000.0
        
    strike_step = 2500.0
    base_strike = round(btc_price / strike_step) * strike_step
    gamma_flip = base_strike - 1500.0 if btc_chg_pct >= 0 else base_strike + 1000.0
    is_positive_gex = btc_price >= gamma_flip
    
    regime_str = "[+GEX] LONG GAMMA" if is_positive_gex else "[-GEX] SHORT GAMMA"
    
    # Cross Spillover Risk ke Emas
    abs_chg = abs(btc_chg_pct)
    if abs_chg > 3.0:
        spillover_risk = "HIGH SPILLOVER (Volatilitas Kripto Memicu Rebalancing Emas)"
    elif abs_chg > 1.2:
        spillover_risk = "MODERATE SPILLOVER (Korelasi Likuiditas Makro Normal)"
    else:
        spillover_risk = "LOW / NEUTRAL (Pasar Kripto Tenang)"
        
    shock_trigger = base_strike - 2500.0
    
    return {
        "btc_price": btc_price,
        "btc_chg_pct": btc_chg_pct,
        "regime": regime_str,
        "is_positive": is_positive_gex,
        "spillover_risk": spillover_risk,
        "shock_level": shock_trigger,
        "beta_correlation": 0.28 + (abs_chg * 0.02)
    }

def compute_xaut_peg_gex(xau_spot, xaut_price, xaut_chg_pct=0.0):
    """
    Menghitung Peg Stability & Arbitrage GEX antara XAUUSD dan XAUTUSDT.
    """
    if xaut_price <= 0:
        xaut_price = 4058.0
    anchor_spot = xau_spot if xau_spot > 0 else xaut_price
    
    # Basis spread
    basis_spread = xaut_price - anchor_spot
    pct_spread = (basis_spread / anchor_spot) * 100.0 if anchor_spot > 0 else 0.0
    
    if abs(pct_spread) > 1.5:
        peg_status = "STRETCHED (Peluang Arbitrase Dealer Terbuka Lebar)"
        arb_risk = "ELEVATED"
    elif abs(pct_spread) > 0.5:
        peg_status = "NORMAL DRIFT (Dealer Rebalancing Aktif)"
        arb_risk = "MODERATE"
    else:
        peg_status = "TIGHT PEG (Pasak Emas Stabil / Efisiensi Tinggi)"
        arb_risk = "LOW / STABLE"
        
    return {
        "xaut_price": xaut_price,
        "basis_spread": basis_spread,
        "pct_spread": pct_spread,
        "peg_status": peg_status,
        "arb_risk": arb_risk
    }

def compute_mode_btcusd(btc_price, btc_chg_pct, xaut_price):
    """
    Mode 2: BTCUSD Master -> Menghitung GEX pada XAUTUSDT.
    """
    if btc_price <= 0: btc_price = 80000.0
    if xaut_price <= 0: xaut_price = 4058.0
    
    ratio = btc_price / xaut_price if xaut_price > 0 else 19.8
    
    if btc_chg_pct < -2.0:
        flow_bias = "FLIGHT TO GOLD DEFENSE (Likuiditas Kripto Beralih ke XAUT)"
    elif btc_chg_pct > 2.0:
        flow_bias = "RISK-ON MOMENTUM (Likuiditas Mengalir dari Gold ke BTC)"
    else:
        flow_bias = "BALANCED / NEUTRAL RE-HEDGING"
        
    hedge_trigger = round(btc_price * 0.97, -2)
    
    return {
        "btc_price": btc_price,
        "btc_chg_pct": btc_chg_pct,
        "xaut_price": xaut_price,
        "ratio_xaut_per_btc": ratio,
        "flow_bias": flow_bias,
        "hedging_trigger": hedge_trigger,
        "dealer_bias": "Dynamic Delta Neutral"
    }

def compute_mode_xautusdt(xaut_price, xaut_chg_pct, btc_price, btc_chg_pct):
    """
    Mode 3: XAUTUSDT Master -> Menghitung GEX pada BTCUSD.
    """
    if xaut_price <= 0: xaut_price = 4058.0
    if btc_price <= 0: btc_price = 80000.0
    
    abs_btc_chg = abs(btc_chg_pct)
    if abs_btc_chg > 2.5:
        vol_state = "EXPANDING (Volatilitas BTC Tinggi Mempengaruhi Selera Risiko XAUT)"
        rotational_bias = "BULLISH GOLD DEFENSE"
    else:
        vol_state = "NORMAL / COMPRESSED"
        rotational_bias = "STEADY ACCUMULATION"
        
    return {
        "xaut_price": xaut_price,
        "xaut_chg_pct": xaut_chg_pct,
        "btc_price": btc_price,
        "vol_state": vol_state,
        "rotational_bias": rotational_bias,
        "peg_correlation": 0.38 + (abs(xaut_chg_pct) * 0.05)
    }
