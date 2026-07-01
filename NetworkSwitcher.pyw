import os
import json
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import psutil
import subprocess
import ctypes
import sys
import time
import threading
from PIL import Image, ImageDraw
import pystray

# === 配置全局化现代主题 ===
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yyy_config.json')

def is_admin():
    """检查是否拥有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

class FloatingWidget:
    """现代版桌面透明悬浮胶囊组件"""
    def __init__(self, root, app_controller):
        self.app = app_controller
        self.win = ctk.CTkToplevel(root)
        self.win.overrideredirect(True)
        
        start_x = self.app.config.get("x", 100)
        start_y = self.app.config.get("y", 100)
        self.win.geometry(f"165x46+{start_x}+{start_y}")
        
        is_topmost = self.app.config.get("topmost_widget", "on") == "on"
        self.win.attributes('-topmost', is_topmost)
        
        if sys.platform.startswith("win"):
            transparent_color = "#000001" 
            self.win.attributes("-transparentcolor", transparent_color)
            self.win.configure(fg_color=transparent_color)
            self.win.attributes("-toolwindow", True)
        
        self.is_locked = False
        self._updating_visually = False
        
        self.frame = ctk.CTkFrame(self.win, corner_radius=23, fg_color="#2b2b2b", border_width=1, border_color="#444444")
        self.frame.pack(fill="both", expand=True)
        
        self.setup_ui()
        
        self.frame.bind("<ButtonPress-1>", self.start_move)
        self.frame.bind("<ButtonRelease-1>", self.stop_move)
        self.frame.bind("<B1-Motion>", self.do_move)
        self.lbl_status.bind("<ButtonPress-1>", self.start_move)
        self.lbl_status.bind("<ButtonRelease-1>", self.stop_move)
        self.lbl_status.bind("<B1-Motion>", self.do_move)
        
        self.win.withdraw()

    def setup_ui(self):
        self.lbl_status = ctk.CTkLabel(self.frame, text="普通模式", text_color="#a0a0a0", font=("Microsoft YaHei", 12, "bold"))
        self.lbl_status.pack(side="left", padx=(15, 0))

        self.switch_var = ctk.StringVar(value="off")
        self.switch = ctk.CTkSwitch(
            self.frame, text="", variable=self.switch_var, onvalue="on", offvalue="off",
            command=self.on_switch_toggle,
            progress_color="#ef5350", 
            button_color="#ffffff",
            width=40
        )
        self.switch.pack(side="right", padx=(0, 10))

    def start_move(self, event):
        if self.is_locked: return
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        if self.is_locked: return
        self.x = None
        self.y = None
        self.app.config["x"] = self.win.winfo_x()
        self.app.config["y"] = self.win.winfo_y()
        self.app.save_config()

    def do_move(self, event):
        if self.is_locked: return
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.win.winfo_x() + deltax
        y = self.win.winfo_y() + deltay
        self.win.geometry(f"+{x}+{y}")

    def on_switch_toggle(self):
        if self._updating_visually: 
            return 
            
        if self.switch_var.get() == "on":
            self.app.set_game_mode(silent=True)
        else:
            self.app.set_normal_mode(silent=True)

    def set_visual_state(self, is_game_mode):
        self._updating_visually = True 
        
        if is_game_mode:
            self.switch_var.set("on")
            self.lbl_status.configure(text="游戏模式", text_color="#ff5252")
            self.frame.configure(border_color="#ff5252")
        else:
            self.switch_var.set("off")
            self.lbl_status.configure(text="普通模式", text_color="#a0a0a0")
            self.frame.configure(border_color="#444444")
            
        self._updating_visually = False 


class NetworkSwitcherApp(ctk.CTk):
    """现代版主控制台"""
    def __init__(self):
        super().__init__()
        
        self.title("YYY Network 智能分流系统")
        self.geometry("500x600")
        self.resizable(False, False)
        
        # === 核心修复：强制注入窗口与任务栏图标 ===
        icon_path = os.path.join(os.path.dirname(ctk.__file__), "assets", "icons", "CustomTkinter_icon_Windows.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        
        self.protocol('WM_DELETE_WINDOW', self.hide_window)
        
        self.interfaces = list(psutil.net_if_addrs().keys())
        self.last_net_io = psutil.net_io_counters(pernic=True)
        self.last_time = time.time()
        
        self.config = self.load_config()
        
        self.setup_tray_icon()
        self.floating_widget = FloatingWidget(self, self)
        
        self.setup_ui()
        self.update_traffic_stats()
        
        self.show_widget_var.set(self.config.get("show_widget", "on"))
        self.lock_widget_var.set(self.config.get("lock_widget", "off"))
        self.topmost_widget_var.set(self.config.get("topmost_widget", "on"))
        self.toggle_floating_widget()
        self.toggle_widget_lock()
        
        if self.config.get("is_game_mode", False):
            self.after(100, lambda: self.set_game_mode(silent=True))
        else:
            self.after(100, lambda: self.set_normal_mode(silent=True))

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {"x": 100, "y": 100, "is_game_mode": False, "show_widget": "on", "lock_widget": "off", "topmost_widget": "on"}

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f)
        except:
            pass

    def setup_ui(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=15)

        header_font = ("Microsoft YaHei", 14, "bold")
        header_color = "#e0e0e0"

        frame_select = ctk.CTkFrame(main_frame, corner_radius=10)
        frame_select.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(frame_select, text="网络接口配置", font=header_font, text_color=header_color).pack(anchor="w", padx=15, pady=(10, 5))

        grid_frame = ctk.CTkFrame(frame_select, fg_color="transparent")
        grid_frame.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(grid_frame, text="无线网络 (Wi-Fi):").grid(row=0, column=0, sticky="w", pady=5)
        self.combo_wifi = ctk.CTkOptionMenu(grid_frame, values=self.interfaces if self.interfaces else ["未找到网卡"], width=220)
        self.combo_wifi.grid(row=0, column=1, padx=(20, 0), pady=5)
        self.auto_select_interface(self.combo_wifi, ["WLAN", "Wi-Fi", "无线网络连接"])

        ctk.CTkLabel(grid_frame, text="有线网络 (Ethernet):").grid(row=1, column=0, sticky="w", pady=5)
        self.combo_eth = ctk.CTkOptionMenu(grid_frame, values=self.interfaces if self.interfaces else ["未找到网卡"], width=220)
        self.combo_eth.grid(row=1, column=1, padx=(20, 0), pady=5)
        self.auto_select_interface(self.combo_eth, ["以太网", "Ethernet", "本地连接"])

        frame_mode = ctk.CTkFrame(main_frame, corner_radius=10)
        frame_mode.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(frame_mode, text="模式切换与状态", font=header_font, text_color=header_color).pack(anchor="w", padx=15, pady=(10, 0))

        self.lbl_main_status = ctk.CTkLabel(frame_mode, text="当前状态：🌐 普通模式 (有线优先)", font=("Microsoft YaHei", 13, "bold"), text_color="#a0a0a0")
        self.lbl_main_status.pack(pady=(5, 10))

        button_frame = ctk.CTkFrame(frame_mode, fg_color="transparent")
        button_frame.pack(fill="x", padx=15, pady=(0, 15))

        btn_game = ctk.CTkButton(button_frame, text="🎮 开启游戏模式\n(优先走热点)", 
                                 fg_color="#d32f2f", hover_color="#b71c1c", height=45,
                                 font=("Microsoft YaHei", 12, "bold"), command=self.set_game_mode)
        btn_game.pack(side="left", expand=True, fill="x", padx=(0, 10))

        btn_normal = ctk.CTkButton(button_frame, text="🌐 恢复普通模式\n(优先走有线)", 
                                   fg_color="#2e7d32", hover_color="#1b5e20", height=45,
                                   font=("Microsoft YaHei", 12, "bold"), command=self.set_normal_mode)
        btn_normal.pack(side="right", expand=True, fill="x", padx=(10, 0))

        frame_monitor = ctk.CTkFrame(main_frame, corner_radius=10)
        frame_monitor.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(frame_monitor, text="实时网卡吞吐量监控", font=header_font, text_color=header_color).pack(anchor="w", padx=15, pady=(10, 5))

        self.lbl_wifi_speed = ctk.CTkLabel(frame_monitor, text="📶 正在初始化数据...", font=("Consolas", 13))
        self.lbl_wifi_speed.pack(anchor="w", padx=15, pady=(5, 2))

        self.lbl_eth_speed = ctk.CTkLabel(frame_monitor, text="🔌 正在初始化数据...", font=("Consolas", 13))
        self.lbl_eth_speed.pack(anchor="w", padx=15, pady=(2, 15))

        frame_widget = ctk.CTkFrame(main_frame, corner_radius=10)
        frame_widget.pack(fill="x", pady=(0, 0))
        
        ctk.CTkLabel(frame_widget, text="桌面悬浮窗设置", font=header_font, text_color=header_color).pack(anchor="w", padx=15, pady=(10, 0))
        
        self.show_widget_var = ctk.StringVar(value="on")
        self.lock_widget_var = ctk.StringVar(value="off")
        self.topmost_widget_var = ctk.StringVar(value="on")
        
        switch_frame = ctk.CTkFrame(frame_widget, fg_color="transparent")
        switch_frame.pack(fill="x", padx=15, pady=(5, 15))
        
        switch_frame.columnconfigure(0, weight=1)
        switch_frame.columnconfigure(1, weight=1)
        
        chk_show = ctk.CTkSwitch(switch_frame, text="启用悬浮快捷开关", variable=self.show_widget_var, onvalue="on", offvalue="off", command=self.toggle_floating_widget)
        chk_show.grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        chk_lock = ctk.CTkSwitch(switch_frame, text="锁定悬浮窗位置", variable=self.lock_widget_var, onvalue="on", offvalue="off", command=self.toggle_widget_lock)
        chk_lock.grid(row=0, column=1, sticky="w", pady=(0, 10))

        chk_topmost = ctk.CTkSwitch(switch_frame, text="悬浮窗总在最前", variable=self.topmost_widget_var, onvalue="on", offvalue="off", command=self.toggle_widget_topmost)
        chk_topmost.grid(row=1, column=0, sticky="w")

    def auto_select_interface(self, combobox, keywords):
        for iface in self.interfaces:
            for kw in keywords:
                if kw.lower() in iface.lower():
                    combobox.set(iface)
                    return
        if self.interfaces:
            combobox.set(self.interfaces[0])

    def set_metric(self, interface_name, metric_value):
        try:
            cmd = f'netsh interface ipv4 set interface "{interface_name}" metric={metric_value}'
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except:
            return False

    def sync_main_status(self, is_game_mode):
        if is_game_mode:
            self.lbl_main_status.configure(text="当前状态：🎮 游戏模式 (热点优先)", text_color="#ff5252")
        else:
            self.lbl_main_status.configure(text="当前状态：🌐 普通模式 (有线优先)", text_color="#a0a0a0")

    def set_game_mode(self, silent=False):
        wifi = self.combo_wifi.get()
        eth = self.combo_eth.get()
        
        if self.set_metric(wifi, 10) and self.set_metric(eth, 50):
            self.floating_widget.set_visual_state(True) 
            self.sync_main_status(True)
            self.config["is_game_mode"] = True
            self.save_config()
            if not silent: messagebox.showinfo("成功", "【游戏模式】已开启！\n\n新连接已切换至 Wi-Fi 热点。")
        else:
            self.floating_widget.set_visual_state(False) 
            self.sync_main_status(False)
            if not silent: messagebox.showerror("权限错误", "设置失败！请确保以管理员身份运行。")

    def set_normal_mode(self, silent=False):
        wifi = self.combo_wifi.get()
        eth = self.combo_eth.get()
            
        if self.set_metric(eth, 10) and self.set_metric(wifi, 50):
            self.floating_widget.set_visual_state(False) 
            self.sync_main_status(False)
            self.config["is_game_mode"] = False
            self.save_config()
            if not silent: messagebox.showinfo("成功", "【普通模式】已恢复！\n\n网络已切回有线优先。")
        else:
            self.floating_widget.set_visual_state(True) 
            self.sync_main_status(True)
            if not silent: messagebox.showerror("权限错误", "设置失败！请确保以管理员身份运行。")

    def toggle_floating_widget(self):
        if self.show_widget_var.get() == "on":
            self.floating_widget.win.deiconify()
        else:
            self.floating_widget.win.withdraw()
        self.config["show_widget"] = self.show_widget_var.get()
        self.save_config()

    def toggle_widget_lock(self):
        self.floating_widget.is_locked = (self.lock_widget_var.get() == "on")
        self.config["lock_widget"] = self.lock_widget_var.get()
        self.save_config()

    def toggle_widget_topmost(self):
        is_top = (self.topmost_widget_var.get() == "on")
        self.floating_widget.win.attributes('-topmost', is_top)
        self.config["topmost_widget"] = self.topmost_widget_var.get()
        self.save_config()

    def format_speed(self, bytes_per_sec):
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:6.1f} B/s "
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:6.1f} KB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024):6.1f} MB/s"

    def update_traffic_stats(self):
        try:
            current_net_io = psutil.net_io_counters(pernic=True)
            current_time = time.time()
            time_diff = current_time - self.last_time

            wifi = self.combo_wifi.get()
            eth = self.combo_eth.get()

            if wifi in current_net_io and wifi in self.last_net_io:
                tx = (current_net_io[wifi].bytes_sent - self.last_net_io[wifi].bytes_sent) / time_diff
                rx = (current_net_io[wifi].bytes_recv - self.last_net_io[wifi].bytes_recv) / time_diff
                self.lbl_wifi_speed.configure(text=f"📶 {wifi[:10]:<10}... | ↓ {self.format_speed(rx):<10} | ↑ {self.format_speed(tx):<10}")

            if eth in current_net_io and eth in self.last_net_io:
                tx = (current_net_io[eth].bytes_sent - self.last_net_io[eth].bytes_sent) / time_diff
                rx = (current_net_io[eth].bytes_recv - self.last_net_io[eth].bytes_recv) / time_diff
                self.lbl_eth_speed.configure(text=f"🔌 {eth[:10]:<10}... | ↓ {self.format_speed(rx):<10} | ↑ {self.format_speed(tx):<10}")

            self.last_net_io = current_net_io
            self.last_time = current_time
        except:
            pass
            
        self.after(1000, self.update_traffic_stats)

    def get_unified_icon(self):
        icon_path = os.path.join(os.path.dirname(ctk.__file__), "assets", "icons", "CustomTkinter_icon_Windows.ico")
        if os.path.exists(icon_path):
            try:
                return Image.open(icon_path)
            except:
                pass
        image = Image.new('RGB', (64, 64), color=(31, 83, 141))
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 20, 44, 44), fill=(255, 255, 255))
        return image

    def setup_tray_icon(self):
        menu = pystray.Menu(
            pystray.MenuItem('打开主控制台', self.show_window, default=True),
            pystray.MenuItem('完全退出', self.quit_app)
        )
        self.tray_icon = pystray.Icon("NetSwitcher", self.get_unified_icon(), "YYY 分流系统", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def hide_window(self):
        self.withdraw()

    def show_window(self, icon, item):
        self.after(0, self.deiconify)

    def quit_app(self, icon, item):
        self.tray_icon.stop()
        self.after(0, self.destroy)

if __name__ == "__main__":
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
        
    # === 核心修复：强制向 Windows 宣告这是一个独立的 App，不再使用 Python 图标合并任务栏 ===
    try:
        myappid = 'yyy.network.switcher.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass
        
    app = NetworkSwitcherApp()
    app.mainloop()