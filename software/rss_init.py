import sys
import subprocess
from tkinter import messagebox
from pathlib import Path

def open_rss_reader(app_instance):
    """
    根据运行环境（打包或开发）启动 RSS 阅读器应用。
    此函数被主桌面应用 (app.py) 调用，用于启动 RSS 阅读器作为一个新的独立进程。
    
    参数:
        app_instance: 主桌面应用的实例 (DesktopApp)，用于获取 project_root。
    
    返回:
        bool: 启动成功返回 True，失败返回 False。
    """
    try:
        # 1. 获取主执行文件路径
        main_executable = sys.executable
        
        # 2. 从主应用实例中获取项目根路径
        # project_root = app_instance.project_root # 此变量目前未使用

        # 3. 统一构建子进程命令：总是通过启动主程序并带上 "rss_only" 参数
        if getattr(sys, 'frozen', False):
            # 打包（Frozen）环境：主程序就是可执行文件
            command = [main_executable, "rss_only"]
        else:
            # 开发环境：必须启动 app.py，而不是直接启动 python 解释器
            # 我们需要找到 app.py 的完整路径
            app_path = Path(__file__).resolve().parent.parent / 'app.py'
            
            # 使用 python 解释器运行 app.py 并带上 rss_only 参数
            command = [main_executable, str(app_path), "rss_only"]
            
        # 4. 启动子进程，不阻塞主程序
        # 使用 CREATE_NEW_CONSOLE 可以在 Windows 上看到单独的终端窗口（如果需要）
        # 但在 macOS/Linux 上，通常只需要 Popen 即可。
        # 我们在这里使用默认设置，保持跨平台兼容性。
        subprocess.Popen(command)
        
        return True

    except Exception as e:
        # 打印更详细的错误信息
        print(f"启动RSS阅读器时发生错误，尝试的命令: {command}")
        messagebox.showerror("启动失败", f"启动RSS阅读器时发生未知错误：{e}")
        return False
