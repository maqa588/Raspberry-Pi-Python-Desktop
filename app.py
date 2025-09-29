import tkinter as tk
import sys
from pathlib import Path
import subprocess
from tkinter import messagebox
import os # 导入 os 模块以供 sys.path 使用

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
from software.file_manager_init import open_file_manager
from software.deepseek import open_deepseek
from software.game import open_pong_game
from software.rss_init import open_rss_reader # <-- 导入 RSS 阅读器启动函数

# 获取项目的根目录，以便于子进程能够正确找到模块
# PyInstaller 打包后，sys.executable 所在目录就是项目的根目录
PROJECT_ROOT = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent

# --- 命令行参数处理 ---
# 当直接从命令行启动特定应用时
if len(sys.argv) > 1:
    if sys.argv[1] == "browser_only":
        # 浏览器模式，可以接收可选的 URL 参数
        startup_url = sys.argv[2] if len(sys.argv) > 2 else None
        # 注意：这里假设 create_browser_window 接受一个 URL 参数，否则需要调整
        create_browser_window(startup_url) 
        sys.exit()
    elif sys.argv[1] == "rss_only":
        # RSS 阅读器模式：这是子进程启动时执行的逻辑
        try:
            # 关键修复：在尝试动态导入前，确保项目根目录在 Python 路径中
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.append(str(PROJECT_ROOT))

            # 动态导入 RSS 阅读器的主类
            from software.rss_app import RSSReaderApp 
            
            rss_root = tk.Tk()
            RSSReaderApp(rss_root)
            rss_root.mainloop()
        except ImportError as e:
            # 给出更清晰的错误提示，指导用户检查文件路径
            print(f"导入错误详情: {e}")
            messagebox.showerror("启动失败", f"RSS 阅读器启动失败：模块导入错误。\n请检查文件是否存在于 {PROJECT_ROOT}/software/rss_app.py 或检查其内部依赖项。\n错误信息: {e}")
        except Exception as e:
            # 捕获其他运行时错误
            print(f"运行时错误详情: {e}")
            messagebox.showerror("启动失败", f"RSS 阅读器启动失败：运行时错误。\n错误信息: {e}")
        sys.exit()
    elif sys.argv[1] == "file_manager_only":
        # 动态导入 FileManagerApp，避免在不需要时加载
        from software.file_manager.main import FileManagerApp 
        
        # 检查是否提供了 project_root 参数
        if len(sys.argv) > 2:
            fm_root = tk.Tk()
            project_root_path = Path(sys.argv[2])
            FileManagerApp(fm_root, project_root=project_root_path)
            fm_root.mainloop()
        else:
            messagebox.showerror("启动失败", "文件管理器启动失败：缺少 project_root 参数。")
        sys.exit()
    elif sys.argv[1] == "file_editor_only":
        # 动态导入 FileEditorApp
        from software.file_editor_app import FileEditorApp
        
        if len(sys.argv) > 2:
            editor_root = tk.Tk()
            project_root_path = Path(sys.argv[2])
            FileEditorApp(editor_root, project_root=project_root_path)
            editor_root.mainloop()
        else:
            messagebox.showerror("启动失败", "文件编辑器启动失败：缺少 project_root 参数。")
        sys.exit()
    # 可以在此处添加其他应用的命令行参数处理

class DesktopApp:
    """
    Raspberry Pi 桌面环境的主应用程序类。
    负责初始化 UI、逻辑处理器和图标管理器，并处理主窗口事件。
    """
    def __init__(self, root):
        self.master = root
        self.root = root
        # 将 PROJECT_ROOT 变量赋值给实例属性
        self.project_root = PROJECT_ROOT
        self.master.title("Raspberry Pi Desktop")
        self.master.geometry(f"{MAIN_WIDTH}x{MAIN_HEIGHT}")
        
        # 将所有启动函数打包成一个字典，方便传递给 LogicHandler
        app_launchers = {
            'file_manager': open_file_manager,
            'browser': open_browser,
            'editor': open_file_editor,
            'camera': open_camera_system,
            'terminal': open_terminal_system,
            'deepseek': open_deepseek,
            'games': open_pong_game,
            'rss_reader': open_rss_reader, # <-- RSS 阅读器启动函数
        }
        
        # 1. 初始化 LogicHandler
        # LogicHandler 负责处理业务逻辑和应用启动
        self.logic = LogicHandler(self, None, None, app_launchers)
        
        # 2. 初始化 UIManager
        # UIManager 负责构建主窗口的菜单栏和状态栏
        self.ui = UIManager(self.master, self)
        
        # 3. 初始化 IconManager
        # IconManager 负责管理图标的加载、布局和持久化
        self.icon_manager = IconManager(self)
        
        # 4. 更新 LogicHandler 中缺失的引用
        # 建立 LogicHandler <-> UIManager <-> IconManager 之间的循环引用
        self.logic.icon_manager = self.icon_manager
        self.logic.ui = self.ui
        
        # 将 Icons 字典暴露给实例（如果需要）
        self.icons = self.icon_manager.icons

        # 绑定窗口关闭事件，确保保存配置
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def on_close(self):
        """在程序退出时调用，确保数据被保存。"""
        print("正在退出应用程序...")
        self.icon_manager.save_layout()
        self.master.destroy()
        
    # --- 逻辑委托方法 (Delegation Methods) ---
    # 这些方法只是将调用转发给 LogicHandler 或 IconManager，
    # 保持了 DesktopApp 作为一个控制器的角色。

    def get_command_for_icon(self, icon_id):
        return self.logic.get_command_for_icon(icon_id)
        
    def update_icon_position(self, icon_id, x, y):
        self.icon_manager.update_icon_position(icon_id, x, y)
    
    # 菜单功能委托
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

    # 拖拽/平移功能委托
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
