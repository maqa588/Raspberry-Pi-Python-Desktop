# app.py
import tkinter as tk
import sys
from system.ui_components import UIManager
from system.app_logic import LogicHandler
from system.icon_manager import IconManager
from system.config import WINDOW_WIDTH, WINDOW_HEIGHT
from software.browser_app import create_browser_window

# 检查命令行参数
if len(sys.argv) > 1 and sys.argv[1] == "browser_only":
    # 如果参数是 "browser_only"，直接启动浏览器应用
    create_browser_window()
    sys.exit()

class DesktopApp:
    def __init__(self, root):
        self.master = root
        self.root = root  # ⬅️ 增加这行，将根窗口对象赋给 self.root
        self.master.title("Raspberry Pi Desktop")
        self.master.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        
        # 初始化功能模块
        self.ui = UIManager(self.master, self)
        self.logic = LogicHandler(self.master, self)
        self.icon_manager = IconManager(self)
        
        # 加载图标
        self.icons = self.icon_manager.icons
    
    # 将核心方法暴露出来，供其他模块调用
    def get_command_for_icon(self, icon_id):
        return self.logic.get_command_for_icon(icon_id)
        
    def update_icon_position(self, icon_id, x, y):
        self.icon_manager.update_icon_position(icon_id, x, y)
    
    def menu_placeholder_function(self):
        self.logic.menu_placeholder_function()
    
    def edit_background_color(self):
        self.logic.edit_background_color()
    
    def show_system_about(self):
        self.logic.show_system_about()

    def show_developer_about(self):
        self.logic.show_developer_about()

    def start_pan(self, event):
        self.logic.start_pan(event)
        
    def pan_view(self, event):
        self.logic.pan_view(event)

if __name__ == "__main__":
    root = tk.Tk()
    app = DesktopApp(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Bye")
    finally:
        sys.exit()