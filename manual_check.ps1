param (
    [string]$Target = "all"
)

# Konfigurasi Encoding & Tampilan
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Show-Header ($title) {
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host "                  $title" -ForegroundColor Yellow
    Write-Host "================================================================================" -ForegroundColor Cyan
}

function Check-Comex {
    Show-Header "[1/3] CEK MANUAL KONEKSI SCRAPPER 1: COMEX GOLD (YAHOO FINANCE)"
    $url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1d&range=1d"
    Write-Host "Target URL   : $url" -ForegroundColor Gray
    Write-Host "Perintah PS  : (Invoke-RestMethod -Headers @{'User-Agent'='Mozilla/5.0'} -Uri '$url').chart.result.meta" -ForegroundColor DarkGray
    Write-Host "Menghubungi Server CME/Yahoo..." -ForegroundColor White
    
    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $resp = Invoke-RestMethod -Headers @{'User-Agent'='Mozilla/5.0'} -Uri $url -TimeoutSec 5
        $sw.Stop()
        $meta = $resp.chart.result.meta
        
        Write-Host "--------------------------------------------------------------------------------" -ForegroundColor Cyan
        Write-Host "STATUS       : [200 OK] SUKSES TERHUBUNG LANGSUNG (Latency: $($sw.ElapsedMilliseconds) ms)" -ForegroundColor Green
        Write-Host "HASIL VERIFIKASI DATA RESMI:" -ForegroundColor Yellow
        $meta | Select-Object symbol, exchangeName, regularMarketPrice, chartPreviousClose, regularMarketVolume | Format-List
    } catch {
        Write-Host "--------------------------------------------------------------------------------" -ForegroundColor Red
        Write-Host "ERROR        : Gagal terhubung: $_" -ForegroundColor Red
    }
    Write-Host "================================================================================" -ForegroundColor Cyan
}

function Check-Btc {
    Show-Header "[2/3] CEK MANUAL KONEKSI SCRAPPER 2: BTC/USDT (BINANCE DATA API)"
    $url = "https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BTCUSDT"
    Write-Host "Target URL   : $url" -ForegroundColor Gray
    Write-Host "Perintah PS  : (Invoke-RestMethod -Uri '$url')" -ForegroundColor DarkGray
    Write-Host "Menghubungi Node Binance Data API..." -ForegroundColor White
    
    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $resp = Invoke-RestMethod -Uri $url -TimeoutSec 5
        $sw.Stop()
        
        Write-Host "--------------------------------------------------------------------------------" -ForegroundColor Cyan
        Write-Host "STATUS       : [200 OK] SUKSES TERHUBUNG LANGSUNG (Latency: $($sw.ElapsedMilliseconds) ms)" -ForegroundColor Green
        Write-Host "HASIL VERIFIKASI DATA RESMI:" -ForegroundColor Yellow
        $resp | Select-Object symbol, lastPrice, priceChangePercent, highPrice, lowPrice | Format-List
    } catch {
        Write-Host "--------------------------------------------------------------------------------" -ForegroundColor Red
        Write-Host "ERROR        : Gagal terhubung: $_" -ForegroundColor Red
    }
    Write-Host "================================================================================" -ForegroundColor Cyan
}

function Check-Xaut {
    Show-Header "[3/3] CEK MANUAL KONEKSI SCRAPPER 3: XAUT/USDT (OKX MARKET API)"
    $url = "https://www.okx.com/api/v5/market/ticker?instId=XAUT-USDT"
    Write-Host "Target URL   : $url" -ForegroundColor Gray
    Write-Host "Perintah PS  : (Invoke-RestMethod -Headers @{'User-Agent'='Mozilla/5.0'} -Uri '$url').data" -ForegroundColor DarkGray
    Write-Host "Menghubungi Server Pasar OKX..." -ForegroundColor White
    
    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $resp = Invoke-RestMethod -Headers @{'User-Agent'='Mozilla/5.0'} -Uri $url -TimeoutSec 5
        $sw.Stop()
        
        Write-Host "--------------------------------------------------------------------------------" -ForegroundColor Cyan
        Write-Host "STATUS       : [200 OK] SUKSES TERHUBUNG LANGSUNG (Latency: $($sw.ElapsedMilliseconds) ms)" -ForegroundColor Green
        Write-Host "HASIL VERIFIKASI DATA RESMI:" -ForegroundColor Yellow
        $resp.data | Select-Object instId, last, open24h, high24h, low24h, vol24h | Format-List
    } catch {
        Write-Host "--------------------------------------------------------------------------------" -ForegroundColor Red
        Write-Host "ERROR        : Gagal terhubung: $_" -ForegroundColor Red
    }
    Write-Host "================================================================================" -ForegroundColor Cyan
}

Clear-Host
if ($Target -eq "1" -or $Target.ToLower() -eq "comex") {
    Check-Comex
} elseif ($Target -eq "2" -or $Target.ToLower() -eq "btc") {
    Check-Btc
} elseif ($Target -eq "3" -or $Target.ToLower() -eq "xaut") {
    Check-Xaut
} else {
    Check-Comex
    Write-Host ""
    Check-Btc
    Write-Host ""
    Check-Xaut
}

Write-Host ""
Write-Host "[INFO] Hasil cek manual telah selesai dijalankan secara otomatis (Zero-Typing)." -ForegroundColor Green
Write-Host "Jendela PowerShell ini tetap terbuka untuk inspeksi Anda. Silakan tutup jika sudah selesai." -ForegroundColor Gray
