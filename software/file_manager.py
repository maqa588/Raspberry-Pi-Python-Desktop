import sys
import subprocess
import os
from pathlib import Path
from tkinter import messagebox

def open_file_manager(app_instance):
    """
    根据运行环境（打包或开发）启动文件管理器应用。
    """
    try:
        main_executable = sys.executable

        if getattr(sys, 'frozen', False):
            # 如果是 PyInstaller 打包后的环境
            command = [main_executable, "file_manager_only"]
        else:
            # 如果是直接用 Python 运行的开发环境
            project_root = Path(__file__).resolve().parent

            # 使用 -m 参数和 cwd 参数来正确地运行模块
            subprocess.Popen([main_executable, "-m", "software.file_manager.main"], cwd=project_root)
            return True

        subprocess.Popen(command)
        return True

    except Exception as e:
        messagebox.showerror("启动失败", f"启动文件管理器时发生未知错误：{e}")
        return False