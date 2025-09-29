# software/camera.py
import sys
import subprocess
import os
import platform
from tkinter import messagebox
import tkinter as tk

def open_camera_system(app_instance=None):
    """
    跨平台启动相机应用 (子进程模式)，支持 macOS/Windows/Linux (Raspberry Pi)。
    PyInstaller 打包和开发环境兼容。
    
    Args:
        app_instance: 可选，主应用实例，用于获取 project_root。开发环境可为 None。
    """
    system = platform.system()
    main_executable = sys.executable
    mode = None

    # 根据系统选择模式
    if system == "Linux":
        mode = "camera_rpi_only"
        try:
            import picamera2  # type: ignore
        except ImportError:
            messagebox.showerror("启动失败", "Linux系统 (Raspberry Pi) 需要安装 'picamera2' 库才能启动。")
            return False

    elif system == "Windows":
        mode = "camera_win_only"

    elif system == "Darwin":  # macOS
        mode = "camera_mac_only"

    else:
        messagebox.showinfo("提示", f"当前操作系统 '{system}' 暂不支持相机功能。")
        return False

    command = [main_executable]

    if getattr(sys, "frozen", False):
        # PyInstaller 打包环境：可执行文件直接传 mode 参数
        command.append(mode)
        cwd_path = os.path.dirname(main_executable)

    else:
        # 开发环境：使用 Python 执行 app.py，并传递 mode
        try:
            project_root = getattr(app_instance, "project_root", None)
            if not project_root:
                raise AttributeError
        except AttributeError:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        app_path = os.path.join(project_root, "app.py")
        if not os.path.exists(app_path):
            messagebox.showerror("启动失败", f"找不到主入口文件: {app_path}")
            return False

        command.append(app_path)
        command.append(mode)
        cwd_path = project_root

    # 启动子进程
    try:
        subprocess.Popen(command, cwd=cwd_path)
        return True
    except Exception as e:
        messagebox.showerror("启动失败", f"启动相机时发生未知错误：{e}")
        return False


if __name__ == "__main__":
    # 测试用
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    success = open_camera_system(None)
    if success:
        print("✅ 相机应用已启动")
    else:
        print("❌ 相机启动失败")
    root.mainloop()
