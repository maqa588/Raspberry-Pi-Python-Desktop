import tkinter as tk
import sys
import os 
from pathlib import Path
import subprocess
from tkinter import messagebox  
import platform 

# --- 核心组件导入 (现在从 app_logic 导入启动函数) ---
try:
    # 从 system.app_logic 导入 LogicHandler 和新移动的启动函数
    from system.app_logic import LogicHandler, start_sub_process_app
    
    # 其他系统组件
    from system.desktop_ui_components import UIManager
    from system.icon_manager import IconManager
    
    # 尝试导入主窗口大小配置，如果失败则使用默认值
    try:
        from system.config import MAIN_WIDTH, MAIN_HEIGHT
    except ImportError:
        MAIN_WIDTH = 1000
        MAIN_HEIGHT = 700

    # --- 独立应用启动函数导入 (用于 LogicHandler 的 app_launchers) ---
    # 这些函数负责在主进程中调用 subprocess.Popen，启动子进程
    from software.browser import open_browser
    from software.file_editor import open_file_editor
    from software.camera import open_camera_system 
    from software.terminal import open_terminal_system
    from software.file_manager_init import open_file_manager
    from software.deepseek import open_deepseek
    from software.game import open_pong_game
    from software.rss_init import open_rss_reader 
    
except ImportError:
    # 允许在子进程模式下，如果只需要特定模块时，其他模块导入失败
    pass


# 获取项目的根目录 (在 PyInstaller 环境下会指向可执行文件所在目录)
PROJECT_ROOT = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent

# --- 命令行参数处理 (使用从 app_logic 导入的函数) ---
if len(sys.argv) > 1:
    
    mode = sys.argv[1]
    
    # 1. 路径设置: 确保子进程环境正确设置 PROJECT_ROOT
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
        
    # --- 统一使用 start_sub_process_app 启动 ---
    
    # RSS Reader (使用类 RSSReaderApp)
    if mode == "rss_only":
        start_sub_process_app('software.rss_app', entry_name='RSSReaderApp')
    
    # 相机子进程启动 (使用类 App)
    elif mode == 'camera_mac_only':
        from software.camera_pi.camera_mac import CameraApp
        app = CameraApp()
        app.run()
    elif mode == 'camera_win_only':
        from software.camera_pi.camera_win import CameraApp
        app = CameraApp()
        app.run()
    elif mode == 'camera_rpi_only':
        from software.camera_pi.camera_rpi import CameraAppRpiTorchScript
        app = CameraAppRpiTorchScript()
        app.run()
    
    # DeepSeek AI 启动 (使用函数 create_deepseek_ui)
    elif mode == 'deepseek_only':
        start_sub_process_app('software.deepseek_app', entry_name='create_deepseek_ui')
        
    # 游戏 (Pong) 启动 (使用函数 create_pong_game)
    elif mode == 'game_only':
        start_sub_process_app('software.games.pong.main_menu', entry_name='run_game_menu')
    
    # --- 保持原有逻辑（browser, file_manager, file_editor）---
    # 这些应用需要从命令行接收额外的文件路径参数 (sys.argv[2]), 
    # 故保持直接处理逻辑，而不是使用统一的 start_sub_process_app
    
    # 浏览器启动 (使用函数 create_browser_window)
    elif mode == "browser_only":
        try:
            from software.browser_app import create_browser_window
            startup_url = sys.argv[2] if len(sys.argv) > 2 else None
            create_browser_window(startup_url) 
        except Exception as e:
            messagebox.showerror("启动失败", f"浏览器启动失败：{e}")
        sys.exit()

    
    # 文件管理器启动 (使用类 FileManagerApp)
    elif mode == "file_manager_only":
        try:
            from software.file_manager.main import FileManagerApp 
            if len(sys.argv) > 2:
                # 模拟 start_sub_process_app 内部的类启动逻辑
                fm_root = tk.Tk()
                project_root_path = Path(sys.argv[2])
                FileManagerApp(fm_root, project_root=project_root_path)
                fm_root.mainloop()
            else:
                messagebox.showerror("启动失败", "文件管理器启动失败：缺少 project_root 参数。")
        except Exception as e:
             messagebox.showerror("启动失败", f"文件管理器启动失败：{e}")
        sys.exit()
    
    # 文件编辑器启动 (使用类 FileEditorApp)
    elif mode == "file_editor_only":
        try:
            from software.file_editor_app import FileEditorApp
            if len(sys.argv) > 2:
                # 模拟 start_sub_process_app 内部的类启动逻辑
                editor_root = tk.Tk()
                project_root_path = Path(sys.argv[2])
                FileEditorApp(editor_root, project_root=project_root_path)
                editor_root.mainloop()
            else:
                messagebox.showerror("启动失败", "文件编辑器启动失败：缺少 project_root 参数。")
        except Exception as e:
             messagebox.showerror("启动失败", f"文件编辑器启动失败：{e}")
        sys.exit()

class DesktopApp:
    """
    Raspberry Pi 桌面环境的主应用程序类。
    负责初始化 UI、逻辑处理器和图标管理器，并处理主窗口事件。
    """
    def __init__(self, root):
        self.master = root
        self.root = root
        self.project_root = PROJECT_ROOT
        self.master.title("Raspberry Pi Desktop")
        # 设置默认大小
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
            'rss_reader': open_rss_reader, 
        }
        
        # 1. 初始化 LogicHandler
        # LogicHandler 现在只负责调度启动，具体启动机制（subprocess.Popen）被封装在 app_launchers 中
        self.logic = LogicHandler(self, None, None, app_launchers)
        
        # 2. 初始化 UIManager
        self.ui = UIManager(self.master, self)
        
        # 3. 初始化 IconManager
        self.icon_manager = IconManager(self)
        
        # 4. 更新 LogicHandler 中缺失的引用
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
    # 启动主应用
    root = tk.Tk()
    app = DesktopApp(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Bye")
    finally:
        sys.exit()
