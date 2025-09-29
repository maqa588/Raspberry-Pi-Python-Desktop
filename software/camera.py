import sys
import subprocess
import os
import platform
from tkinter import messagebox
import tkinter as tk

def open_camera_system(app_instance):
    """
    根据运行环境和操作系统启动相应的相机应用脚本 (带 YOLO 功能)。
    
    Args:
        app_instance: 主应用的实例 (如果需要)。
    """
    system = platform.system()
    
    # 获取 Python 解释器的执行路径
    main_executable = sys.executable
    
    # 获取当前文件所在的目录 (software/)
    software_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 动态获取项目根目录
    # (software/camera.py) -> (software/) -> (project_root/)
    project_root = os.path.dirname(software_dir)
    
    # 统一使用 camera_pi/ 目录下的脚本
    script_path = None
    
    if system == "Linux":
        # Linux (Raspberry Pi) 使用 picamera2 版本
        script_path = os.path.join(software_dir, 'camera_pi', 'camera_rpi.py')
        try:
            # 检查 picamera2 是否可用，这是 Pi 版本的硬性要求
            import picamera2 # type: ignore
        except ImportError:
            messagebox.showerror("启动失败", "Linux系统 (Raspberry Pi) 需要安装 'picamera2' 库才能启动。")
            return False
        
    elif system == "Windows":
        # Windows 使用基于 OpenCV 的版本
        script_path = os.path.join(software_dir, 'camera_pi', 'camera_nonlinux.py')
        
    elif system == "Darwin":  # macOS
        # macOS 使用基于 OpenCV 的版本
        script_path = os.path.join(software_dir, 'camera_pi', 'camera_nonlinux.py')

    else:
        messagebox.showinfo("提示", f"当前操作系统 '{system}' 暂不支持 YOLO 相机功能。")
        return False
    
    # 检查 OpenCV 是否可用 (Windows 和 macOS 版本都需要)
    if system != "Linux":
        try:
            import cv2
        except ImportError:
            messagebox.showerror("启动失败", f"{system} 系统需要安装 'opencv-python' 库才能运行相机。")
            return False

    if not os.path.exists(script_path):
        messagebox.showerror("启动失败", f"找不到相机脚本: {script_path}。请检查文件路径是否正确。")
        return False

    try:
        # 构造执行命令：[python解释器, 脚本路径]
        command = [main_executable, script_path]
        
        # 启动子进程。设置 cwd 参数确保相对路径 (如 models) 正确解析
        # CWD 设置为项目根目录，以便 camera_rpi/win/mac.py 能够正确导入 system 模块
        subprocess.Popen(command, cwd=project_root) 
        return True
        
    except Exception as e:
        messagebox.showerror("启动失败", f"启动相机时发生未知错误：{e}")
        return False

if __name__ == "__main__":
    # 仅用于测试
    root = tk.Tk()
    root.withdraw() # 隐藏主窗口
    open_camera_system(None)
    root.mainloop()
