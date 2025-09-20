import sys
import subprocess
import os
from pathlib import Path
from tkinter import messagebox

def open_file_manager(app_instance):
    """
    根据运行环境（打包或开发）启动文件管理器应用。
    此函数被主程序调用，负责启动一个新进程来运行文件管理器。
    """
    try:
        main_executable = sys.executable
        # 获取项目的根目录，与主程序中的逻辑保持一致
        project_root = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(os.path.abspath(__file__)).parent.parent.parent

        if getattr(sys, 'frozen', False):
            # 如果是 PyInstaller 打包后的环境
            # 我们将 "file_manager_only" 和项目根目录作为参数传递给主可执行文件
            command = [main_executable, "file_manager_only", str(project_root)]
        else:
            # 如果是直接用 Python 运行的开发环境
            # 使用 -m 参数和 cwd 参数来正确地运行模块
            command = [main_executable, "-m", "software.file_manager.main", str(project_root)]
        
        # 启动子进程，不阻塞主程序
        subprocess.Popen(command)
        
        return True

    except Exception as e:
        messagebox.showerror("启动失败", f"启动文件管理器时发生未知错误：{e}")
        return False
