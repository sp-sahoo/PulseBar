
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
import ipaddress
import urllib.request

import psutil

if sys.platform == "win32":
    import ctypes


APP_NAME = "PulseBar"

HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010


def get_app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_launch_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{os.path.abspath(sys.executable)}"'

    exe = sys.executable

    if sys.platform == "win32" and exe.lower().endswith("python.exe"):
        pythonw = exe[:-10] + "pythonw.exe"
        if os.path.exists(pythonw):
            exe = pythonw

    script = os.path.abspath(__file__)
    return f'"{exe}" "{script}"'


BASE_DIR = get_app_dir()
CONFIG_PATH = os.path.join(BASE_DIR, "settings.json")


def load_config():
    defaults = {
        "start_with_windows": False,
    }

    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                defaults.update({
                    k: v for k, v in data.items()
                    if k in defaults
                })
        except Exception:
            pass

    return defaults


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


def set_windows_startup(enable: bool):
    if sys.platform != "win32":
        return

    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        cmd = get_launch_command()

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_SET_VALUE
        ) as key:

            if enable:
                winreg.SetValueEx(
                    key, APP_NAME, 0, winreg.REG_SZ, cmd
                )
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass

    except Exception:
        pass


def format_speed(bps: float) -> str:
    if bps < 1024:
        return f"{int(bps)} B/s"

    kb = bps / 1024.0

    if kb < 1024:
        return f"{int(round(kb))} KB/s"

    mb = kb / 1024.0

    if mb < 100:
        return f"{mb:.1f} MB/s"

    return f"{int(round(mb))} MB/s"


# Get the actual PUBLIC IP address
def get_public_ip() -> str:
    try:
        request = urllib.request.Request(
            "https://api64.ipify.org",
            headers={"User-Agent": "PulseBar/1.0"}
        )

        with urllib.request.urlopen(request, timeout=5) as response:
            ip = response.read(64).decode("utf-8").strip()

        # Validate that the response is actually an IP address
        return str(ipaddress.ip_address(ip))

    except Exception:
        return "Unavailable"


def measure_ping_ms(host="1.1.1.1") -> str:
    try:
        startupinfo = None

        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        res = subprocess.run(
            ["ping", "-n", "1", "-w", "900", host],
            capture_output=True,
            text=True,
            timeout=1.6,
            startupinfo=startupinfo,
        )

        match = re.search(
            r"time[=<]\s*(\d+)\s*ms",
            res.stdout,
            re.IGNORECASE
        )

        if match:
            return f"{match.group(1)}ms"

        if "TTL=" in res.stdout:
            return "<1ms"

        return "--"

    except Exception:
        return "--"


def round_rect_points(x1, y1, x2, y2, r=12):
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)

    return [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]


class SpeedMeter:

    # Slightly wider widget for better spacing
    W = 280
    H = 54

    def __init__(self):

        self.cfg = load_config()

        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        self.trans_key = "#010203"

        self.root.configure(bg=self.trans_key)

        if sys.platform == "win32":
            self.root.wm_attributes(
                "-transparentcolor",
                self.trans_key
            )

        self.canvas = tk.Canvas(
            self.root,
            width=self.W,
            height=self.H,
            bg=self.trans_key,
            highlightthickness=0,
            bd=0,
        )

        self.canvas.pack()

        self._draw_ui()
        self._center_window()
        self._bind_events()

        self.prev_io = psutil.net_io_counters()
        self.last_time = time.monotonic()

        self.ping_text = "--"
        self.ip_text = "Checking..."

        self._start_bg_workers()
        self._poll_speeds()

    def _draw_arrow_glyph(self, x, y, symbol, color):

        self.canvas.create_text(
            x + 0.6,
            y,
            text=symbol,
            fill=color,
            font=("Segoe UI", 10, "bold"),
            anchor="w"
        )

        self.canvas.create_text(
            x,
            y,
            text=symbol,
            fill=color,
            font=("Segoe UI", 10, "bold"),
            anchor="w"
        )

    def _draw_ui(self):

        # Main background
        self.canvas.create_polygon(
            round_rect_points(
                1, 1, self.W - 1, self.H - 1, r=12
            ),
            smooth=True,
            fill="#1C1C1C",
            outline="#2E2E2E",
            width=1,
        )

        # Upload speed
        self._draw_arrow_glyph(
            12, 19, "↑", "#5B9BFF"
        )

        self.up_id = self.canvas.create_text(
            24,
            19,
            text="0 B/s",
            fill="#EAECEF",
            font=("Segoe UI", 9, "bold"),
            anchor="w"
        )

        # Download speed
        # Moved slightly further away from upload
        self._draw_arrow_glyph(
            108, 19, "↓", "#2ECC71"
        )

        self.down_id = self.canvas.create_text(
            120,
            19,
            text="0 B/s",
            fill="#EAECEF",
            font=("Segoe UI", 9, "bold"),
            anchor="w"
        )

        # Ping pill
        pill_x1 = 224
        pill_y1 = 9
        pill_x2 = self.W - 9
        pill_y2 = 29

        self.canvas.create_polygon(
            round_rect_points(
                pill_x1,
                pill_y1,
                pill_x2,
                pill_y2,
                r=8
            ),
            smooth=True,
            fill="#282828",
            outline="#383838",
            width=1,
        )

        self.ping_id = self.canvas.create_text(
            (pill_x1 + pill_x2) / 2,
            (pill_y1 + pill_y2) / 2,
            text="--",
            fill="#E2E5EA",
            font=("Segoe UI", 9, "bold"),
            anchor="center",
        )

        # Public IP address
        self.ip_id = self.canvas.create_text(
            13,
            42,
            text="IP: Checking...",
            fill="#8E939E",
            font=("Segoe UI", 8),
            anchor="w"
        )

    def _keep_on_top(self):

        try:
            self.root.attributes("-topmost", True)

            if sys.platform == "win32":

                hwnd = (
                    ctypes.windll.user32.GetParent(
                        self.root.winfo_id()
                    )
                    or self.root.winfo_id()
                )

                ctypes.windll.user32.SetWindowPos(
                    hwnd,
                    HWND_TOPMOST,
                    0, 0, 0, 0,
                    SWP_NOSIZE |
                    SWP_NOMOVE |
                    SWP_NOACTIVATE
                )

        except Exception:
            pass

    def _center_window(self):

        self.root.update_idletasks()

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()

        x = (sw - self.W) // 2
        y = (sh - self.H) // 2

        self.root.geometry(
            f"{self.W}x{self.H}+{x}+{y}"
        )

        self._keep_on_top()

    def _bind_events(self):

        self._drag_ox = 0
        self._drag_oy = 0

        def on_press(event):

            self._drag_ox = event.x
            self._drag_oy = event.y

            self._keep_on_top()

        def on_drag(event):

            nx = (
                self.root.winfo_x()
                + (event.x - self._drag_ox)
            )

            ny = (
                self.root.winfo_y()
                + (event.y - self._drag_oy)
            )

            self.root.geometry(f"+{nx}+{ny}")

        def on_release(event):
            self._keep_on_top()

        self.canvas.bind(
            "<ButtonPress-1>", on_press
        )

        self.canvas.bind(
            "<B1-Motion>", on_drag
        )

        self.canvas.bind(
            "<ButtonRelease-1>", on_release
        )

        self.canvas.bind(
            "<Button-3>", self._show_menu
        )

        self.root.bind(
            "<FocusOut>",
            lambda e: self.root.after(
                150, self._keep_on_top
            )
        )

    def _show_menu(self, event):

        menu = tk.Menu(
            self.root,
            tearoff=0,
            bg="#242424",
            fg="#EAECEF",
            bd=0
        )

        st_var = tk.BooleanVar(
            value=bool(
                self.cfg.get("start_with_windows", False)
            )
        )

        def toggle_startup():

            val = st_var.get()

            self.cfg["start_with_windows"] = val

            save_config(self.cfg)
            set_windows_startup(val)

        menu.add_checkbutton(
            label="Start with Windows",
            variable=st_var,
            command=toggle_startup
        )

        menu.add_separator()

        menu.add_command(
            label="Center Widget",
            command=self._center_window
        )

        menu.add_command(
            label="Quit",
            command=self._quit
        )

        try:
            menu.tk_popup(
                event.x_root,
                event.y_root
            )

        finally:
            menu.grab_release()

            self.root.after(
                150, self._keep_on_top
            )

    def _start_bg_workers(self):

        def ping_and_ip_loop():

            last_ip_check = 0

            while True:

                # Update ping
                p = measure_ping_ms("1.1.1.1")

                self.ping_text = p

                # Public IP lookup every 30 seconds
                # This avoids unnecessary repeated API requests
                now = time.monotonic()

                if now - last_ip_check >= 30:

                    ip = get_public_ip()

                    self.ip_text = ip

                    last_ip_check = now

                time.sleep(2.5)

        threading.Thread(
            target=ping_and_ip_loop,
            daemon=True
        ).start()

    def _poll_speeds(self):

        now = time.monotonic()

        elapsed = max(
            now - self.last_time,
            0.05
        )

        cur_io = psutil.net_io_counters()

        tx_bps = max(
            0.0,
            (
                cur_io.bytes_sent
                - self.prev_io.bytes_sent
            ) / elapsed
        )

        rx_bps = max(
            0.0,
            (
                cur_io.bytes_recv
                - self.prev_io.bytes_recv
            ) / elapsed
        )

        self.prev_io = cur_io
        self.last_time = now

        self.canvas.itemconfigure(
            self.up_id,
            text=format_speed(tx_bps)
        )

        self.canvas.itemconfigure(
            self.down_id,
            text=format_speed(rx_bps)
        )

        self.canvas.itemconfigure(
            self.ping_id,
            text=self.ping_text
        )

        self.canvas.itemconfigure(
            self.ip_id,
            text=f"IP: {self.ip_text}"
        )

        self._keep_on_top()

        self.root.after(
            1000,
            self._poll_speeds
        )

    def _quit(self):

        save_config(self.cfg)

        self.root.destroy()

        sys.exit(0)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    SpeedMeter().run()
