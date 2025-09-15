# system/ui_components.py
import tkinter as tk
import time
from system.config import CANVAS_WIDTH, CANVAS_HEIGHT

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
        edit_menu.add_command(label="设置", command=self.app.menu_placeholder_function)
        menubar.add_cascade(label="编辑", menu=edit_menu)
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