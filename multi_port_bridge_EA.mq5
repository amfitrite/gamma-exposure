//+------------------------------------------------------------------+
//|                                        multi port bridge EA.mq5  |
//|                                    Copyright 2026, Tick Map Pro  |
//|                   High-Performance Real-Time Order Flow Bridge   |
//|                          Multi-Client Concurrent Port Streamer   |
//+------------------------------------------------------------------+
#property copyright   "Tick Map Pro Engine"
#property link        "https://github.com/tickmap"
#property version     "5.50"
#property description "Multi Port Bridge EA - Broadcast Tick & Histori hingga 5 Port Paralel (5555+)"

#define MAX_PORTS 5

//--- INPUT PARAMETERS ---
input group "=== KONFIGURASI MULTI-PORT (TCP HOST) ==="
input string   InpServerHost        = "127.0.0.1";    // Server Host (IP Address)
input int      InpReconnectSec      = 2;              // Interval Reconnect Otomatis (Detik)

input group "--- PORT 1 (Utama) ---"
input bool     InpEnablePort1       = true;           // Aktifkan Port 1
input int      InpPort1             = 5555;           // Nomor Port 1

input group "--- PORT 2 ---"
input bool     InpEnablePort2       = true;           // Aktifkan Port 2
input int      InpPort2             = 5556;           // Nomor Port 2

input group "--- PORT 3 ---"
input bool     InpEnablePort3       = false;          // Aktifkan Port 3
input int      InpPort3             = 5557;           // Nomor Port 3

input group "--- PORT 4 ---"
input bool     InpEnablePort4       = false;          // Aktifkan Port 4
input int      InpPort4             = 5558;           // Nomor Port 4

input group "--- PORT 5 ---"
input bool     InpEnablePort5       = false;          // Aktifkan Port 5
input int      InpPort5             = 5559;           // Nomor Port 5

input group "=== HISTORI TICK AWAL ==="
input bool     InpSendHistory       = true;           // Kirim Tick Histori Saat Terhubung
input int      InpHistoryDays       = 1;              // Hari Histori Awal (1 Hari Ideal)
input int      InpMaxHistoryTicks   = 5000;           // Batas Maksimum Histori Tick (Anti-Freeze)

input group "=== PENGATURAN INSTRUMEN ==="
input bool     InpAutoDetectTick    = true;           // Deteksi Otomatis Tick Size
input double   InpManualTickSize    = 0.5;            // Manual Tick Size (Jika Auto OFF)

//--- STRUCT STATUS PER PORT ---
struct PortClient
{
    int      port;
    bool     enabled;
    int      socket;
    bool     is_connected;
    bool     history_sent;
    datetime last_reconnect;
    ulong    live_ticks_sent;
    ulong    hist_ticks_sent;
};

//--- GLOBAL VARIABLES ---
PortClient     g_ports[MAX_PORTS];
double         g_actual_tick_size   = 0.5;
double         g_prev_bid           = 0.0;
double         g_prev_ask           = 0.0;
double         g_prev_last          = 0.0;
uint           g_prev_flag          = 32;
ulong          g_total_ticks_sent   = 0;

//+------------------------------------------------------------------+
//| Helper Inisialisasi Data Port                                    |
//+------------------------------------------------------------------+
void InitPortConfigs()
{
    g_ports[0].port = InpPort1;  g_ports[0].enabled = InpEnablePort1;
    g_ports[1].port = InpPort2;  g_ports[1].enabled = InpEnablePort2;
    g_ports[2].port = InpPort3;  g_ports[2].enabled = InpEnablePort3;
    g_ports[3].port = InpPort4;  g_ports[3].enabled = InpEnablePort4;
    g_ports[4].port = InpPort5;  g_ports[4].enabled = InpEnablePort5;

    for(int i = 0; i < MAX_PORTS; i++)
    {
        g_ports[i].socket          = INVALID_HANDLE;
        g_ports[i].is_connected    = false;
        g_ports[i].history_sent    = false;
        g_ports[i].last_reconnect  = 0;
        g_ports[i].live_ticks_sent = 0;
        g_ports[i].hist_ticks_sent = 0;
    }
}

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    InitPortConfigs();

    // 1. Tentukan Tick Size Instrumen
    if(InpAutoDetectTick)
    {
        double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
        if(ts > 0.0)
            g_actual_tick_size = ts;
        else
            g_actual_tick_size = _Point;
    }
    else
    {
        g_actual_tick_size = InpManualTickSize;
    }

    PrintFormat("[Multi Port Bridge] Memulai bridge untuk %s (Digits: %d, TickSize: %s)", 
                _Symbol, _Digits, DoubleToString(g_actual_tick_size, _Digits));

    // 2. Pasang Timer 1 Detik untuk Auto-Reconnect mandiri tiap port & refresh HUD
    EventSetTimer(1);

    // 3. Lakukan percobaan koneksi awal ke port yang aktif
    for(int i = 0; i < MAX_PORTS; i++)
    {
        if(g_ports[i].enabled)
        {
            ConnectPort(i);
        }
    }

    UpdateChartHUD();
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    EventKillTimer();
    for(int i = 0; i < MAX_PORTS; i++)
    {
        ClosePortSocket(i);
    }
    Comment(""); // Bersihkan HUD komentar di chart
    Print("[Multi Port Bridge] Seluruh port ditutup. Bridge dihentikan.");
}

//+------------------------------------------------------------------+
//| Tutup Socket per Port Tertentu Secara Aman                       |
//+------------------------------------------------------------------+
void ClosePortSocket(int idx)
{
    if(idx < 0 || idx >= MAX_PORTS) return;

    if(g_ports[idx].socket != INVALID_HANDLE)
    {
        SocketClose(g_ports[idx].socket);
        g_ports[idx].socket = INVALID_HANDLE;
    }
    g_ports[idx].is_connected = false;
    g_ports[idx].history_sent = false;
}

void SendHistoryToPort(int idx);
bool SendRawStringToSocket(int socket_h, const string data);

//+------------------------------------------------------------------+
//| Hubungkan Port Tertentu Secara Terisolasi                        |
//+------------------------------------------------------------------+
bool ConnectPort(int idx)
{
    if(idx < 0 || idx >= MAX_PORTS || !g_ports[idx].enabled) return false;

    ClosePortSocket(idx);

    int s = SocketCreate();
    if(s == INVALID_HANDLE)
    {
        return false;
    }

    // Timeout singkat 300ms agar OnTick / OnTimer tidak freeze jika salah satu app belum jalan
    if(!SocketConnect(s, InpServerHost, g_ports[idx].port, 300))
    {
        SocketClose(s);
        return false;
    }

    g_ports[idx].socket       = s;
    g_ports[idx].is_connected = true;
    PrintFormat("[Multi Port Bridge] [PORT %d] TERHUBUNG ke %s:%d!", idx + 1, InpServerHost, g_ports[idx].port);

    // Kirim Handshake Spesifikasi Instrumen
    double contract_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE);
    string meta_line = StringFormat("#META:%s,%d,%s,%s,%s\n",
                                    _Symbol,
                                    _Digits,
                                    DoubleToString(_Point, 10),
                                    DoubleToString(g_actual_tick_size, _Digits),
                                    DoubleToString(contract_size, 2));

    string handshake = StringFormat("#SYMBOL:%s\n%s", _Symbol, meta_line);
    SendRawStringToSocket(g_ports[idx].socket, handshake);

    // Kirim histori tick awal khusus untuk port yang baru saja terhubung ini
    g_ports[idx].history_sent = false;
    SendHistoryToPort(idx);

    return true;
}

//+------------------------------------------------------------------+
//| Mengirim Raw String via Socket Tertentu                          |
//+------------------------------------------------------------------+
bool SendRawStringToSocket(int socket_h, const string data)
{
    if(socket_h == INVALID_HANDLE) return false;

    uchar buf[];
    int len = StringToCharArray(data, buf, 0, WHOLE_ARRAY, CP_UTF8) - 1;
    if(len <= 0) return true;

    int offset = 0;
    while(offset < len)
    {
        if(!SocketIsWritable(socket_h))
        {
            return false;
        }

        int to_send = len - offset;
        if(to_send > 32768) to_send = 32768; // Chunk 32KB

        uchar chunk[];
        ArrayCopy(chunk, buf, 0, offset, to_send);
        int sent = SocketSend(socket_h, chunk, to_send);

        if(sent <= 0)
        {
            return false;
        }
        offset += sent;
    }
    return true;
}

//+------------------------------------------------------------------+
//| Format Tick Menjadi Baris Protokol Tick Map                      |
//| Format: timestamp_ms,bid,ask,last,volume,flags                   |
//+------------------------------------------------------------------+
string FormatTick(const MqlTick &t)
{
    double vol = (t.volume_real > 0.0) ? t.volume_real : (double)t.volume;
    if(vol <= 0.0) vol = 1.0;

    uint flags = t.flags;
    double px = t.last;

    if(px <= 0.0)
    {
        if(g_prev_bid > 0.0)
        {
            if(t.bid > g_prev_bid || t.ask > g_prev_ask)
            {
                flags |= 32; // TICK_FLAG_BUY (Uptick)
                px = t.ask;
                g_prev_flag = 32;
            }
            else if(t.bid < g_prev_bid || t.ask < g_prev_ask)
            {
                flags |= 64; // TICK_FLAG_SELL (Downtick)
                px = t.bid;
                g_prev_flag = 64;
            }
            else
            {
                flags |= g_prev_flag;
                px = (g_prev_flag == 32) ? t.ask : t.bid;
            }
        }
        else
        {
            flags |= 32;
            px = t.bid;
        }
    }
    else
    {
        if(!(flags & 32) && !(flags & 64))
        {
            if(t.ask > t.bid)
            {
                double mid = (t.bid + t.ask) / 2.0;
                if(px > mid) flags |= 32;
                else if(px < mid) flags |= 64;
                else if(g_prev_last > 0.0)
                {
                    if(px >= g_prev_last) flags |= 32;
                    else flags |= 64;
                }
                else flags |= 32;
            }
        }
    }

    g_prev_bid = t.bid;
    g_prev_ask = t.ask;
    g_prev_last = (t.last > 0.0) ? t.last : px;

    return StringFormat("%I64d,%s,%s,%s,%.2f,%u\n",
                        t.time_msc,
                        DoubleToString(t.bid, _Digits),
                        DoubleToString(t.ask, _Digits),
                        DoubleToString(px, _Digits),
                        vol,
                        flags);
}

//+------------------------------------------------------------------+
//| Mengirim Histori Tick ke Port Tertentu                           |
//+------------------------------------------------------------------+
void SendHistoryToPort(int idx)
{
    if(idx < 0 || idx >= MAX_PORTS || !g_ports[idx].is_connected) return;

    if(!InpSendHistory)
    {
        g_ports[idx].history_sent = true;
        return;
    }

    MqlTick history[];
    datetime from_time = TimeCurrent() - (InpHistoryDays * 86400);
    int count = CopyTicksRange(_Symbol, history, COPY_TICKS_ALL, ((ulong)from_time) * 1000, 0);

    if(count <= 0)
    {
        count = CopyTicks(_Symbol, history, COPY_TICKS_ALL, 0, InpMaxHistoryTicks);
    }
    else if(count > InpMaxHistoryTicks)
    {
        ArrayRemove(history, 0, count - InpMaxHistoryTicks);
        count = ArraySize(history);
    }

    if(count > 0)
    {
        PrintFormat("[Multi Port Bridge] Mengirim %d tick histori ke Port %d...", count, g_ports[idx].port);
        SendRawStringToSocket(g_ports[idx].socket, StringFormat("#HIST_START:%d\n", count));

        string batch = "";
        for(int i = 0; i < count; i++)
        {
            batch += FormatTick(history[i]);
            if(StringLen(batch) >= 16384)
            {
                if(!SendRawStringToSocket(g_ports[idx].socket, batch))
                {
                    ClosePortSocket(idx);
                    return;
                }
                batch = "";
            }
        }
        if(StringLen(batch) > 0)
        {
            if(!SendRawStringToSocket(g_ports[idx].socket, batch))
            {
                ClosePortSocket(idx);
                return;
            }
        }

        SendRawStringToSocket(g_ports[idx].socket, "#HIST_END\n");
        g_ports[idx].hist_ticks_sent += count;
    }

    g_ports[idx].history_sent = true;
}

//+------------------------------------------------------------------+
//| Broadcast Tick ke Seluruh Port Aktif Secara Paralel              |
//+------------------------------------------------------------------+
void BroadcastTick(const MqlTick &cur)
{
    // Format tick sekali saja
    string tick_str = FormatTick(cur);

    uchar buf[];
    int len = StringToCharArray(tick_str, buf, 0, WHOLE_ARRAY, CP_UTF8) - 1;
    if(len <= 0) return;

    bool any_sent = false;

    // Distribusikan ke setiap socket port yang sedang terhubung
    for(int i = 0; i < MAX_PORTS; i++)
    {
        if(g_ports[i].enabled && g_ports[i].is_connected && g_ports[i].socket != INVALID_HANDLE)
        {
            if(!SocketIsWritable(g_ports[i].socket))
            {
                ClosePortSocket(i);
                continue;
            }

            int sent = SocketSend(g_ports[i].socket, buf, len);
            if(sent <= 0)
            {
                ClosePortSocket(i); // Port ini terputus, tapi port lain tetap aman!
            }
            else
            {
                g_ports[i].live_ticks_sent++;
                any_sent = true;
            }
        }
    }

    if(any_sent)
    {
        g_total_ticks_sent++;
        if(g_total_ticks_sent % 100 == 0)
            UpdateChartHUD();
    }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    MqlTick cur;
    if(SymbolInfoTick(_Symbol, cur))
    {
        BroadcastTick(cur);
    }
}

//+------------------------------------------------------------------+
//| Timer function: Auto-Reconnect per Port Mandiri                  |
//+------------------------------------------------------------------+
void OnTimer()
{
    datetime now = TimeLocal();

    for(int i = 0; i < MAX_PORTS; i++)
    {
        if(g_ports[i].enabled && !g_ports[i].is_connected)
        {
            if(now - g_ports[i].last_reconnect >= InpReconnectSec)
            {
                g_ports[i].last_reconnect = now;
                ConnectPort(i);
            }
        }
    }

    UpdateChartHUD();
}

//+------------------------------------------------------------------+
//| Tampilan Status Chart Komentar Mewah Multi-Port                  |
//+------------------------------------------------------------------+
void UpdateChartHUD()
{
    string hud = "";
    hud += "====================================================\n";
    hud += "       ⚡ MULTI PORT BRIDGE EA (5 PORTS) ⚡\n";
    hud += "====================================================\n";
    hud += StringFormat("Target Host     : %s\n", InpServerHost);
    hud += StringFormat("Instrumen Aktif : %s (Digits: %d)\n", _Symbol, _Digits);
    hud += StringFormat("Tick Size       : %s\n", DoubleToString(g_actual_tick_size, _Digits));
    hud += "----------------------------------------------------\n";
    hud += "STATUS PORT CLIENT:\n";

    int online_count = 0;
    for(int i = 0; i < MAX_PORTS; i++)
    {
        string status_str = "";
        if(!g_ports[i].enabled)
        {
            status_str = "⚪ [DISABLED]";
        }
        else if(g_ports[i].is_connected)
        {
            status_str = StringFormat("🟢 ONLINE  (Live: %I64u | Hist: %I64u)", 
                                      g_ports[i].live_ticks_sent, g_ports[i].hist_ticks_sent);
            online_count++;
        }
        else
        {
            status_str = "🔴 RECONNECTING...";
        }

        hud += StringFormat("  Port %d (%d) : %s\n", i + 1, g_ports[i].port, status_str);
    }

    hud += "----------------------------------------------------\n";
    hud += StringFormat("Total Port Aktif  : %d dari %d port terhubung\n", online_count, MAX_PORTS);
    hud += StringFormat("Total Tick Siar   : %I64u tick\n", g_total_ticks_sent);
    hud += "====================================================\n";
    if(online_count == 0)
    {
        hud += ">> Menunggu aplikasi klien terhubung pada port di atas <<\n";
    }

    Comment(hud);
}
//+------------------------------------------------------------------+
