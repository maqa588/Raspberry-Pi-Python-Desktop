import tkinter as tk
from tkinter import messagebox
import subprocess
import platform
import threading

from system.config import WINDOW_WIDTH, WINDOW_HEIGHT

def get_wifi_status():
    """
    检查当前Wi-Fi状态。
    返回 True 表示开启，False 表示关闭，None 表示未知或出错。
    """
    system = platform.system()
    if system == "Linux":
        try:
            # 尝试通过nmcli获取WLAN设备状态
            cmd = "nmcli -t -f DEVICE,STATE,TYPE dev status | grep 'wlan0'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if "connected" in result.stdout:
                return True
            elif "disconnected" in result.stdout or "unavailable" in result.stdout:
                return False
        except FileNotFoundError:
            messagebox.showerror("错误", "命令未找到，请确保系统命令可用。")
            return None
        except Exception as e:
            messagebox.showerror("错误", f"获取Wi-Fi状态时出错：{e}")
            return None
    else:
        # 非Linux系统，不执行任何操作
        return None
    return None

def toggle_wifi_status(current_status):
    """
    切换Wi-Fi状态。
    """
    system = platform.system()
    if system == "Linux":
        if current_status:
            cmd = "nmcli radio wifi off"
        else:
            cmd = "nmcli radio wifi on"
        try:
            # 使用Popen来避免UI卡死，并在新线程中执行
            threading.Thread(target=lambda: subprocess.run(cmd, shell=True)).start()
        except Exception as e:
            messagebox.showerror("错误", f"执行命令时出错：{e}")
    else:
        # 非Linux系统，不执行任何操作
        return

def update_ui(label, button, root):
    """
    更新UI以反映当前的Wi-Fi状态。
    """
    system = platform.system()
    if system != "Linux":
        label.config(text="该功能仅在树莓派上才可运行", fg="red")
        button.config(text="退出", command=root.destroy)
        return

    status = get_wifi_status()
    if status is None:
        label.config(text="状态未知")
        button.config(text="重试", command=lambda: toggle_wifi_status_and_update(label, button, root))
        return

    if status:
        label.config(text="Wi-Fi: 已开启", fg="green")
        button.config(text="关闭Wi-Fi")
    else:
        label.config(text="Wi-Fi: 已关闭", fg="black")
        button.config(text="开启Wi-Fi")

    # 重新绑定按钮的命令
    button.config(command=lambda: toggle_wifi_status_and_update(label, button, root))

def toggle_wifi_status_and_update(label, button, root):
    """
    切换Wi-Fi并更新UI。
    """
    current_status = get_wifi_status()
    if current_status is not None:
        toggle_wifi_status(current_status)
    # 延迟几秒后更新UI，给系统切换状态的时间
    root.after(3000, lambda: update_ui(label, button, root))

def show_wifi_configure(root):
    """
    显示Wi-Fi控制窗口。
    :param root: Tkinter 主窗口实例。
    """
    # 定义子窗口尺寸
    win_width, win_height = 200, 100
    # 计算居中位置
    x_pos = (WINDOW_WIDTH - win_width) // 2
    y_pos = (WINDOW_HEIGHT - win_height) // 2

    # 创建一个顶级（悬浮）窗口
    about_window = tk.Toplevel(root)
    about_window.title("Wi-Fi 控制")
    about_window.geometry(f"{win_width}x{win_height}+{x_pos}+{y_pos}")
    about_window.resizable(False, False)
    about_window.grab_set()  # 确保子窗口在主窗口之上

    # 创建一个Frame来组织内容
    main_frame = tk.Frame(about_window)
    main_frame.pack(pady=10)

    # 显示Wi-Fi状态的标签
    status_label = tk.Label(main_frame, text="正在获取Wi-Fi状态...", font=("Arial", 12))
    status_label.pack(pady=(0, 10))

    # 创建一个Frame来放置按钮
    button_frame = tk.Frame(main_frame)
    button_frame.pack()

    # 切换Wi-Fi状态的按钮
    toggle_button = tk.Button(button_frame, text="加载中...")
    toggle_button.pack(side=tk.LEFT, padx=5)

    # 退出按钮
    exit_button = tk.Button(button_frame, text="退出", command=about_window.destroy)
    exit_button.pack(side=tk.RIGHT, padx=5)

    # 初始更新UI
    update_ui(status_label, toggle_button, about_window)