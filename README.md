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

## 2. Spesifikasi 3 Mode Gamma Exposure (GEX)

Sistem menganalisis interaksi posisi dealer/market maker derivatif antar instrumen terkait:

$$\Gamma = \frac{\partial^2 V}{\partial S^2}, \quad GEX = \sum (\Gamma_{call} \times OI_{call}) - \sum (\Gamma_{put} \times OI_{put})$$

### A. Mode 1: XAUUSD (Spot Gold)
Menganalisis eksposur gamma dari 3 pilar:
1. **GEX pada COMEX Gold (`GC=F`)**:
   * Mengukur *anchor* institusional opsi emas berjangka CME.
   * Menentukan **Call Wall** (resistensi magnetik), **Put Wall** (lantai support dealer), dan **Gamma Flip** (titik transisi volatilitas tenang ke agresif).
2. **GEX pada BTCUSD**:
   * Mengukur *cross-asset liquidity spillover*.
   * Saat dealer opsi kripto mengalami *gamma squeeze* (short gamma), mendeteksi pergeseran likuiditas menuju emas fisik.
3. **GEX pada XAUTUSDT (Tether Gold)**:
   * Mengukur *basis spread* dan tekanan pasak (*peg elasticity*).
   * Menghitung potensi aliran arbitrase dealer antara token sintetis emas dan emas spot fisik.

### B. Mode 2: XAUTUSDT (Tether Gold)
1. **GEX pada BTCUSD**:
   * Mengukur rotasi portofolio pasar kripto (*Digital Gold vs Tether Gold*).
   * Memantau korelasi delta-gamma dealer kripto saat terjadi pergerakan ekstrem di pasar Bitcoin.

### C. Mode 3: BTCUSD (Bitcoin)
1. **GEX pada XAUTUSDT**:
   * Mengukur *safe-haven flight* di dalam ekosistem kripto saat BTC menembus level Gamma Flip negatif (Short Gamma).

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
>> MODE AKTIF: XAUUSD (HANYA MENAMPILKAN GEX XAUUSD)
SPOT MT5: 2,745.20 │ Bid: 2,745.10 │ Ask: 2,745.30 │ Spread: 0.20 │ Vol: 1.50
------------------------------------------------------------------------------------
1. GEX PADA COMEX GOLD (GC=F):
   • Basis vs Futures : +$0.10
   • Gamma Regime     : [+GEX POSITIVE] (Volatilitas diredam / Mean Reverting)
   • Gamma Flip Level : $2,735.00
   • Major Call Wall  : $2,760.00 (Resistensi Utama)
   • Major Put Wall   : $2,720.00 (Support Utama)

2. GEX PADA BTCUSD:
   • BTC Spot         : $80,595.00
   • Cross Gamma Bias : MODERATE SPILLOVER (Korelasi Likuiditas 0.31)
   • Shock Level      : $79,500.00

3. GEX PADA XAUTUSDT:
   • XAUT Spot        : $4,058.60
   • Basis Peg Spread : +$0.50 (Normal Peg)
   • Arbitrage Risk   : LOW (Peg Stabil)
====================================================================================
```

#### Tampilan Mode 2: BTCUSD (Aktif)
```text
====================================================================================
 [   XAUUSD   ]                 [ ■ BTCUSD ]                 [   XAUTUSDT   ]
====================================================================================
>> MODE AKTIF: BTCUSD (HANYA MENAMPILKAN GEX BTCUSD)
SPOT BTC/USDT: $80,595.00 │ 24H: +0.39% ▲ │ 24H High: $81,200 │ 24H Low: $79,800
------------------------------------------------------------------------------------
1. GEX PADA XAUTUSDT (GOLD TOKEN SENSITIVITY):
   • XAUT Spot Price  : $4,058.60
   • Relative Ratio   : 19.85 XAUT per 1 BTC
   • Cross Gamma Flow : NEUTRAL
   • Hedging Trigger  : Jika BTC < $79,500 (Potensi rotasi safe-haven ke Gold Token)
   • Dealer Bias      : Balanced Hedging
====================================================================================
```

#### Tampilan Mode 3: XAUTUSDT (Aktif)
```text
====================================================================================
 [   XAUUSD   ]                 [   BTCUSD   ]                 [ ■ XAUTUSDT ]
====================================================================================
>> MODE AKTIF: XAUTUSDT (HANYA MENAMPILKAN GEX XAUTUSDT)
SPOT XAUT/USDT: $4,058.60 │ 24H: +0.88% ▲ │ Source: OKX Direct Node
------------------------------------------------------------------------------------
1. GEX PADA BTCUSD (CRYPTO PORTFOLIO ROTATION):
   • BTC Spot Price   : $80,595.00
   • BTC Volatility   : EXPANDING (Gamma Risk di BTC mempengaruhi selera risiko XAUT)
   • Peg Correlation  : 0.42
   • Rotational Bias  : BULLISH GOLD DEFENSE
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
