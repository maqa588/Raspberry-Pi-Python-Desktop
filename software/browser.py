# software/browser.py
import sys
import subprocess
import os
from tkinter import messagebox

def open_browser_system(app_instance):
    """
    根据运行环境（打包或开发）启动浏览器应用。
    """
    try:
        # 获取主程序的执行路径
        main_executable = sys.executable

        if getattr(sys, 'frozen', False):
            # 如果是 PyInstaller 打包后的环境
            # 我们只需要传递 "browser_only" 参数给主程序
            command = [main_executable, "browser_only"]
        else:
            # 如果是直接用 Python 运行的开发环境
            # 我们需要用 python 解释器来运行 browser_app.py
            command = [main_executable, 'software/browser_app.py']
            
        # 启动子进程，不阻塞主程序
        subprocess.Popen(command)
        
        return True

    except Exception as e:
        messagebox.showerror("启动失败", f"启动浏览器时发生未知错误：{e}")
        return False