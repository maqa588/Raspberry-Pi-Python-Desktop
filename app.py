import tkinter as tk
import sys
from system.ui_components import UIManager
from system.app_logic import LogicHandler
from system.icon_manager import IconManager
from software.browser_app import create_browser_window
from software.file_manager_app import FileManagerApp
from system.config import WINDOW_WIDTH, WINDOW_HEIGHT

# 检查命令行参数
if len(sys.argv) > 1:
    if sys.argv[1] == "browser_only":
        create_browser_window()
        sys.exit()
    
    elif sys.argv[1] == "file_manager_only":
        fm_root = tk.Tk()
        FileManagerApp(fm_root)
        fm_root.mainloop()
        sys.exit()

class DesktopApp:
    def __init__(self, root):
        self.master = root
        self.root = root
        self.master.title("Raspberry Pi Desktop")
        self.master.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        
        # 1. 初始化 UIManager，它提供了画布和 UI 元素。
        self.ui = UIManager(self.master, self)
        
        # 2. 初始化 LogicHandler，它包含了图标的双击命令逻辑。
        #    LogicHandler 现在需要 IconManager 和 UIManager 的引用。
        self.logic = LogicHandler(self, None, self.ui) # 先用 None 占位，稍后更新
        
        # 3. 初始化 IconManager，它依赖 UIManager 和 LogicHandler。
        self.icon_manager = IconManager(self)
        
        # 4. 更新 LogicHandler，将 IconManager 引用传递给它。
        self.logic.icon_manager = self.icon_manager
        
        # 5. 从 IconManager 实例中获取图标，供其他模块使用。
        self.icons = self.icon_manager.icons

        # 6. 增加退出事件处理函数，确保程序关闭时保存布局。
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def on_close(self):
        """在程序退出时调用，确保数据被保存。"""
        print("正在退出应用程序...")
        self.icon_manager.save_layout()
        self.master.destroy()
        
    # 将核心方法暴露出来，供其他模块调用
    def get_command_for_icon(self, icon_id):
        # 这个方法现在可以安全地访问 self.logic。
        return self.logic.get_command_for_icon(icon_id)
        
    def update_icon_position(self, icon_id, x, y):
        self.icon_manager.update_icon_position(icon_id, x, y)
    
    def menu_placeholder_function(self):
        self.logic.menu_placeholder_function()
    
    def edit_background_color(self):
        self.logic.edit_background_color()

    def edit_label_color(self):
        self.logic.edit_label_color()
    
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