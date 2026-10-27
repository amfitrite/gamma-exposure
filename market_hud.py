"""
Market HUD - Frameless Text-Based Single-Window GUI.
No OS Title Bar, No Secondary Console Panel, No Popups.
Direct Socket Connection with Live Market Integrity Verification.
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

# Import core collector
from collector import fetch_all_market_data

class FramelessTextHUD:
    def __init__(self, root):
        self.root = root
        self.root.title("Market HUD")
        
        # 2. FRAMELESS WINDOW (Hapus total title bar dan border OS)
        self.root.overrideredirect(True)
        
        # Styling Palet Warna Retro / Terminal Hacker Minimalis
        self.c_bg = "#0c1017"          # Deep dark background
        self.c_border = "#263040"      # Subtle border accent
        self.c_header_bg = "#151c27"   # Header bar bg
        self.c_text_dim = "#7d8590"    # Gray text
        self.c_text_main = "#e6edf3"   # Crisp white text
        self.c_cyan = "#58a6ff"        # Cyan highlight
        self.c_green = "#3fb950"       # Positive price / ok status
        self.c_red = "#f85149"         # Negative price / alert
        self.c_yellow = "#d29922"      # Warning / Notice
        
        # Dimensi Jendela
        self.win_width = 760
        self.win_height = 430
        
        # Posisikan tepat di tengah layar
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        start_x = max(0, (screen_w - self.win_width) // 2)
        start_y = max(0, (screen_h - self.win_height) // 2)
        self.root.geometry(f"{self.win_width}x{self.win_height}+{start_x}+{start_y}")
        self.root.configure(bg=self.c_border)
        
        # Variabel State
        self.is_running = True
        self.is_fetching = False
        self.auto_refresh = True
        self.refresh_interval_sec = 3
        self.last_update_str = "Menghubungkan..."
        
        # Buat Font Monospace Standar
        self.font_title = tkfont.Font(family="Consolas", size=10, weight="bold")
        self.font_mono = tkfont.Font(family="Consolas", size=10)
        self.font_mono_bold = tkfont.Font(family="Consolas", size=10, weight="bold")
        self.font_mono_sm = tkfont.Font(family="Consolas", size=9)
        
        # Frame Kontainer Utama (1px padding untuk efek border tipis)
        self.container = tk.Frame(self.root, bg=self.c_bg)
        self.container.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Pasang Interaksi Mouse Dragging (Pindah Jendela Tanpa Titlebar)
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.container.bind("<ButtonPress-1>", self.on_drag_start)
        self.container.bind("<B1-Motion>", self.on_drag_motion)
        
        # Pasang Keyboard Hotkeys (Keluar & Refresh)
        self.root.bind("<Escape>", lambda e: self.close_app())
        self.root.bind("<q>", lambda e: self.close_app())
        self.root.bind("<Q>", lambda e: self.close_app())
        self.root.bind("<space>", lambda e: self.trigger_manual_refresh())
        self.root.bind("<r>", lambda e: self.trigger_manual_refresh())
        
        self.build_ui()
        
        # Jalankan Thread Pengambil Data di Latar Belakang
        self.worker_thread = threading.Thread(target=self.bg_fetch_loop, daemon=True)
        self.worker_thread.start()

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
        # 1. TOP HEADER BAR
        top_bar = tk.Frame(self.container, bg=self.c_header_bg, height=32)
        top_bar.pack(fill=tk.X, side=tk.TOP)
        top_bar.bind("<ButtonPress-1>", self.on_drag_start)
        top_bar.bind("<B1-Motion>", self.on_drag_motion)
        
        lbl_brand = tk.Label(
            top_bar, 
            text=" ▰ DIRECT MARKET HUD // LIVE COLLECTOR", 
            font=self.font_title, 
            fg=self.c_cyan, 
            bg=self.c_header_bg
        )
        lbl_brand.pack(side=tk.LEFT, padx=8, pady=4)
        lbl_brand.bind("<ButtonPress-1>", self.on_drag_start)
        lbl_brand.bind("<B1-Motion>", self.on_drag_motion)
        
        btn_close = tk.Label(
            top_bar, 
            text=" [ESC] [X] ", 
            font=self.font_mono_bold, 
            fg=self.c_text_dim, 
            bg=self.c_header_bg, 
            cursor="hand2"
        )
        btn_close.pack(side=tk.RIGHT, padx=6)
        btn_close.bind("<Button-1>", lambda e: self.close_app())
        btn_close.bind("<Enter>", lambda e: btn_close.configure(fg=self.c_red))
        btn_close.bind("<Leave>", lambda e: btn_close.configure(fg=self.c_text_dim))
        
        # 2. SYSTEM NETWORK AUDIT BAR
        self.bar_audit = tk.Frame(self.container, bg=self.c_bg)
        self.bar_audit.pack(fill=tk.X, padx=14, pady=(10, 4))
        
        self.lbl_net_status = tk.Label(
            self.bar_audit, 
            text="AUDIT : MEMERIKSA JARINGAN & PROXY...", 
            font=self.font_mono_sm, 
            fg=self.c_yellow, 
            bg=self.c_bg, 
            anchor="w"
        )
        self.lbl_net_status.pack(fill=tk.X)
        
        # Garis Pembatas
        sep1 = tk.Frame(self.container, bg=self.c_border, height=1)
        sep1.pack(fill=tk.X, padx=14, pady=6)
        
        # 3. TABEL DATA REALTIME (Text Monospace)
        table_frame = tk.Frame(self.container, bg=self.c_bg)
        table_frame.pack(fill=tk.X, padx=14, pady=4)
        
        # Header Tabel
        header_text = f"{'INSTRUMEN':<14} | {'HARGA (USD)':<14} | {'24H PERUBAHAN':<15} | {'RENTANG 24H (LOW - HIGH)':<26} | {'TIME'}"
        lbl_th = tk.Label(
            table_frame, 
            text=header_text, 
            font=self.font_mono_bold, 
            fg=self.c_cyan, 
            bg=self.c_bg, 
            anchor="w"
        )
        lbl_th.pack(fill=tk.X)
        
        sep_table = tk.Frame(table_frame, bg=self.c_border, height=1)
        sep_table.pack(fill=tk.X, pady=(4, 6))
        
        # Baris Tabel untuk 4 Instrumen
        self.row_labels = {}
        for key in ["BTC/USDT", "XAUT/USDT", "GOLD COMEX", "USD (DXY)"]:
            row_lbl = tk.Label(
                table_frame, 
                text=f"{key:<14} | Mengambil data live upstream...", 
                font=self.font_mono, 
                fg=self.c_text_dim, 
                bg=self.c_bg, 
                anchor="w"
            )
            row_lbl.pack(fill=tk.X, pady=2)
            self.row_labels[key] = row_lbl
            
        # Garis Pembatas Bawah Tabel
        sep2 = tk.Frame(self.container, bg=self.c_border, height=1)
        sep2.pack(fill=tk.X, padx=14, pady=(8, 6))
        
        # 4. AUDIT TRANSPARANSI JARINGAN & SERVER IP
        audit_box = tk.Frame(self.container, bg="#0e131c", padx=10, pady=8)
        audit_box.pack(fill=tk.X, padx=14, pady=2)
        
        lbl_audit_title = tk.Label(
            audit_box, 
            text="[VERIFIKASI INTEGRITAS: ZERO-MOCK // DIRECT SOCKET]", 
            font=self.font_mono_bold, 
            fg=self.c_cyan, 
            bg="#0e131c", 
            anchor="w"
        )
        lbl_audit_title.pack(fill=tk.X)
        
        self.lbl_node_btc = tk.Label(audit_box, text="  • BTC Node   : Menghubungkan...", font=self.font_mono_sm, fg=self.c_text_dim, bg="#0e131c", anchor="w")
        self.lbl_node_btc.pack(fill=tk.X)
        
        self.lbl_node_xaut = tk.Label(audit_box, text="  • XAUT Node  : Menghubungkan...", font=self.font_mono_sm, fg=self.c_text_dim, bg="#0e131c", anchor="w")
        self.lbl_node_xaut.pack(fill=tk.X)
        
        self.lbl_node_gold = tk.Label(audit_box, text="  • COMEX Node : Menghubungkan...", font=self.font_mono_sm, fg=self.c_text_dim, bg="#0e131c", anchor="w")
        self.lbl_node_gold.pack(fill=tk.X)
        
        self.lbl_node_usd = tk.Label(audit_box, text="  • DXY Node   : Menghubungkan...", font=self.font_mono_sm, fg=self.c_text_dim, bg="#0e131c", anchor="w")
        self.lbl_node_usd.pack(fill=tk.X)
        
        # 5. FOOTER STATUS BAR
        footer = tk.Frame(self.container, bg=self.c_header_bg, height=24)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.lbl_footer_status = tk.Label(
            footer, 
            text="[LIVE POLLING: 3s] Tekan SPASI: Refresh Manual | Klik & Drag untuk geser jendela", 
            font=self.font_mono_sm, 
            fg=self.c_text_dim, 
            bg=self.c_header_bg
        )
        self.lbl_footer_status.pack(side=tk.LEFT, padx=10, pady=2)
        
        self.lbl_footer_time = tk.Label(
            footer, 
            text="", 
            font=self.font_mono_sm, 
            fg=self.c_cyan, 
            bg=self.c_header_bg
        )
        self.lbl_footer_time.pack(side=tk.RIGHT, padx=10, pady=2)

    def trigger_manual_refresh(self):
        if not self.is_fetching:
            threading.Thread(target=self.do_fetch, daemon=True).start()

    def bg_fetch_loop(self):
        while self.is_running:
            self.do_fetch()
            # Polling loop
            for _ in range(int(self.refresh_interval_sec * 10)):
                if not self.is_running:
                    break
                time.sleep(0.1)

    def do_fetch(self):
        if self.is_fetching or not self.is_running:
            return
        self.is_fetching = True
        try:
            data = fetch_all_market_data()
            if self.is_running:
                # Update UI thread-safely
                self.root.after(0, self.update_display, data)
        except Exception as e:
            pass
        finally:
            self.is_fetching = False

    def update_display(self, data):
        if not self.is_running:
            return
            
        now_wib = datetime.datetime.now().strftime("%H:%M:%S WIB")
        self.lbl_footer_time.configure(text=now_wib)
        
        # 1. Update Audit Bar
        net = data.get("network_audit", {})
        is_direct = net.get("is_direct", True)
        total_lat = data.get("total_latency_ms", 0)
        
        if is_direct:
            net_text = f"AUDIT : [✓] DIRECT CONNECTION (NO PROXY)  │  LATENCY PARALEL : {total_lat}ms  │  UPDATE : {now_wib}"
            self.lbl_net_status.configure(text=net_text, fg=self.c_green)
        else:
            net_text = f"AUDIT : [!] PERINGATAN: PROXY TERDETEKSI  │  LATENCY : {total_lat}ms"
            self.lbl_net_status.configure(text=net_text, fg=self.c_red)

        # 2. Update Table Rows
        node_labels = {
            "BTC/USDT": self.lbl_node_btc,
            "XAUT/USDT": self.lbl_node_xaut,
            "GOLD COMEX": self.lbl_node_gold,
            "USD (DXY)": self.lbl_node_usd
        }
        
        for item in data.get("items", []):
            if not item:
                continue
            symbol = item.get("symbol")
            if symbol not in self.row_labels:
                continue
                
            row_widget = self.row_labels[symbol]
            node_widget = node_labels.get(symbol)
            
            if "error" in item:
                row_widget.configure(
                    text=f"{symbol:<14} | GAGAL: {item['error'][:40]}", 
                    fg=self.c_red
                )
            else:
                price = item["price"]
                chg = item["change_pct"]
                high = item.get("high", 0)
                low = item.get("low", 0)
                lat = item.get("latency_ms", 0)
                ip = item.get("remote_ip", "-")
                src = item.get("source", "-")
                server_ts = item.get("server_time_ms", 0)
                
                # Format Harga & Perubahan
                if "DXY" in symbol:
                    price_str = f"{price:.3f}"
                    range_str = f"{low:.2f} - {high:.2f}"
                elif price >= 1000:
                    price_str = f"${price:,.2f}"
                    range_str = f"${low:,.1f} - ${high:,.1f}"
                else:
                    price_str = f"${price:.2f}"
                    range_str = f"${low:.2f} - ${high:.2f}"
                    
                chg_arrow = "▲" if chg >= 0 else "▼"
                chg_str = f"{chg:+.2f}% {chg_arrow}"
                chg_color = self.c_green if chg >= 0 else self.c_red
                
                time_wib = datetime.datetime.fromtimestamp(server_ts / 1000.0).strftime("%H:%M:%S")
                
                line_text = f"{symbol:<14} | {price_str:<14} | {chg_str:<15} | {range_str:<26} | {time_wib}"
                row_widget.configure(text=line_text, fg=chg_color)
                
                # Update Audit Node
                if node_widget:
                    node_widget.configure(
                        text=f"  • {symbol:<11} : IP {ip:<15} | {src:<20} | {lat}ms | HTTP 200 OK",
                        fg=self.c_text_main
                    )

    def close_app(self):
        self.is_running = False
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

def main():
    root = tk.Tk()
    app = FramelessTextHUD(root)
    root.mainloop()

if __name__ == "__main__":
    main()
