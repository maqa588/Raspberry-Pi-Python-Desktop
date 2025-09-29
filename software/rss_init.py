import sys
import os
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
        project_root = app_instance.project_root

        # 3. 确定 RSS 脚本路径
        # 注意: 这里需要指向包含 RSSReaderApp 类的文件
        # 假设 RSSReaderApp 位于 software/rss_app.py
        rss_script_path = Path(app_instance.project_root) / 'software' / 'rss_app.py'

        if getattr(sys, 'frozen', False):
            # 打包（Frozen）环境：传递启动参数给主可执行文件
            command = [main_executable, "rss_only", str(project_root)]
        else:
            # 开发环境：直接运行 RSS 应用的主 Python 脚本
            command = [main_executable, str(rss_script_path), str(project_root)]
            
        # 4. 启动子进程，不阻塞主程序
        subprocess.Popen(command)
        
        return True

    except Exception as e:
        messagebox.showerror("启动失败", f"启动RSS阅读器时发生未知错误：{e}")
        return False
