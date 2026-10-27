# Gamma Exposure (GEX) & Direct Market Terminal

Sistem pengumpul data pasar terpadu (*real-time collector*) dan analisis eksposur gamma lintas pasar (*Cross-Market Gamma Exposure / GEX*) berbasis teks tanpa chart visual (*zero-chart overhead*).

---

## 1. Arsitektur Komponen Sistem

```
┌────────────────────────────────────────────────────────┐
│               MetaTrader 5 (MT5 Terminal)              │
│       Expert Advisor: "multi port bridge EA.mq5"       │
│               [Port 1: 5555 | Port 2: 5556]            │
└──────────────────────────┬─────────────────────────────┘
                           │ TCP Socket Stream (Port 5556)
                           ▼
┌────────────────────────────────────────────────────────┐
│         Python GEX & Market Engine (Localhost)         │
│  - TCP Listener Port 5556 (XAUUSD Live Ticks)          │
│  - Direct Crawler: COMEX (GC=F), BTCUSDT, XAUTUSDT     │
│  - Cross-Asset GEX Analytical Engine                   │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│           Pure Text-Based HUD / Terminal               │
│  - Pantauan Harga Live (XAUUSD, COMEX, BTC, XAUT)      │
│  - Matriks GEX 3 Mode Interaktif                       │
│  - Frameless, Zero Extra Windows, Ultra Low Latency    │
└────────────────────────────────────────────────────────┘
```

---

## 2. Konsep Custom Gamma Exposure (GEX)

Secara konvensional di pasar keuangan, Gamma Exposure untuk emas selalu dihitung menggunakan opsi berjangka CME (COMEX Gold Options). Namun sistem ini mengimplementasikan **Custom Gamma Exposure** yang menggabungkan:
1. **Benchmark Tradisional**: GEX berbasis COMEX Gold Options.
2. **Custom GEX Berbasis BTCUSD**: Menggunakan kurva kelengkungan (*derivative curvature*) dan pemetaan strike BTCUSD ke skala emas untuk mendeteksi akselerasi *re-hedging* dealer kripto.
3. **Custom GEX Berbasis XAUTUSDT**: Menggunakan elastisitas pasak (*peg curvature*) dan kolam arbitrase Tether Gold untuk mengukur dinding likuiditas dan tekanan deviasi pasak.

---

### A. Mode 1: XAUUSD (Spot Gold)
Menganalisis eksposur gamma dari 3 pilar:
1. **GEX pada COMEX Gold (`GC=F`) [Benchmark Tradisional]**:
   * Menentukan **Call Wall** (resistensi magnetik), **Put Wall** (lantai support dealer), dan **Gamma Flip** CME.
   * Net Dollar GEX ($M per 1% move).
2. **Custom GEX pada BTCUSD [Crypto Derivative Curvature]**:
   * Menghitung **BTC-Induced Gamma Flip** pada skala harga emas.
   * Menentukan **Call/Put Walls pada Emas** yang terinduksi oleh posisi dealer derivatif Bitcoin.
   * Mengukur risiko *convexity spillover* dan aliran *hedging*.
3. **Custom GEX pada XAUTUSDT [Tether Gold Peg Curvature]**:
   * Mengukur *basis peg spread* dan stabilitas pasak.
   * Menghitung **Peg Gamma Flip Level** dan dinding arbitrase dealer (*Arbitrage Call/Put Walls*).

### B. Mode 2: BTCUSD (Bitcoin)
1. **Custom GEX pada XAUTUSDT [Gold Token Hedging on BTC]**:
   * Menghitung rasio nilai tukar XAUT per BTC.
   * Menentukan **Gamma Flip BTC** dan **Call/Put Walls** yang terinduksi oleh rotasi emas sintetis.
   * Mendeteksi level pemicu *Flight to Gold Defense*.

### C. Mode 3: XAUTUSDT (Tether Gold)
1. **Custom GEX pada BTCUSD [Bitcoin Derivative Spillover on XAUT]**:
   * Menghitung **Gamma Flip XAUT** dan **Call/Put Walls** yang terinduksi oleh guncangan volatilitas Bitcoin.
   * Mendeteksi bias rotasi modal (*Bullish Safe-Haven Inflow* vs *Steady Accumulation*).

### D. Tampilan Eksklusif Berdasarkan Mode (Zero Cross-Clutter)
Layar hanya menampilkan data GEX yang relevan dengan **mode yang sedang aktif**:
* **Jika Mode `XAUUSD` Aktif**: 
  * Layar **hanya menampilkan GEX untuk XAUUSD** (GEX pada COMEX, GEX pada BTCUSD, dan GEX pada XAUTUSDT). Data mode BTCUSD & XAUTUSDT disembunyikan total.
* **Jika Mode `BTCUSD` Aktif**: 
  * Layar **hanya menampilkan GEX untuk BTCUSD** (GEX pada XAUTUSDT). Data XAUUSD disembunyikan.
* **Jika Mode `XAUTUSDT` Aktif**: 
  * Layar **hanya menampilkan GEX untuk XAUTUSDT** (GEX pada BTCUSD). Data XAUUSD disembunyikan.

Satu-satunya elemen kontrol pada layar adalah **tombol pemilih 3 mode**: `[ XAUUSD ]`, `[ BTCUSD ]`, dan `[ XAUTUSDT ]`.

### E. Visual Mockup Tampilan 3 Mode

#### Tampilan Mode 1: XAUUSD (Aktif)
```text
====================================================================================
 [ ■ XAUUSD ]                 [   BTCUSD   ]                 [   XAUTUSDT   ]
====================================================================================
>> MODE: XAUUSD (SPOT GOLD)
Spot: $4,076.80 │ Bid: $4,076.65 │ Ask: $4,076.95 │ Spread: $0.30 │ Vol: 1.00
------------------------------------------------------------------------------------
1. COMEX (Futures: $4,076.80)  [* ONLINE] [KLIK TEST CMD] >>
   • Basis vs Futures : +$0.00 │ Regime: [+GEX POSITIVE] LONG GAMMA
   • Call Wall        : $4,100.00 (Vol: $28.40M)
   • Gamma Flip Level : $4,065.00 (Vol: $9.60M)
   • Put Wall         : $4,025.00 (Vol: $24.80M)
   • Net Dollar GEX   : +$26.50M per 1% move

2. BTCUSD (Spot: $80,691.85)   [* ONLINE] [KLIK TEST CMD] >>
   • 24H Change       : +0.56% │ Rasio: 19.79x │ Regime: [+GEX BTC] VOLATILITY DAMPENER
   • Call Wall        : $4,140.00 (Vol: $18.50M)
   • Gamma Flip Level : $4,045.22 (Vol: $8.20M)
   • Put Wall         : $4,010.00 (Vol: $15.80M)
   • Net Dollar GEX   : +$17.04M per 1% move

3. XAUTUSDT (Spot: $4,062.60)  [* ONLINE] [KLIK TEST CMD] >>
   • Spread vs Spot   : $-14.20 (-0.35%) │ Regime: [+GEX XAUT] TIGHT PEG
   • Call Wall        : $4,098.10 (Vol: $12.80M)
   • Gamma Flip Level : $4,069.70 (Vol: $6.40M)
   • Put Wall         : $4,055.50 (Vol: $11.20M)
   • Net Dollar GEX   : +$10.19M per 1% move

──────────────────────────────────────────────────────────────────────────────────
[RISET PERBANDINGAN WALLS & FLIP - SKALA XAUUSD]
INSTRUMEN     │ CALL WALL (VOL)       │ GAMMA FLIP (VOL)      │ PUT WALL (VOL)
──────────────┼───────────────────────┼───────────────────────┼───────────────────
1. COMEX      │ $4,100.00 ($28.40M)   │ $4,065.00 ($9.60M)    │ $4,025.00 ($24.80M)
2. BTCUSD     │ $4,140.00 ($18.50M)   │ $4,045.22 ($8.20M)    │ $4,010.00 ($15.80M)
3. XAUTUSDT   │ $4,098.10 ($12.80M)   │ $4,069.70 ($6.40M)    │ $4,055.50 ($11.20M)
====================================================================================
TEST SCRAPPER:  [1. COMEX]   [2. BTCUSD]   [3. XAUTUSDT]
```

#### Tampilan Mode 2: BTCUSD (Aktif)
```text
====================================================================================
 [   XAUUSD   ]                 [ ■ BTCUSD ]                 [   XAUTUSDT   ]
====================================================================================
>> MODE: BTCUSD
Spot: $80,691.85 │ 24H: +0.56% ▲
------------------------------------------------------------------------------------
1. XAUTUSDT
   • XAUT Spot Price  : $4,062.60 │ Rasio: 19.79 XAUT/BTC
   • Gamma Regime     : [+GEX] BALANCED ROTATION
   • BTC Gamma Flip   : $78,500.00
   • Major Walls BTC  : Call: $82,500.00 │ Put: $77,500.00
   • Net Dollar GEX   : +$18.20M per 1% move
   • Capital Rotation : BALANCED RE-HEDGING
   • Hedging Trigger  : Jika BTC < $77,800.00
====================================================================================
```

#### Tampilan Mode 3: XAUTUSDT (Aktif)
```text
====================================================================================
 [   XAUUSD   ]                 [   BTCUSD   ]                 [ ■ XAUTUSDT ]
====================================================================================
>> MODE: XAUTUSDT
Spot: $4,062.60 │ 24H: +0.88% ▲
------------------------------------------------------------------------------------
1. BTCUSD
   • BTC Spot Price   : $80,691.85 (+0.56%)
   • Gamma Regime     : [+GEX] STEADY VALUE ABSORPTION
   • XAUT Gamma Flip  : $4,050.00
   • Major Walls XAUT : Call: $4,090.00 │ Put: $4,040.00
   • Net Dollar GEX   : +$12.50M per 1% move
   • Volatility State : NORMAL / COMPRESSED
   • Rotational Bias  : STEADY ACCUMULATION
====================================================================================
```

---

## 3. Komponen Multi-Port Bridge EA (`multi port bridge EA.mq5`)

EA MQL5 kustom yang mampu menyiarkan tick order flow ke hingga 5 port TCP secara paralel:
* **Port 1 (5555)**: Port default untuk streaming umum / Terminal TickMap eksternal.
* **Port 2 (5556)**: Dedicated Port untuk GEX Engine (XAUUSD Tick Stream).
* **Port 3 - 5 (5557 - 5559)**: Port cadangan tambahan.
* **Karakteristik**:
  * *Fault-tolerant*: Jika salah satu port terputus, port lain tetap berjalan tanpa gangguan.
  * *Non-blocking*: Timeout koneksi 300 ms (mencegah chart MT5 membeku).
  * *Integrated Chart HUD*: Menampilkan status aktif setiap port secara visual di chart MT5.

---

## 4. File dalam Repository

| File | Keterangan |
| :--- | :--- |
| `collector.py` | Engine pengambil data live HTTPS direct socket (Binance, OKX, Yahoo Finance) dengan verifikasi audit anti-proxy dan anti-mock. |
| `market_hud.py` | Terminal HUD frameless teks murni untuk pemantauan harga live. |
| `market_hud.pyw` | Launcher windowless Windows (tanpa jendela konsol hitam CMD). |
| `multi_port_bridge_EA.mq5` | Expert Advisor MT5 pengirim tick ke multi-port (5555+). |
| `start_hud.bat` | Skrip batch sekali-klik untuk meluncurkan HUD. |
| `README.md` | Dokumentasi arsitektur dan spesifikasi sistem. |

---

## 5. Cara Menjalankan

### Menjalankan Market HUD Saat Ini:
```powershell
# Jalankan GUI teks frameless
pythonw market_hud.pyw

# Atau uji crawler mandiri di konsol
python collector.py
```

### Navigasi & Pintasan Keyboard:
* **Klik & Drag**: Memindahkan posisi jendela di layar monitor.
* **ESC** atau **Q**: Keluar dari aplikasi.
* **SPASI** atau **R**: Refresh data instan secara manual.
