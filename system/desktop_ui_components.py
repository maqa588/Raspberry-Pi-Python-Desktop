import tkinter as tk
import time

from system.icon_manager import IconManager
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
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="新文件", command=self.app.menu_placeholder_function)
        file_menu.add_command(label="打开", command=self.app.menu_placeholder_function)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.master.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        
        # 设置菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="背景颜色", command=self.app.edit_background_color)
        edit_menu.add_command(label="图标文字颜色", command=self.app.edit_label_color)
        edit_menu.add_separator() # 这里应该是 edit_menu
        edit_menu.add_command(label="WIFI开关", command=lambda: show_wifi_configure(self.master))
        edit_menu.add_command(label="蓝牙开关", command=lambda: show_bluetooth_configure(self.master))
        menubar.add_cascade(label="设置", menu=edit_menu)
        
        # 关于菜单
        about_menu = tk.Menu(menubar, tearoff=0)
        about_menu.add_command(label="系统信息", command=lambda: show_system_about(self.master))
        about_menu.add_command(label="关于开发者", command=lambda: show_developer_about(self.master))
        menubar.add_cascade(label="关于", menu=about_menu)
        
        # --- V V V 这里是修改的核心 V V V ---
        # 软件菜单 (动态生成)
        software_menu = tk.Menu(menubar, tearoff=0)
        
        # 1. 从 IconManager 类获取默认图标布局
        default_icons = IconManager._get_default_layout()
        
        # 2. 遍历布局信息，为每个图标创建一个菜单项
        for icon_data in default_icons:
            icon_id = icon_data['id']
            icon_text = icon_data['text']
            
            # 3. 通过主应用实例(self.app)获取对应的命令
            command_func = self.app.get_command_for_icon(icon_id)
            
            # 4. 将菜单项添加到“软件”菜单中
            software_menu.add_command(label=icon_text, command=command_func)
            
        menubar.add_cascade(label="软件", menu=software_menu)
        # --- ^ ^ ^ 修改结束 ^ ^ ^ ---
        
        self.master.config(menu=menubar)

    def create_desktop_canvas(self):
        self.canvas = tk.Canvas(self.master, bg="#3498db", scrollregion=(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT))
        self.canvas.pack(fill=tk.BOTH, expand=True)
        # 注意: 您的代码绑定的是左键拖动，我予以保留。
        # 如果需要中键拖动，请改为 <ButtonPress-2> 和 <B2-Motion>
        self.canvas.bind("<ButtonPress-1>", self.app.start_pan)
        self.canvas.bind("<B1-Motion>", self.app.pan_view)

    def update_clock(self):
        now = time.strftime("%H:%M:%S")
        self.time_label.config(text=now)
        self.master.after(1000, self.update_clock)
    
    def set_status_text(self, text):
        self.status_text.config(text=text)