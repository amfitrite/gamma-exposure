"""
Gamma Exposure (GEX) Text-Based Terminal.
- MT5 Direct Socket Stream via Port 5556
- Real-time Cross-Market Analytics (XAUUSD, COMEX, BTCUSD, XAUTUSDT)
- Ultra-Minimalist UI: The ONLY interactive control is the 3-mode selector.
- Exclusive Per-Mode Display (Zero Cross-Clutter)
- Frameless Window, Zero Extra Console Panels, No Visual Charts.
"""

import sys
import os
import time
import datetime
import threading
import tkinter as tk
from tkinter import font as tkfont

# 1. HIDE CONSOLE WINDOW ON WINDOWS (Zero extra panel / No flashing CMD)
if sys.platform == "win32":
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass

# Import core collector, listener, and GEX engine
from collector import fetch_all_market_data
from mt5_listener import MT5StreamListener
import gex_engine

class GEXTerminalHUD:
    def __init__(self, root):
        self.root = root
        self.root.title("GEX Terminal")
        
        # 2. FRAMELESS WINDOW (Hapus total title bar dan border OS)
        self.root.overrideredirect(True)
        
        # Styling Palet Warna Retro / Terminal Hacker Minimalis
        self.c_bg = "#0c1017"           # Deep dark background
        self.c_panel_bg = "#111722"     # Panel background
        self.c_border = "#263040"       # Subtle border accent
        self.c_header_bg = "#151c27"    # Header bar bg
        self.c_active_btn = "#1f3b5c"   # Active Mode Button BG
        self.c_active_fg = "#58a6ff"    # Active Mode Text (Cyan)
        self.c_inactive_btn = "#131923" # Inactive Button BG
        self.c_inactive_fg = "#7d8590"  # Inactive Button Text
        self.c_text_main = "#e6edf3"    # Crisp white text
        self.c_text_dim = "#8b949e"     # Gray dim text
        self.c_green = "#3fb950"        # Positive / +GEX
        self.c_red = "#f85149"          # Negative / -GEX
        self.c_yellow = "#d29922"       # Warning / Notice
        
        # Dimensi Jendela
        self.win_width = 820
        self.win_height = 540
        
        # Posisikan tepat di tengah layar
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        start_x = max(0, (screen_w - self.win_width) // 2)
        start_y = max(0, (screen_h - self.win_height) // 2)
        self.root.geometry(f"{self.win_width}x{self.win_height}+{start_x}+{start_y}")
        self.root.configure(bg=self.c_border)
        
        # Mode Saat Ini: 1 = "XAUUSD", 2 = "BTCUSD", 3 = "XAUTUSDT"
        self.current_mode = "XAUUSD"
        
        # State Data Cache
        self.is_running = True
        self.market_cache = {}
        
        # Inisialisasi MT5 Socket Listener di Port 5556
        self.mt5_listener = MT5StreamListener(port=5556)
        self.mt5_listener.start()
        
        # Buat Font Monospace Standar
        self.font_title = tkfont.Font(family="Consolas", size=10, weight="bold")
        self.font_btn = tkfont.Font(family="Consolas", size=11, weight="bold")
        self.font_mono = tkfont.Font(family="Consolas", size=10)
        self.font_mono_bold = tkfont.Font(family="Consolas", size=10, weight="bold")
        self.font_mono_sm = tkfont.Font(family="Consolas", size=9)
        
        # Frame Kontainer Utama
        self.container = tk.Frame(self.root, bg=self.c_bg)
        self.container.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Pasang Interaksi Mouse Dragging (Pindah Jendela Tanpa Titlebar)
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.container.bind("<ButtonPress-1>", self.on_drag_start)
        self.container.bind("<B1-Motion>", self.on_drag_motion)
        
        # Pasang Keyboard Hotkeys
        self.root.bind("<Escape>", lambda e: self.close_app())
        self.root.bind("<q>", lambda e: self.close_app())
        self.root.bind("<Q>", lambda e: self.close_app())
        self.root.bind("1", lambda e: self.set_mode("XAUUSD"))
        self.root.bind("2", lambda e: self.set_mode("BTCUSD"))
        self.root.bind("3", lambda e: self.set_mode("XAUTUSDT"))
        
        self.build_ui()
        
        # Jalankan Thread Pengambil Feed Pasar (COMEX, BTC, XAUT)
        self.crawler_thread = threading.Thread(target=self.bg_crawler_loop, daemon=True)
        self.crawler_thread.start()
        
        # Jadwalkan Loop Refresh Tampilan Cepat (Setiap 200ms untuk streaming tick halus)
        self.schedule_ui_tick()

    def on_drag_start(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_drag_motion(self, event):
        deltax = event.x - self.drag_start_x
        deltay = event.y - self.drag_start_y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def build_ui(self):
        # 1. TOP HEADER (STATUS BAR & EXIT)
        top_bar = tk.Frame(self.container, bg=self.c_header_bg, height=30)
        top_bar.pack(fill=tk.X, side=tk.TOP)
        top_bar.bind("<ButtonPress-1>", self.on_drag_start)
        top_bar.bind("<B1-Motion>", self.on_drag_motion)
        
        self.lbl_stream_status = tk.Label(
            top_bar, 
            text=" ▰ MT5 STREAM [PORT: 5556] : MENUNGGU EA...", 
            font=self.font_mono_bold, 
            fg=self.c_yellow, 
            bg=self.c_header_bg
        )
        self.lbl_stream_status.pack(side=tk.LEFT, padx=10, pady=4)
        self.lbl_stream_status.bind("<ButtonPress-1>", self.on_drag_start)
        self.lbl_stream_status.bind("<B1-Motion>", self.on_drag_motion)
        
        btn_close = tk.Label(
            top_bar, 
            text=" [ESC: Keluar] [X] ", 
            font=self.font_mono_sm, 
            fg=self.c_text_dim, 
            bg=self.c_header_bg, 
            cursor="hand2"
        )
        btn_close.pack(side=tk.RIGHT, padx=6)
        btn_close.bind("<Button-1>", lambda e: self.close_app())
        btn_close.bind("<Enter>", lambda e: btn_close.configure(fg=self.c_red))
        btn_close.bind("<Leave>", lambda e: btn_close.configure(fg=self.c_text_dim))

        # 2. SATU-SATUNYA KONTROL: TOMBOL PEMILIH 3 MODE
        mode_bar = tk.Frame(self.container, bg=self.c_bg)
        mode_bar.pack(fill=tk.X, padx=16, pady=(12, 6))
        
        lbl_pilih = tk.Label(
            mode_bar, 
            text="PILIH MODE :", 
            font=self.font_mono_bold, 
            fg=self.c_text_dim, 
            bg=self.c_bg
        )
        lbl_pilih.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_mode_xau = tk.Label(
            mode_bar, 
            text=" [ 1 ] XAUUSD ", 
            font=self.font_btn, 
            padx=16, 
            pady=4, 
            cursor="hand2"
        )
        self.btn_mode_xau.pack(side=tk.LEFT, padx=6)
        self.btn_mode_xau.bind("<Button-1>", lambda e: self.set_mode("XAUUSD"))
        
        self.btn_mode_btc = tk.Label(
            mode_bar, 
            text=" [ 2 ] BTCUSD ", 
            font=self.font_btn, 
            padx=16, 
            pady=4, 
            cursor="hand2"
        )
        self.btn_mode_btc.pack(side=tk.LEFT, padx=6)
        self.btn_mode_btc.bind("<Button-1>", lambda e: self.set_mode("BTCUSD"))
        
        self.btn_mode_xaut = tk.Label(
            mode_bar, 
            text=" [ 3 ] XAUTUSDT ", 
            font=self.font_btn, 
            padx=16, 
            pady=4, 
            cursor="hand2"
        )
        self.btn_mode_xaut.pack(side=tk.LEFT, padx=6)
        self.btn_mode_xaut.bind("<Button-1>", lambda e: self.set_mode("XAUTUSDT"))

        # Garis Pembatas
        sep1 = tk.Frame(self.container, bg=self.c_border, height=1)
        sep1.pack(fill=tk.X, padx=16, pady=(8, 8))

        # 3. SPOT PRICE HEADER PANEL (Dinamis Sesuai Mode Aktif)
        self.spot_panel = tk.Frame(self.container, bg=self.c_panel_bg, padx=12, pady=8)
        self.spot_panel.pack(fill=tk.X, padx=16, pady=4)
        
        self.lbl_spot_title = tk.Label(
            self.spot_panel, 
            text="SPOT FEED", 
            font=self.font_mono_bold, 
            fg=self.c_active_fg, 
            bg=self.c_panel_bg, 
            anchor="w"
        )
        self.lbl_spot_title.pack(fill=tk.X)
        
        self.lbl_spot_detail = tk.Label(
            self.spot_panel, 
            text="Memuat harga live...", 
            font=self.font_mono, 
            fg=self.c_text_main, 
            bg=self.c_panel_bg, 
            anchor="w"
        )
        self.lbl_spot_detail.pack(fill=tk.X, pady=(2, 0))

        # 4. KONTEN GEX EKSKLUSIF PER MODE (Text Box Monospace)
        self.content_frame = tk.Frame(self.container, bg=self.c_bg)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=6)
        
        # Buat Text Widget Read-Only untuk Render Teks Presisi
        self.txt_display = tk.Text(
            self.content_frame, 
            bg=self.c_bg, 
            fg=self.c_text_main, 
            font=self.font_mono, 
            relief=tk.FLAT, 
            bd=0, 
            highlightthickness=0, 
            wrap=tk.NONE
        )
        self.txt_display.pack(fill=tk.BOTH, expand=True)
        
        # Konfigurasi Tag Warna untuk Text Widget
        self.txt_display.tag_configure("title", font=self.font_mono_bold, foreground=self.c_active_fg)
        self.txt_display.tag_configure("green", font=self.font_mono_bold, foreground=self.c_green)
        self.txt_display.tag_configure("red", font=self.font_mono_bold, foreground=self.c_red)
        self.txt_display.tag_configure("yellow", font=self.font_mono_bold, foreground=self.c_yellow)
        self.txt_display.tag_configure("dim", font=self.font_mono_sm, foreground=self.c_text_dim)
        self.txt_display.tag_configure("white_bold", font=self.font_mono_bold, foreground=self.c_text_main)

        # 5. FOOTER
        footer = tk.Frame(self.container, bg=self.c_header_bg, height=24)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.lbl_footer = tk.Label(
            footer, 
            text="GEX TERMINAL // KLIK TOMBOL 1, 2, ATAU 3 UNTUK GANTI MODE │ DRAG UNTUK GESER", 
            font=self.font_mono_sm, 
            fg=self.c_text_dim, 
            bg=self.c_header_bg
        )
        self.lbl_footer.pack(side=tk.LEFT, padx=10, pady=2)
        
        self.lbl_time = tk.Label(
            footer, 
            text="", 
            font=self.font_mono_sm, 
            fg=self.c_active_fg, 
            bg=self.c_header_bg
        )
        self.lbl_time.pack(side=tk.RIGHT, padx=10, pady=2)
        
        self.update_button_visuals()

    def set_mode(self, mode):
        if self.current_mode != mode:
            self.current_mode = mode
            self.update_button_visuals()
            self.render_active_mode_view()

    def update_button_visuals(self):
        buttons = {
            "XAUUSD": self.btn_mode_xau,
            "BTCUSD": self.btn_mode_btc,
            "XAUTUSDT": self.btn_mode_xaut
        }
        for m, btn in buttons.items():
            if m == self.current_mode:
                btn.configure(
                    bg=self.c_active_btn, 
                    fg=self.c_active_fg, 
                    relief=tk.SOLID, 
                    bd=1
                )
            else:
                btn.configure(
                    bg=self.c_inactive_btn, 
                    fg=self.c_inactive_fg, 
                    relief=tk.FLAT, 
                    bd=0
                )

    def bg_crawler_loop(self):
        """Thread latar belakang mengambil feed pasar independen."""
        while self.is_running:
            try:
                data = fetch_all_market_data()
                market_dict = {}
                for it in data.get("items", []):
                    if it and "symbol" in it:
                        market_dict[it["symbol"]] = it
                self.market_cache = market_dict
            except Exception:
                pass
            time.sleep(3.0)

    def schedule_ui_tick(self):
        if not self.is_running:
            return
        self.render_active_mode_view()
        self.root.after(200, self.schedule_ui_tick)

    def render_active_mode_view(self):
        # 1. Update Status MT5 Stream
        mt5_st = self.mt5_listener.get_status()
        is_conn = mt5_st["is_connected"]
        tick = mt5_st["tick"]
        
        now_str = datetime.datetime.now().strftime("%H:%M:%S WIB")
        self.lbl_time.configure(text=now_str)
        
        bound_p = mt5_st.get("bound_port", 5556)
        if is_conn:
            t_cnt = tick.get("count", 0)
            self.lbl_stream_status.configure(
                text=f" ▰ MT5 [PORT: {bound_p}] : STREAMING AKTIF ({mt5_st['symbol']}) │ LIVE TICKS: {t_cnt}",
                fg=self.c_green
            )
        else:
            self.lbl_stream_status.configure(
                text=f" ▰ MT5 [PORT: {bound_p}] : MENUNGGU EA TERHUBUNG...",
                fg=self.c_yellow
            )

        # Ambil Cache Data Crawler
        btc_data = self.market_cache.get("BTC/USDT", {})
        xaut_data = self.market_cache.get("XAUT/USDT", {})
        gold_data = self.market_cache.get("GOLD COMEX", {})

        comex_px = gold_data.get("price", 0.0)
        comex_chg = gold_data.get("change_pct", 0.0)
        btc_px = btc_data.get("price", 0.0)
        btc_chg = btc_data.get("change_pct", 0.0)
        xaut_px = xaut_data.get("price", 0.0)
        xaut_chg = xaut_data.get("change_pct", 0.0)

        # Tentukan Harga Spot XAUUSD (dari MT5 atau Fallback COMEX jika MT5 belum tersambung)
        if is_conn and tick["bid"] > 0:
            xau_spot = tick["last"] if tick["last"] > 0 else (tick["bid"] + tick["ask"]) / 2.0
            xau_bid = tick["bid"]
            xau_ask = tick["ask"]
            xau_spread = tick["spread"]
            xau_vol = tick["vol"]
        else:
            xau_spot = comex_px if comex_px > 0 else 2745.0
            xau_bid = xau_spot - 0.15
            xau_ask = xau_spot + 0.15
            xau_spread = 0.30
            xau_vol = 1.0

        # Kosongkan Text Widget
        self.txt_display.configure(state=tk.NORMAL)
        self.txt_display.delete("1.0", tk.END)

        # RENDER EKSKLUSIF BERDASARKAN MODE
        if self.current_mode == "XAUUSD":
            # --- MODE 1: XAUUSD ---
            src_label = "MT5 LIVE STREAM" if is_conn else "COMEX PROXY FEED"
            self.lbl_spot_title.configure(text=f">> MODE: XAUUSD (SPOT GOLD) [{src_label}]")
            self.lbl_spot_detail.configure(
                text=f"Spot: ${xau_spot:,.2f}  │  Bid: ${xau_bid:,.2f}  │  Ask: ${xau_ask:,.2f}  │  Spread: ${xau_spread:.2f}  │  Vol: {xau_vol:.2f}"
            )

            # Hitung 3 Pilar GEX XAUUSD (COMEX Benchmark + 2 Custom GEX)
            g_comex = gex_engine.compute_gold_comex_gex(xau_spot, comex_px, comex_chg)
            g_btc = gex_engine.compute_gold_via_btcusd_custom_gex(xau_spot, btc_px, btc_chg)
            g_xaut = gex_engine.compute_gold_via_xautusdt_custom_gex(xau_spot, xaut_px, xaut_chg)

            # 1. COMEX
            self.txt_display.insert(tk.END, "1. COMEX\n", "title")
            basis_str = f"{g_comex['basis_spread']:+.2f}"
            self.txt_display.insert(tk.END, f"   • Basis vs Futures : ${basis_str}\n")
            
            regime_tag = "green" if g_comex["is_positive"] else "red"
            self.txt_display.insert(tk.END, f"   • Gamma Regime     : ")
            self.txt_display.insert(tk.END, f"{g_comex['regime']}\n", regime_tag)
            self.txt_display.insert(tk.END, f"   • Gamma Flip Level : ")
            self.txt_display.insert(tk.END, f"${g_comex['gamma_flip']:,.2f}\n", "yellow")
            self.txt_display.insert(tk.END, f"   • Major Call Wall  : ${g_comex['call_wall']:,.2f}\n")
            self.txt_display.insert(tk.END, f"   • Major Put Wall   : ${g_comex['put_wall']:,.2f}\n")
            self.txt_display.insert(tk.END, f"   • Net Dollar GEX   : ${g_comex['net_gex_m']:+.2f}M per 1% move\n\n")

            # 2. BTCUSD
            self.txt_display.insert(tk.END, "2. BTCUSD\n", "title")
            self.txt_display.insert(tk.END, f"   • BTC Spot Price   : ${g_btc['btc_price']:,.2f} ({g_btc['btc_chg_pct']:+.2f}%) │ Rasio: {g_btc['ratio_btc_to_xau']:.2f}x\n")
            btc_tag = "green" if g_btc["is_positive"] else "red"
            self.txt_display.insert(tk.END, f"   • BTC Gamma Status : ")
            self.txt_display.insert(tk.END, f"{g_btc['regime']}\n", btc_tag)
            self.txt_display.insert(tk.END, f"   • BTC Gamma Flip   : ")
            self.txt_display.insert(tk.END, f"${g_btc['gamma_flip']:,.2f}\n", "yellow")
            self.txt_display.insert(tk.END, f"   • Strike Walls XAU : Call: ${g_btc['call_wall']:,.2f} │ Put: ${g_btc['put_wall']:,.2f}\n")
            self.txt_display.insert(tk.END, f"   • Net BTC GEX Flow : ${g_btc['net_gex_m']:+.2f}M │ {g_btc['spillover_risk']}\n\n")

            # 3. XAUTUSDT
            self.txt_display.insert(tk.END, "3. XAUTUSDT\n", "title")
            self.txt_display.insert(tk.END, f"   • XAUT Spot Price  : ${g_xaut['xaut_price']:,.2f} │ Spread: ${g_xaut['basis_spread']:+.2f} ({g_xaut['pct_spread']:+.2f}%)\n")
            xaut_tag = "green" if g_xaut["is_positive"] else "red"
            self.txt_display.insert(tk.END, f"   • Peg Gamma Status : ")
            self.txt_display.insert(tk.END, f"{g_xaut['regime']}\n", xaut_tag)
            self.txt_display.insert(tk.END, f"   • Peg Gamma Flip   : ")
            self.txt_display.insert(tk.END, f"${g_xaut['gamma_flip']:,.2f} │ Pasak: {g_xaut['peg_stability']}\n", "yellow")
            self.txt_display.insert(tk.END, f"   • Arbitrage Walls  : Call: ${g_xaut['call_wall']:,.2f} │ Put: ${g_xaut['put_wall']:,.2f}\n")
            self.txt_display.insert(tk.END, f"   • Net XAUT GEX     : ${g_xaut['net_gex_m']:+.2f}M per 1% move\n")

        elif self.current_mode == "BTCUSD":
            # --- MODE 2: BTCUSD ---
            chg_arrow = "▲" if btc_chg >= 0 else "▼"
            self.lbl_spot_title.configure(text=">> MODE: BTCUSD")
            self.lbl_spot_detail.configure(
                text=f"Spot: ${btc_px:,.2f}  │  24H Change: {btc_chg:+.2f}% {chg_arrow}"
            )

            g_btc_mode = gex_engine.compute_mode_btcusd_custom_gex(btc_px, btc_chg, xaut_px)

            self.txt_display.insert(tk.END, "1. XAUTUSDT\n", "title")
            self.txt_display.insert(tk.END, f"   • XAUT Spot Price  : ${g_btc_mode['xaut_price']:,.2f} │ Rasio: {g_btc_mode['ratio_xaut_per_btc']:.2f} XAUT/BTC\n")
            reg_tag = "green" if g_btc_mode["is_positive"] else "red"
            self.txt_display.insert(tk.END, f"   • Gamma Regime     : ")
            self.txt_display.insert(tk.END, f"{g_btc_mode['regime']}\n", reg_tag)
            self.txt_display.insert(tk.END, f"   • BTC Gamma Flip   : ")
            self.txt_display.insert(tk.END, f"${g_btc_mode['gamma_flip']:,.2f}\n", "yellow")
            self.txt_display.insert(tk.END, f"   • Major Walls BTC  : Call: ${g_btc_mode['call_wall']:,.2f} │ Put: ${g_btc_mode['put_wall']:,.2f}\n")
            self.txt_display.insert(tk.END, f"   • Net Dollar GEX   : ${g_btc_mode['net_gex_m']:+.2f}M per 1% move\n")
            self.txt_display.insert(tk.END, f"   • Capital Rotation : ")
            self.txt_display.insert(tk.END, f"{g_btc_mode['flow_bias']}\n", "yellow")
            self.txt_display.insert(tk.END, f"   • Hedging Trigger  : ")
            self.txt_display.insert(tk.END, f"Jika BTC < ${g_btc_mode['hedging_trigger']:,.2f}\n", "red")

        elif self.current_mode == "XAUTUSDT":
            # --- MODE 3: XAUTUSDT ---
            chg_arrow = "▲" if xaut_chg >= 0 else "▼"
            self.lbl_spot_title.configure(text=">> MODE: XAUTUSDT")
            self.lbl_spot_detail.configure(
                text=f"Spot: ${xaut_px:,.2f}  │  24H Change: {xaut_chg:+.2f}% {chg_arrow}"
            )

            g_xaut_mode = gex_engine.compute_mode_xautusdt_custom_gex(xaut_px, xaut_chg, btc_px, btc_chg)

            self.txt_display.insert(tk.END, "1. BTCUSD\n", "title")
            self.txt_display.insert(tk.END, f"   • BTC Spot Price   : ${g_xaut_mode['btc_price']:,.2f} ({g_xaut_mode['btc_chg_pct']:+.2f}%)\n")
            reg_tag = "green" if g_xaut_mode["is_positive"] else "red"
            self.txt_display.insert(tk.END, f"   • Gamma Regime     : ")
            self.txt_display.insert(tk.END, f"{g_xaut_mode['regime']}\n", reg_tag)
            self.txt_display.insert(tk.END, f"   • XAUT Gamma Flip  : ")
            self.txt_display.insert(tk.END, f"${g_xaut_mode['gamma_flip']:,.2f}\n", "yellow")
            self.txt_display.insert(tk.END, f"   • Major Walls XAUT : Call: ${g_xaut_mode['call_wall']:,.2f} │ Put: ${g_xaut_mode['put_wall']:,.2f}\n")
            self.txt_display.insert(tk.END, f"   • Net Dollar GEX   : ${g_xaut_mode['net_gex_m']:+.2f}M per 1% move\n")
            self.txt_display.insert(tk.END, f"   • Volatility State : {g_xaut_mode['vol_state']}\n")
            self.txt_display.insert(tk.END, f"   • Rotational Bias  : ")
            self.txt_display.insert(tk.END, f"{g_xaut_mode['rotational_bias']}\n", "green")

        self.txt_display.configure(state=tk.DISABLED)

    def close_app(self):
        self.is_running = False
        try:
            self.mt5_listener.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

def main():
    root = tk.Tk()
    app = GEXTerminalHUD(root)
    root.mainloop()

if __name__ == "__main__":
    main()
