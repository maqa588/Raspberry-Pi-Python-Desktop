# software/camera.py
import sys
import subprocess
import os
import platform
from tkinter import messagebox

def open_camera_system(app_instance):
    """
    根据运行环境和操作系统启动相机应用。
    """
    system = platform.system()
    
    try:
        if system == "Darwin":  # macOS
            # 在macOS上使用open命令启动Photo Booth
            command = ['open', '-a', 'Photo Booth']
            subprocess.Popen(command)
            return True
        
        elif system == "Windows":
            # 在Windows上使用start命令启动相机应用
            command = ['start', 'microsoft.windows.camera:']
            subprocess.Popen(command, shell=True)
            return True
            
        elif system == "Linux":
            # 检查是否安装了picamera2库
            try:
                import picamera2
                
                # 获取主程序的执行路径
                main_executable = sys.executable

                if getattr(sys, 'frozen', False):
                    # PyInstaller打包后的环境，直接传递参数
                    command = [main_executable, "camera_rpi_only"]
                else:
                    # 开发环境，用python解释器运行
                    command = [main_executable, 'software/camera_rpi.py']
                    
                subprocess.Popen(command)
                return True
                
            except ImportError:
                messagebox.showerror("启动失败", "Linux系统需要安装'picamera2'库。")
                return False
        
        else:
            # 对于其他不支持的系统
            messagebox.showinfo("提示", f"当前操作系统 '{system}' 暂不支持相机功能。")
            return False

    except Exception as e:
        messagebox.showerror("启动失败", f"启动相机时发生未知错误：{e}")
        return False