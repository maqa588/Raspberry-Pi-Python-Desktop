import tkinter as tk
import sys
from system.desktop_ui_components import UIManager
from system.app_logic import LogicHandler
from system.icon_manager import IconManager
from software.browser_app import create_browser_window
from software.file_manager_app import FileManagerApp
from system.config import MAIN_WIDTH, MAIN_HEIGHT

# ... (命令行参数检查部分保持不变) ...
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
        self.master.geometry(f"{MAIN_WIDTH}x{MAIN_HEIGHT}")
        
        # 1. 首先初始化 LogicHandler，因为 UI 组件在创建时会依赖它。
        #    此时 UI 和 IconManager 都还不存在，所以暂时传入 None。
        self.logic = LogicHandler(self, None, None)
        
        # 2. 接着初始化 UIManager。现在当它回调 self.app.get_command_for_icon 时,
        #    self.logic 已经存在，不会再报错。
        self.ui = UIManager(self.master, self)
        
        # 3. 然后初始化 IconManager。它在创建图标时需要 self.ui.canvas，
        #    由于 self.ui 已经创建，所以可以正常工作。
        self.icon_manager = IconManager(self)
        
        # 4. 现在所有核心组件都已创建，回头更新 LogicHandler 中缺失的引用。
        self.logic.icon_manager = self.icon_manager
        self.logic.ui = self.ui
        
        # --- ^ ^ ^ 修改结束 ^ ^ ^ ---
        
        # 5. 从 IconManager 实例中获取图标，供其他模块使用 (此行可选，取决于你的设计)。
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
        # 假设这个方法在 LogicHandler 中
        self.logic.show_system_about()

    def show_developer_about(self):
        # 假设这个方法在 LogicHandler 中
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