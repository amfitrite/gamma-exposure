# Direct Market HUD & Live Collector

Aplikasi pengumpul data harga pasar realtime (*crawler/collector*) untuk 4 instrumen:
1. **BTC/USDT** (Binance Public Data API)
2. **XAUT/USDT** (OKX Market Engine)
3. **GOLD COMEX** (Yahoo Finance GC=F Continuous Futures)
4. **USD DXY** (Yahoo Finance DX-Y.NYB US Dollar Index)

---

## Fitur Utama

- **Zero-Proxy & Zero-Mock**: Data ditarik langsung ke server resmi bursa via koneksi HTTPS langsung (Direct Socket Port 443).
- **Audit Transparansi Terintegrasi**: Menampilkan IP server upstream, status proxy lokal, latency bolak-balik (ms), dan timestamp bursa resmi.
- **Frameless Text-Based GUI**:
  - Tanpa OS Title Bar (borderless floating HUD).
  - Tanpa panel konsol hitam CMD saat peluncuran (`pythonw`).
  - Font Monospace (Consolas) bergaya terminal finansial.
  - Warna kontras tinggi (Hijau untuk kenaikan, Merah untuk penurunan).
  - Dapat digeser (*drag & drop*) ke mana saja di layar.

---

## Cara Menjalankan

### Cara 1: Sekali Klik (Rekomendasi)
Klik ganda file:
`start_hud.bat` atau `market_hud.pyw`

### Cara 2: Dari Terminal / PowerShell
```powershell
# Jalankan GUI tanpa console window di belakangnya
pythonw market_hud.pyw

# Atau uji engine collector di terminal (CLI Mode)
python collector.py
```

---

## Tombol Kontrol (Hotkeys)
- **Klik & Drag**: Geser jendela ke posisi mana pun di monitor.
- **ESC** atau **Q**: Tutup aplikasi secara bersih.
- **SPASI** atau **R**: Trigger refresh manual instan (aplikasi juga melakukan auto-polling setiap 3 detik).
