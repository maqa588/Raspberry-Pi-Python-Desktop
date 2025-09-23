import sys
import subprocess
import os
from pathlib import Path
from tkinter import messagebox

def open_deepseek(app_instance):
    """
    根据运行环境（打包或开发）启动Deepseek应用。
    此函数被主程序调用，负责启动一个新进程来运行Deepseek。
    """
    try:
        main_executable = sys.executable
        
        project_root = app_instance.project_root

        if getattr(sys, 'frozen', False):
            command = [main_executable, "deepseek_only", str(project_root)]
        else:
            command = [main_executable, 'software/deepseek_app.py', str(project_root)]
            
        # 启动子进程，不阻塞主程序
        subprocess.Popen(command)
        
        return True

    except Exception as e:
        messagebox.showerror("启动失败", f"启动Deepseek时发生未知错误：{e}")
        return False
