import sys
import subprocess
import os
from pathlib import Path
from tkinter import messagebox

# 我们假设主程序会传递 project_root
def open_file_editor(app_instance):
    """
    根据运行环境（打包或开发）启动文件编辑器应用。
    此函数被主程序调用，负责启动一个新进程来运行文件编辑器。
    """
    try:
        main_executable = sys.executable
        
        # 从 app_instance 获取项目的根目录
        project_root = app_instance.project_root

        if getattr(sys, 'frozen', False):
            # 如果是 PyInstaller 打包后的环境
            # 我们将 "file_editor_only" 和项目根目录作为参数传递给主可执行文件
            command = [main_executable, "file_editor_only", str(project_root)]
        else:
            # 如果是直接用 Python 运行的开发环境
            # 我们需要用 python 解释器来运行 file_editor_app.py
            command = [main_executable, 'software/file_editor_app.py', str(project_root)]
            
        # 启动子进程，不阻塞主程序
        subprocess.Popen(command)
        
        return True

    except Exception as e:
        messagebox.showerror("启动失败", f"启动文件编辑器时发生未知错误：{e}")
        return False
