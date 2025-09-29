import sys
import subprocess
import os
import platform
from tkinter import messagebox
import tkinter as tk

def open_camera_system(app_instance):
    """
    根据操作系统类型，通过启动主应用 (app.py) 的子进程模式来启动相机应用。
    此函数修正了 PyInstaller 打包后的路径问题，使其能兼容 开发环境 和 打包环境。
    
    Args:
        app_instance: 主应用的实例，用于获取 project_root。
    """
    system = platform.system()
    
    # 获取 Python 解释器的执行路径 (开发环境) 或 主可执行文件的路径 (打包环境)
    main_executable = sys.executable
    
    # 确定启动模式
    mode = None
    
    if system == "Linux":
        mode = 'camera_rpi_only'
        try:
            # 检查 picamera2 是否可用，这是 Pi 版本的硬性要求
            import picamera2 # type: ignore
        except ImportError:
            messagebox.showerror("启动失败", "Linux系统 (Raspberry Pi) 需要安装 'picamera2' 库才能启动。")
            return False
        
    elif system == "Windows":
        mode = 'camera_win_only'
        
    elif system == "Darwin":  # macOS
        mode = 'camera_mac_only'

    else:
        messagebox.showinfo("提示", f"当前操作系统 '{system}' 暂不支持相机功能。")
        return False
        
    # --- 核心修正区域 ---
    command = [main_executable]
    
    if getattr(sys, 'frozen', False):
        # 1. 打包环境 (PyInstaller)：直接执行主可执行文件，将 mode 作为第一个参数。
        #    主程序会检查 sys.argv[1] 来决定启动哪个子功能。
        command.append(mode)
        
        # 在打包环境中，sys.executable 位于 Contents/MacOS/ 下，cwd 应该是其父目录。
        # 但我们保险起见，直接使用主执行文件所在的目录作为 cwd。
        cwd_path = os.path.dirname(main_executable)
    else:
        # 2. 开发环境：使用 Python 解释器执行 app.py，并将 mode 作为参数。
        try:
            project_root = app_instance.project_root
        except (AttributeError, TypeError):
            # 如果在测试环境下调用，则尝试推断项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        app_path = os.path.join(project_root, 'app.py')
        
        if not os.path.exists(app_path):
             messagebox.showerror("启动失败", f"找不到主入口文件: {app_path}。无法启动子进程。")
             return False
        
        # 完整的开发环境命令：[python, app.py, mode]
        command.append(app_path)
        command.append(mode)
        cwd_path = project_root
        
    # --- 修正结束 ---

    try:
        # 启动子进程。设置 cwd 参数确保相对路径 (如 models) 正确解析
        subprocess.Popen(command, cwd=cwd_path) 
        return True
        
    except Exception as e:
        messagebox.showerror("启动失败", f"启动相机时发生未知错误：{e}")
        return False

if __name__ == "__main__":
    # 仅用于测试
    root = tk.Tk()
    root.withdraw() # 隐藏主窗口
    # 仅用于测试，请注意测试时 app_instance 为 None，project_root 推导逻辑需要可靠
    open_camera_system(None) 
    root.mainloop()
