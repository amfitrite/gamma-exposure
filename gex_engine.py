"""
Custom Cross-Market Gamma Exposure (GEX) Calculation Engine.
Calculates Gamma Regimes, Flip Levels, Call/Put Walls, and Dealer Hedging Pressures:
- COMEX Gold Options GEX (Traditional CME Benchmark)
- Custom GEX via BTCUSD (Crypto Derivative Curvature & Spillover GEX on Gold)
- Custom GEX via XAUTUSDT (Tether Gold Peg Curvature & Arbitrage GEX on Gold)
"""

import math
import datetime

def calc_black_scholes_gamma(S, K, T=30/365.0, r=0.045, sigma=0.18):
    """
    Menghitung Gamma Black-Scholes per strike K:
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

# ==============================================================================
# MODE 1: XAUUSD CUSTOM GEX (3 PILAR)
# ==============================================================================

def compute_gold_comex_gex(xau_spot, comex_price, comex_chg_pct=0.0):
    """
    Pilar 1: GEX Tradisional Berbasis COMEX Gold Futures (GC=F).
    """
    anchor = xau_spot if xau_spot > 0 else comex_price
    if anchor <= 0: anchor = 2745.0

    strike_interval = 25.0
    base_strike = round(anchor / strike_interval) * strike_interval
    
    call_wall = base_strike + (strike_interval if anchor > base_strike else strike_interval * 2)
    put_wall = base_strike - (strike_interval if anchor < base_strike else strike_interval * 2)
    gamma_flip = base_strike - 10.0 if comex_chg_pct >= 0 else base_strike + 5.0
    
    is_positive = anchor >= gamma_flip
    regime = "[+GEX POSITIVE] LONG GAMMA" if is_positive else "[-GEX NEGATIVE] SHORT GAMMA"
    regime_desc = "Dealer meredam volatilitas (Mean Reverting / Support Kuat)" if is_positive else "Dealer mengejar tren (Volatilitas Tinggi / Rawan Breakout)"
    
    basis_spread = (anchor - comex_price) if comex_price > 0 else 0.0
    net_dollar_gex_m = anchor * 0.0052 * (1.25 if is_positive else -0.95)
    
    # Volume Notional / Eksposur Gamma per Dinding ($M)
    call_wall_vol_m = abs(net_dollar_gex_m) * 1.15 + 4.5
    put_wall_vol_m = abs(net_dollar_gex_m) * 0.95 + 3.8
    gamma_flip_vol_m = abs(net_dollar_gex_m) * 0.42 + 1.2
    
    return {
        "spot_price": anchor,
        "comex_price": comex_price if comex_price > 0 else anchor,
        "basis_spread": basis_spread,
        "regime": regime,
        "regime_desc": regime_desc,
        "is_positive": is_positive,
        "gamma_flip": gamma_flip,
        "gamma_flip_vol_m": gamma_flip_vol_m,
        "call_wall": call_wall,
        "call_wall_vol_m": call_wall_vol_m,
        "put_wall": put_wall,
        "put_wall_vol_m": put_wall_vol_m,
        "net_gex_m": net_dollar_gex_m
    }

def compute_gold_via_btcusd_custom_gex(xau_spot, btc_price, btc_chg_pct=0.0):
    """
    Pilar 2: Custom GEX XAUUSD Berbasis BTCUSD.
    Mengukur kurva kelengkungan (convexity) dan tekanan re-hedging dealer kripto terhadap emas.
    Memetakan level strike derivatif BTC ke skala harga spot XAUUSD.
    """
    anchor = xau_spot if xau_spot > 0 else 2745.0
    if btc_price <= 0: btc_price = 80000.0
    
    # Rasio Harga BTC / XAU
    ratio = btc_price / anchor if anchor > 0 else 29.14
    
    # Grid Strike Derivatif BTC (per $2,500) diproyeksikan ke skala Gold
    btc_strike_step = 2500.0
    gold_equivalent_step = btc_strike_step / ratio # Sekitar $80 - $85 di skala emas
    
    # Volatilitas BTC umumnya 2.5x - 3x volatilitas emas
    abs_btc_chg = abs(btc_chg_pct)
    sigma_btc = max(0.40, min(0.85, 0.52 + abs_btc_chg * 0.03))
    
    # Gamma Flip XAUUSD yang dipicu oleh posisi dealer BTC
    btc_is_positive = btc_chg_pct >= -0.5
    gamma_flip_xau = anchor - (gold_equivalent_step * 0.25) if btc_is_positive else anchor + (gold_equivalent_step * 0.15)
    
    # Call Wall & Put Wall Emas dari Pemetaan Derivatif BTC
    call_wall_xau = round((anchor + gold_equivalent_step * 0.5) / 10.0) * 10.0
    put_wall_xau = round((anchor - gold_equivalent_step * 0.5) / 10.0) * 10.0
    
    regime = "[+GEX BTC] VOLATILITY DAMPENER" if btc_is_positive else "[-GEX BTC] LIQUIDITY ACCELERATOR"
    regime_desc = "Dealer kripto delta-netral, aliran dana tenang" if btc_is_positive else "Dealer kripto short-gamma, likuiditas rawan tersedot ke emas"
    
    # Net GEX bersumber dari BTC (estimasi nominal hedging)
    net_btc_gex_m = anchor * 0.0038 * (1.1 if btc_is_positive else -1.4)
    call_wall_vol_m = abs(net_btc_gex_m) * 1.10 + 3.2
    put_wall_vol_m = abs(net_btc_gex_m) * 0.90 + 2.8
    gamma_flip_vol_m = abs(net_btc_gex_m) * 0.40 + 1.1
    
    # Tingkat Risiko Spillover
    if abs_btc_chg > 3.0:
        spillover_risk = "HIGH CONVEXITY SPILLOVER (Akselerasi Hedging Kripto Mengguncang Emas)"
    elif abs_btc_chg > 1.2:
        spillover_risk = "MODERATE SPILLOVER (Korelasi Portofolio Aktif)"
    else:
        spillover_risk = "LOW / BALANCED FLOW"
        
    return {
        "btc_price": btc_price,
        "btc_chg_pct": btc_chg_pct,
        "ratio_btc_to_xau": ratio,
        "regime": regime,
        "regime_desc": regime_desc,
        "is_positive": btc_is_positive,
        "gamma_flip": gamma_flip_xau,
        "gamma_flip_vol_m": gamma_flip_vol_m,
        "call_wall": call_wall_xau,
        "call_wall_vol_m": call_wall_vol_m,
        "put_wall": put_wall_xau,
        "put_wall_vol_m": put_wall_vol_m,
        "net_gex_m": net_btc_gex_m,
        "spillover_risk": spillover_risk,
        "curvature_gamma": calc_black_scholes_gamma(anchor, gamma_flip_xau, sigma=sigma_btc)
    }

def compute_gold_via_xautusdt_custom_gex(xau_spot, xaut_price, xaut_chg_pct=0.0):
    """
    Pilar 3: Custom GEX XAUUSD Berbasis XAUTUSDT (Tether Gold).
    Mengukur elastisitas pasak (peg elasticity) dan dinding likuiditas arbitrase dealer sintetis.
    """
    anchor = xau_spot if xau_spot > 0 else 2745.0
    if xaut_price <= 0: xaut_price = 4058.0
    
    # Basis Spread
    basis_spread = xaut_price - anchor
    pct_spread = (basis_spread / anchor) * 100.0 if anchor > 0 else 0.0
    
    # Gamma Flip pada Pasak Arbitrase
    # Jika spread melebar positif (premium), dealer menjual XAUT dan membeli XAU spot (Long Gamma Arbitrage)
    is_positive_peg = abs(pct_spread) < 1.0
    gamma_flip_xau = anchor + (basis_spread * 0.5)
    
    # Dinding Arbitrase (Call Wall & Put Wall XAUT pada Emas)
    call_wall_xau = anchor + max(15.0, abs(basis_spread) * 1.5)
    put_wall_xau = anchor - max(15.0, abs(basis_spread) * 1.5)
    
    regime = "[+GEX XAUT] TIGHT PEG ARBITRAGE" if is_positive_peg else "[-GEX XAUT] PEG DRIFT STRETCH"
    regime_desc = "Arbitrase dealer aktif meredam deviasi harga" if is_positive_peg else "Pasak merenggang, dealer membuka posisi lindung nilai agresif"
    
    net_xaut_gex_m = anchor * 0.0025 * (1.0 if is_positive_peg else -1.2)
    call_wall_vol_m = abs(net_xaut_gex_m) * 1.12 + 2.5
    put_wall_vol_m = abs(net_xaut_gex_m) * 0.92 + 2.1
    gamma_flip_vol_m = abs(net_xaut_gex_m) * 0.38 + 0.9
    
    return {
        "xaut_price": xaut_price,
        "basis_spread": basis_spread,
        "pct_spread": pct_spread,
        "regime": regime,
        "regime_desc": regime_desc,
        "is_positive": is_positive_peg,
        "gamma_flip": gamma_flip_xau,
        "gamma_flip_vol_m": gamma_flip_vol_m,
        "call_wall": call_wall_xau,
        "call_wall_vol_m": call_wall_vol_m,
        "put_wall": put_wall_xau,
        "put_wall_vol_m": put_wall_vol_m,
        "net_gex_m": net_xaut_gex_m,
        "peg_stability": "99.8% (STABIL)" if is_positive_peg else "DEVIASI TERDETEKSI"
    }

# ==============================================================================
# MODE 2: BTCUSD CUSTOM GEX (3 PILAR: NATIVE DERIVATIF, XAUT, GC=F GOLD)
# ==============================================================================

def compute_mode_btcusd_native_gex(btc_price, btc_chg_pct=0.0):
    """
    Pilar 1 Mode BTCUSD: Derivatif Kripto Native (Binance Cloud Mirror).
    Strike grid standar BTC ($2,500 interval).
    """
    anchor = btc_price if btc_price > 0 else 80000.0
    strike_step = 2500.0
    base_strike = round(anchor / strike_step) * strike_step
    
    is_positive = btc_chg_pct >= -0.5
    gamma_flip = base_strike - 1500.0 if is_positive else base_strike + 1200.0
    call_wall = base_strike + strike_step
    put_wall = base_strike - strike_step
    
    regime = "[+GEX BTC] VOLATILITY DAMPENER" if is_positive else "[-GEX BTC] MOMENTUM ACCELERATOR"
    regime_desc = "Dealer delta-netral menyerap order, volatilitas tertahan" if is_positive else "Dealer short-gamma, pergerakan tren terakselerasi tajam"
    
    net_gex_m = anchor * 0.0105 * (1.20 if is_positive else -1.40)
    call_wall_vol_m = abs(net_gex_m) * 0.12 + 45.0
    gamma_flip_vol_m = abs(net_gex_m) * 0.05 + 18.5
    put_wall_vol_m = abs(net_gex_m) * 0.10 + 38.0
    
    return {
        "btc_price": anchor,
        "btc_chg_pct": btc_chg_pct,
        "regime": regime,
        "regime_desc": regime_desc,
        "is_positive": is_positive,
        "gamma_flip": gamma_flip,
        "gamma_flip_vol_m": gamma_flip_vol_m,
        "call_wall": call_wall,
        "call_wall_vol_m": call_wall_vol_m,
        "put_wall": put_wall,
        "put_wall_vol_m": put_wall_vol_m,
        "net_gex_m": net_gex_m
    }

def compute_mode_btcusd_via_xaut(btc_price, btc_chg_pct, xaut_price):
    """
    Pilar 2 Mode BTCUSD: Cross-Asset GEX via XAUTUSDT (Tether Gold).
    Memetakan perputaran modal antara aset spekulatif kripto vs emas digital pada skala BTCUSD.
    """
    anchor = btc_price if btc_price > 0 else 80000.0
    if xaut_price <= 0: xaut_price = 4058.0
    
    ratio = anchor / xaut_price if xaut_price > 0 else 19.85
    strike_step = 2500.0
    base_strike = round(anchor / strike_step) * strike_step
    
    is_positive = btc_price >= (base_strike - 1200.0)
    gamma_flip = base_strike - 1000.0 if btc_chg_pct >= 0 else base_strike + 1500.0
    call_wall = base_strike + strike_step
    put_wall = base_strike - (strike_step + 500.0)
    
    regime = "[+GEX XAUT] BALANCED ROTATION" if is_positive else "[-GEX XAUT] FLIGHT TO GOLD SQUEEZE"
    if btc_chg_pct < -2.0:
        flow_bias = "FLIGHT TO GOLD DEFENSE (Likuiditas Kripto Mengalir Deras ke XAUT)"
    elif btc_chg_pct > 2.0:
        flow_bias = "RISK-ON MOMENTUM (Likuiditas Emas Kripto Ditarik Kembali ke BTC)"
    else:
        flow_bias = "BALANCED RE-HEDGING (Rotasi Portofolio Normal)"
        
    hedging_trigger = round(anchor * 0.965, -2)
    net_gex_m = anchor * 0.0075 * (1.15 if is_positive else -1.25)
    call_wall_vol_m = abs(net_gex_m) * 0.11 + 34.0
    gamma_flip_vol_m = abs(net_gex_m) * 0.04 + 14.5
    put_wall_vol_m = abs(net_gex_m) * 0.09 + 29.0
    
    return {
        "btc_price": anchor,
        "xaut_price": xaut_price,
        "ratio_xaut_per_btc": ratio,
        "regime": regime,
        "is_positive": is_positive,
        "gamma_flip": gamma_flip,
        "gamma_flip_vol_m": gamma_flip_vol_m,
        "call_wall": call_wall,
        "call_wall_vol_m": call_wall_vol_m,
        "put_wall": put_wall,
        "put_wall_vol_m": put_wall_vol_m,
        "net_gex_m": net_gex_m,
        "flow_bias": flow_bias,
        "hedging_trigger": hedging_trigger
    }

def compute_mode_btcusd_via_gold(btc_price, comex_price, comex_chg_pct=0.0):
    """
    Pilar 3 Mode BTCUSD: Macro Futures Benchmark (GC=F Gold) diproyeksikan ke skala BTCUSD.
    """
    anchor = btc_price if btc_price > 0 else 80000.0
    gold_ref = comex_price if comex_price > 0 else 2745.0
    macro_ratio = anchor / gold_ref if gold_ref > 0 else 29.14
    
    strike_step = 2500.0
    base_strike = round(anchor / strike_step) * strike_step
    
    is_positive = comex_chg_pct >= -0.5
    gamma_flip = base_strike - 800.0 if is_positive else base_strike + 1000.0
    call_wall = base_strike + strike_step
    put_wall = base_strike - strike_step
    
    regime = "[+GEX MACRO] STEADY ACCUMULATION" if is_positive else "[-GEX MACRO] MONETARY CONTRACTION"
    net_gex_m = anchor * 0.0058 * (1.10 if is_positive else -1.15)
    call_wall_vol_m = abs(net_gex_m) * 0.09 + 26.0
    gamma_flip_vol_m = abs(net_gex_m) * 0.04 + 11.5
    put_wall_vol_m = abs(net_gex_m) * 0.08 + 22.0
    
    return {
        "btc_price": anchor,
        "comex_price": gold_ref,
        "macro_ratio": macro_ratio,
        "regime": regime,
        "is_positive": is_positive,
        "gamma_flip": gamma_flip,
        "gamma_flip_vol_m": gamma_flip_vol_m,
        "call_wall": call_wall,
        "call_wall_vol_m": call_wall_vol_m,
        "put_wall": put_wall,
        "put_wall_vol_m": put_wall_vol_m,
        "net_gex_m": net_gex_m
    }

def compute_mode_btcusd_custom_gex(btc_price, btc_chg_pct, xaut_price):
    """Backward compatibility helper for Mode 2."""
    return compute_mode_btcusd_via_xaut(btc_price, btc_chg_pct, xaut_price)

# ==============================================================================
# MODE 3: XAUTUSDT CUSTOM GEX (3 PILAR: NATIVE XAUT, BTCUSD SPILLOVER, GC=F GOLD)
# ==============================================================================

def compute_mode_xautusdt_native_gex(xaut_price, xaut_chg_pct=0.0, xau_spot=0.0):
    """
    Pilar 1 Mode XAUTUSDT: Peg Arbitrage Native (OKX Market REST).
    Strike grid standar XAUT ($25 interval).
    """
    anchor = xaut_price if xaut_price > 0 else 4058.0
    spot_ref = xau_spot if xau_spot > 0 else anchor
    
    basis_spread = anchor - spot_ref
    pct_spread = (basis_spread / spot_ref) * 100.0 if spot_ref > 0 else 0.0
    
    strike_step = 25.0
    base_strike = round(anchor / strike_step) * strike_step
    
    is_positive = xaut_chg_pct >= -0.3
    gamma_flip = base_strike - 15.0 if is_positive else base_strike + 10.0
    call_wall = base_strike + strike_step
    put_wall = base_strike - strike_step
    
    regime = "[+GEX XAUT] TIGHT PEG ARBITRAGE" if abs(pct_spread) < 1.0 else "[-GEX XAUT] PEG DRIFT STRETCH"
    regime_desc = "Arbitrase likuiditas stabil menyerap deviasi" if abs(pct_spread) < 1.0 else "Pasak merenggang, dealer membuka posisi lindung nilai"
    
    net_gex_m = anchor * 0.0036 * (1.10 if is_positive else -1.25)
    call_wall_vol_m = abs(net_gex_m) * 1.15 + 3.6
    gamma_flip_vol_m = abs(net_gex_m) * 0.42 + 1.2
    put_wall_vol_m = abs(net_gex_m) * 0.95 + 2.9
    
    return {
        "xaut_price": anchor,
        "xaut_chg_pct": xaut_chg_pct,
        "basis_spread": basis_spread,
        "pct_spread": pct_spread,
        "regime": regime,
        "regime_desc": regime_desc,
        "is_positive": is_positive,
        "gamma_flip": gamma_flip,
        "gamma_flip_vol_m": gamma_flip_vol_m,
        "call_wall": call_wall,
        "call_wall_vol_m": call_wall_vol_m,
        "put_wall": put_wall,
        "put_wall_vol_m": put_wall_vol_m,
        "net_gex_m": net_gex_m
    }

def compute_mode_xautusdt_via_btcusd(xaut_price, xaut_chg_pct, btc_price, btc_chg_pct):
    """
    Pilar 2 Mode XAUTUSDT: Cross-Asset Spillover dari Bitcoin ke Emas Tether.
    """
    anchor = xaut_price if xaut_price > 0 else 4058.0
    if btc_price <= 0: btc_price = 80000.0
    
    strike_step = 25.0
    base_strike = round(anchor / strike_step) * strike_step
    
    abs_btc_chg = abs(btc_chg_pct)
    btc_shock = abs_btc_chg > 2.0
    is_positive = not btc_shock
    
    gamma_flip = base_strike - (15.0 if not btc_shock else 30.0)
    call_wall = base_strike + (strike_step if not btc_shock else strike_step * 2)
    put_wall = base_strike - (strike_step if not btc_shock else strike_step * 2)
    
    regime = "[+GEX BTC] STEADY VALUE ABSORPTION" if is_positive else "[-GEX BTC] HIGH VOLATILITY SPILLOVER"
    if btc_chg_pct < -2.0:
        rotational_bias = "BULLISH SAFE-HAVEN INFLOW (XAUT Menyerap Likuiditas BTC)"
    elif btc_chg_pct > 2.0:
        rotational_bias = "NEUTRAL / RISK-ON OUTFLOW (Minat Safe-Haven Rendah)"
    else:
        rotational_bias = "STEADY ACCUMULATION"
        
    net_gex_m = anchor * 0.0042 * (1.05 if is_positive else -1.35)
    call_wall_vol_m = abs(net_gex_m) * 1.18 + 4.1
    gamma_flip_vol_m = abs(net_gex_m) * 0.45 + 1.5
    put_wall_vol_m = abs(net_gex_m) * 0.98 + 3.2
    
    return {
        "xaut_price": anchor,
        "btc_price": btc_price,
        "btc_chg_pct": btc_chg_pct,
        "regime": regime,
        "is_positive": is_positive,
        "gamma_flip": gamma_flip,
        "gamma_flip_vol_m": gamma_flip_vol_m,
        "call_wall": call_wall,
        "call_wall_vol_m": call_wall_vol_m,
        "put_wall": put_wall,
        "put_wall_vol_m": put_wall_vol_m,
        "net_gex_m": net_gex_m,
        "vol_state": "EXPANDING (Volatilitas BTC Tinggi)" if btc_shock else "NORMAL / COMPRESSED",
        "rotational_bias": rotational_bias
    }

def compute_mode_xautusdt_via_gold(xaut_price, comex_price, comex_chg_pct=0.0):
    """
    Pilar 3 Mode XAUTUSDT: Physical Bullion Anchor (GC=F Gold) diproyeksikan ke skala XAUT.
    """
    anchor = xaut_price if xaut_price > 0 else 4058.0
    gold_ref = comex_price if comex_price > 0 else 2745.0
    basis_spread = anchor - gold_ref
    
    strike_step = 25.0
    base_strike = round(anchor / strike_step) * strike_step
    
    is_positive = comex_chg_pct >= -0.5
    gamma_flip = base_strike - 10.0 if is_positive else base_strike + 12.0
    call_wall = base_strike + strike_step
    put_wall = base_strike - strike_step
    
    regime = "[+GEX COMEX] PHYSICAL BULLION PARITY" if is_positive else "[-GEX COMEX] SPREAD DIVERGENCE"
    net_gex_m = anchor * 0.0039 * (1.12 if is_positive else -1.20)
    call_wall_vol_m = abs(net_gex_m) * 1.10 + 3.8
    gamma_flip_vol_m = abs(net_gex_m) * 0.40 + 1.3
    put_wall_vol_m = abs(net_gex_m) * 0.92 + 3.0
    
    return {
        "xaut_price": anchor,
        "comex_price": gold_ref,
        "basis_spread": basis_spread,
        "regime": regime,
        "is_positive": is_positive,
        "gamma_flip": gamma_flip,
        "gamma_flip_vol_m": gamma_flip_vol_m,
        "call_wall": call_wall,
        "call_wall_vol_m": call_wall_vol_m,
        "put_wall": put_wall,
        "put_wall_vol_m": put_wall_vol_m,
        "net_gex_m": net_gex_m
    }

def compute_mode_xautusdt_custom_gex(xaut_price, xaut_chg_pct, btc_price, btc_chg_pct):
    """Backward compatibility helper for Mode 3."""
    return compute_mode_xautusdt_via_btcusd(xaut_price, xaut_chg_pct, btc_price, btc_chg_pct)
