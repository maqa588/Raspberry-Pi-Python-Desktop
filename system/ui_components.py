# system/ui_components.py
import tkinter as tk
import time

from system.config import CANVAS_WIDTH, CANVAS_HEIGHT
from system.button.about import show_system_about, show_developer_about
from system.wireless.wifi import show_wifi_configure
from system.wireless.bluetooth import show_bluetooth_configure

class UIManager:
    def __init__(self, master, app_instance):
        self.master = master
        self.app = app_instance
        
        self.status_frame = tk.Frame(self.master, bd=1, relief="sunken")
        self.status_frame.pack(side="bottom", fill="x")
        self.status_text = tk.Label(self.status_frame, text="就绪", anchor="w")
        self.status_text.pack(side="left", padx=(5,0))
        self.time_label = tk.Label(self.status_frame, text="", anchor="e")
        self.time_label.pack(side="right", padx=(0,5))
        
        self.create_menu()
        self.create_desktop_canvas()
        self.update_clock()

    def create_menu(self):
        menubar = tk.Menu(self.master)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="新文件", command=self.app.menu_placeholder_function)
        file_menu.add_command(label="打开", command=self.app.menu_placeholder_function)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.master.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="背景颜色", command=self.app.edit_background_color)
        file_menu.add_separator()
        edit_menu.add_command(label="WIFI开关", command=lambda: show_wifi_configure(self.master))
        edit_menu.add_command(label="蓝牙开关", command=lambda: show_bluetooth_configure(self.master))
        menubar.add_cascade(label="设置", menu=edit_menu)
        about_menu = tk.Menu(menubar, tearoff=0)
        about_menu.add_command(label="系统信息", command=lambda: show_system_about(self.master))
        about_menu.add_command(label="关于开发者", command=lambda: show_developer_about(self.master))
        menubar.add_cascade(label="关于", menu=about_menu)
        self.master.config(menu=menubar)

    def create_desktop_canvas(self):
        self.canvas = tk.Canvas(self.master, bg="#3498db", scrollregion=(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT))
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self.app.start_pan)
        self.canvas.bind("<B1-Motion>", self.app.pan_view)

    def update_clock(self):
        now = time.strftime("%H:%M:%S")
        self.time_label.config(text=now)
        self.master.after(1000, self.update_clock)
    
    def set_status_text(self, text):
        self.status_text.config(text=text)