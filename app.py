import tkinter as tk
import sys
from pathlib import Path
import subprocess
from tkinter import messagebox

# 从 system 包导入核心组件
from system.desktop_ui_components import UIManager
from system.app_logic import LogicHandler
from system.icon_manager import IconManager
from system.config import MAIN_WIDTH, MAIN_HEIGHT

# 导入各个独立应用的启动函数
from software.browser_app import create_browser_window
from software.browser import open_browser
from software.file_editor import open_file_editor
from software.camera import open_camera_system
from software.terminal import open_terminal_system

# 获取项目的根目录，以便于子进程能够正确找到模块
PROJECT_ROOT = Path(__file__).resolve().parent

# --- 独立应用的启动函数 ---
# 这些函数应该放在一个方便主程序调用的地方
def open_file_manager_system(app_instance):
    """根据运行环境启动文件管理器应用。"""
    try:
        main_executable = sys.executable
        if getattr(sys, 'frozen', False):
            # PyInstaller 打包后的环境
            command = [main_executable, "file_manager_only"]
        else:
            # 开发环境，使用 -m 参数和 cwd 参数来正确地运行模块
            command = [main_executable, "-m", "software.file_manager.main"]
        
        # 启动子进程，并将工作目录设置为项目根目录
        subprocess.Popen(command, cwd=PROJECT_ROOT)
        return True
    except Exception as e:
        messagebox.showerror("启动失败", f"启动文件管理器时发生未知错误：{e}")
        return False

# --- 命令行参数处理 ---
# 当直接从命令行启动特定应用时
if len(sys.argv) > 1:
    if sys.argv[1] == "browser_only":
        create_browser_window()
        sys.exit()
    elif sys.argv[1] == "file_manager_only":
        from software.file_manager.main import FileManagerApp # 动态导入
        fm_root = tk.Tk()
        FileManagerApp(fm_root)
        fm_root.mainloop()
        sys.exit()
    # 可以在此处添加其他应用的命令行参数处理

class DesktopApp:
    def __init__(self, root):
        self.master = root
        self.root = root
        self.master.title("Raspberry Pi Desktop")
        self.master.geometry(f"{MAIN_WIDTH}x{MAIN_HEIGHT}")
        
        # 将所有启动函数打包成一个字典，方便传递
        app_launchers = {
            'file_manager': open_file_manager_system,
            'browser': open_browser,
            'editor': open_file_editor,
            'camera': open_camera_system,
            'terminal': open_terminal_system
        }
        
        # 1. 初始化 LogicHandler
        self.logic = LogicHandler(self, None, None, app_launchers)
        
        # 2. 初始化 UIManager
        self.ui = UIManager(self.master, self)
        
        # 3. 初始化 IconManager
        self.icon_manager = IconManager(self)
        
        # 4. 更新 LogicHandler 中缺失的引用
        self.logic.icon_manager = self.icon_manager
        self.logic.ui = self.ui
        
        self.icons = self.icon_manager.icons

        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def on_close(self):
        """在程序退出时调用，确保数据被保存。"""
        print("正在退出应用程序...")
        self.icon_manager.save_layout()
        self.master.destroy()
        
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
