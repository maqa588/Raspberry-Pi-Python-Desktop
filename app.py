import tkinter as tk
import sys
# 不需要直接导入 appdirs_pack，因为 icon_manager 会处理
from system.ui_components import UIManager
from system.app_logic import LogicHandler
from system.icon_manager import IconManager
from software.browser_app import create_browser_window
# 新增：导入文件管理器应用
from software.file_manager_app import FileManagerApp
from system.config import WINDOW_WIDTH, WINDOW_HEIGHT

# 检查命令行参数
if len(sys.argv) > 1:
    if sys.argv[1] == "browser_only":
        # 如果参数是 "browser_only"，直接启动浏览器应用
        create_browser_window()
        sys.exit()
    
    elif sys.argv[1] == "file_manager_only":
        # 如果参数是 "file_manager_only"，直接启动文件管理器
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
        
        # 初始化功能模块
        # 注意：这里需要先初始化 UIManager，因为它会被 IconManager 引用
        self.ui = UIManager(self.master, self)
        self.logic = LogicHandler(self.master, self)
        
        # 1. 初始化 IconManager，它会自动加载并创建图标
        self.icon_manager = IconManager(self)
        
        # 2. 从 IconManager 实例中获取图标，供其他模块使用
        self.icons = self.icon_manager.icons

        # 3. 增加退出事件处理函数，确保程序关闭时保存布局
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def on_close(self):
        """在程序退出时调用，确保数据被保存。"""
        print("正在退出应用程序...")
        # 调用 IconManager 的 save_layout 方法
        self.icon_manager.save_layout()
        self.master.destroy()
        
    # 将核心方法暴露出来，供其他模块调用
    def get_command_for_icon(self, icon_id):
        return self.logic.get_command_for_icon(icon_id)
        
    def update_icon_position(self, icon_id, x, y):
        # 这个方法现在只负责调用 IconManager 中的相应方法
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