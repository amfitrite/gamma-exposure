"""
MT5 TCP Socket Stream Listener (Smart Multi-Port Auto-Bind).
Priority Port: 5556 (with fallback to 5555 / 5557 if 5556 is in use by another app).
Receives real-time tick streaming directly from multi port bridge EA.mq5.
Thread-safe, non-blocking with auto-reconnect handling.
"""

import socket
import threading
import time
import datetime

class MT5StreamListener:
    def __init__(self, host="127.0.0.1", port=5556, fallback_ports=(5555, 5557)):
        self.host = host
        self.preferred_port = port
        self.fallback_ports = fallback_ports
        self.bound_port = None
        self.is_running = False
        self.server_sock = None
        self.client_sock = None
        self.thread = None
        
        # State Data
        self.lock = threading.Lock()
        self.is_client_connected = False
        self.client_addr = None
        self.symbol = "XAUUSD"
        self.digits = 2
        self.tick_size = 0.01
        
        # Latest Live Tick Data
        self.last_tick = {
            "bid": 0.0,
            "ask": 0.0,
            "last": 0.0,
            "spread": 0.0,
            "vol": 0.0,
            "flags": 0,
            "time_msc": 0,
            "received_at": 0.0,
            "count": 0
        }

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False
        if self.client_sock:
            try:
                self.client_sock.close()
            except Exception:
                pass
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass

    def _run_server(self):
        # Coba bind ke preferred_port (5556), jika dipakai app lain (misal TickMap), coba 5555
        ports_to_try = [self.preferred_port] + [p for p in self.fallback_ports if p != self.preferred_port]
        
        for p in ports_to_try:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((self.host, p))
                s.listen(1)
                s.settimeout(1.0)
                self.server_sock = s
                self.bound_port = p
                print(f"[MT5 Listener] Berhasil terikat pada Port TCP {p}")
                break
            except Exception as e:
                # Port sedang digunakan app lain
                continue

        if not self.server_sock:
            print(f"[MT5 Listener] Gagal bind ke semua port {ports_to_try}")
            return

        while self.is_running:
            try:
                client, addr = self.server_sock.accept()
                self.client_sock = client
                self.client_addr = addr
                with self.lock:
                    self.is_client_connected = True
                self._handle_client(client)
            except socket.timeout:
                continue
            except Exception:
                if not self.is_running:
                    break
                time.sleep(0.5)

    def _handle_client(self, client):
        client.settimeout(2.0)
        buffer = ""
        while self.is_running:
            try:
                data = client.recv(4096)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="ignore")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        self._parse_line(line)
            except socket.timeout:
                continue
            except Exception:
                break

        with self.lock:
            self.is_client_connected = False
        try:
            client.close()
        except Exception:
            pass

    def _parse_line(self, line):
        # 1. Parse Metadata / Handshake
        if line.startswith("#SYMBOL:"):
            with self.lock:
                self.symbol = line.split(":", 1)[1].strip()
            return
        if line.startswith("#META:"):
            # Format: #META:Symbol,Digits,Point,TickSize,ContractSize
            parts = line[6:].split(",")
            if len(parts) >= 4:
                with self.lock:
                    self.symbol = parts[0]
                    try:
                        self.digits = int(parts[1])
                        self.tick_size = float(parts[3])
                    except ValueError:
                        pass
            return
        if line.startswith("#HIST"):
            return

        # 2. Parse Tick Data: time_msc,bid,ask,last,vol,flags
        parts = line.split(",")
        if len(parts) >= 6:
            try:
                t_msc = int(parts[0])
                bid = float(parts[1])
                ask = float(parts[2])
                last = float(parts[3])
                vol = float(parts[4])
                flags = int(parts[5])
                spread = ask - bid if ask >= bid else 0.0

                with self.lock:
                    self.last_tick["bid"] = bid
                    self.last_tick["ask"] = ask
                    self.last_tick["last"] = last if last > 0 else (bid + ask) / 2.0
                    self.last_tick["spread"] = spread
                    self.last_tick["vol"] = vol
                    self.last_tick["flags"] = flags
                    self.last_tick["time_msc"] = t_msc
                    self.last_tick["received_at"] = time.time()
                    self.last_tick["count"] += 1
            except Exception:
                pass

    def get_status(self):
        """Ambil snapshot terkini status stream MT5 secara aman."""
        with self.lock:
            tick_copy = dict(self.last_tick)
            is_conn = self.is_client_connected
            sym = self.symbol
            dig = self.digits
            bp = self.bound_port or self.preferred_port
            
        return {
            "bound_port": bp,
            "is_connected": is_conn,
            "symbol": sym,
            "digits": dig,
            "tick": tick_copy
        }
