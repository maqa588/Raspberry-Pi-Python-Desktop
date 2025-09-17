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
            command = ['open', '-a', 'Photo Booth']
            subprocess.Popen(command)
            return True
        
        elif system == "Windows":
            command = ['start', 'microsoft.windows.camera:']
            subprocess.Popen(command, shell=True)
            return True
            
        elif system == "Linux":
            try:
                import picamera2
                
                # 获取主程序的执行路径
                main_executable = sys.executable
                
                # 动态获取项目根目录
                # os.path.dirname(__file__) 是当前文件所在目录 (software/)
                # os.path.dirname(...) 再向上找一级就是项目根目录
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

                if getattr(sys, 'frozen', False):
                    command = [main_executable, "camera_rpi_only"]
                    # 打包环境通常不需要设置 cwd
                    subprocess.Popen(command)
                else:
                    # 开发环境，用python解释器运行
                    command = [main_executable, 'software/camera_rpi.py']
                    # 在这里设置 cwd 参数，确保子进程在项目根目录运行
                    subprocess.Popen(command, cwd=project_root)
                    
                return True
                
            except ImportError:
                messagebox.showerror("启动失败", "Linux系统需要安装'picamera2'库。")
                return False
        
        else:
            messagebox.showinfo("提示", f"当前操作系统 '{system}' 暂不支持相机功能。")
            return False

    except Exception as e:
        messagebox.showerror("启动失败", f"启动相机时发生未知错误：{e}")
        return False