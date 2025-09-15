# system/browser.py
import sys
import os
import subprocess
from tkinter import messagebox

# 从 browser_app.py 导入退出信号
from system.browser_app import EXIT_SIGNAL

def open_browser_system():
    """
    启动一个独立的进程来运行浏览器应用，并等待其退出。
    返回 True 表示成功退出，False 表示失败。
    """
    try:
        # 使用 subprocess.run 启动 browser_app.py，并捕获标准输出
        # capture_output=True 捕获输出
        # text=True 解码输出为字符串
        result = subprocess.run(
            [sys.executable, 'system/browser_app.py'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # 检查子进程的输出是否包含退出信号
        if EXIT_SIGNAL in result.stdout:
            print("浏览器已成功退出。")
            return True
        else:
            print("浏览器意外退出，未收到退出信号。")
            print("子进程输出：", result.stdout)
            return False
            
    except FileNotFoundError:
        messagebox.showerror("文件未找到", "未能找到 browser_app.py 文件。")
        return False
    except subprocess.CalledProcessError as e:
        messagebox.showerror("启动失败", f"启动浏览器时发生错误：{e.stderr}")
        return False
    except Exception as e:
        messagebox.showerror("启动失败", f"启动浏览器时发生未知错误：{e}")
        return False