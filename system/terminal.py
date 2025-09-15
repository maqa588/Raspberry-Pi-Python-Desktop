# system/terminal.py

import platform
import subprocess
from tkinter import messagebox

def open_terminal_system():
    """
    跨平台打开终端的逻辑。
    在 Linux / 树莓派上尝试几个 terminal 程序，不保证全屏。
    返回 True 表示成功启动 terminal，False 或抛异常表示失败。
    """
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["open", "-a", "Terminal"])
            return True
        elif system == "Linux":
            # 你可以根据 Raspberry Pi 上实际安装什么 terminal 来修改
            # 比如 LXTerminal, xterm, 或者其它
            for cmd in (["x-terminal-emulator", "-e", "bash"], ["lxterminal"], ["xterm"]):
                try:
                    subprocess.Popen(cmd)
                    return True
                except FileNotFoundError:
                    continue
            # 如果都没找到 terminal 程序
            messagebox.showwarning("No terminal", "未能找到终端程序，请在系统中安装或配置")
            return False
        elif system == "Windows":
            # Windows 下打开 cmd
            subprocess.Popen(["start", "cmd"], shell=True)
            return True
        else:
            messagebox.showwarning("Unsupported OS", f"系统 {system} 暂不支持打开终端")
            return False
    except Exception as e:
        messagebox.showerror("Open terminal failed", str(e))
        return False