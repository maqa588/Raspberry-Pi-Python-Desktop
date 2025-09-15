# system/terminal.py

# system/terminal.py

import platform
import subprocess
import tkinter as tk
from tkinter import messagebox
import os

WINDOW_WIDTH = 480
WINDOW_HEIGHT = 290

def open_terminal_system():
    """
    跨平台打开终端的逻辑。
    在 Linux / 树莓派上实现 tkinter 中植入 xterm 的界面。
    返回 True 表示成功，False 表示失败。
    """
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["open", "-a", "Terminal"])
            return True
        elif system == "Linux":
            # 在 Linux 上尝试植入 xterm
            try:
                # 检查 xterm 是否安装
                subprocess.run(["xterm", "-v"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # 创建 Tkinter 窗口
                root = tk.Tk()
                root.title("嵌入式终端")
                root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
                
                # 创建顶部菜单栏
                menubar = tk.Menu(root)
                file_menu = tk.Menu(menubar, tearoff=0)
                file_menu.add_command(label="退出", command=root.destroy)
                menubar.add_cascade(label="文件", menu=file_menu)
                root.config(menu=menubar)

                # 创建一个 Frame 作为 xterm 的容器
                term_frame = tk.Frame(root, width=480, height=290)
                term_frame.pack(fill=tk.BOTH, expand=True)

                # 获取 Frame 的窗口 ID
                window_id = term_frame.winfo_id()

                # 启动 xterm 并嵌入到 Frame 中
                os.system(f'xterm -into {window_id} &')

                # 启动 Tkinter 主循环
                root.mainloop()
                return True
                
            except (FileNotFoundError, subprocess.CalledProcessError):
                # 如果 xterm 未安装或执行失败，则退回旧的打开方式
                messagebox.showwarning("Xterm 未找到", "未能找到 xterm 程序，将尝试打开外部终端。")
                for cmd in (["x-terminal-emulator"], ["lxterminal"], ["gnome-terminal"], ["konsole"]):
                    try:
                        subprocess.Popen(cmd)
                        return True
                    except FileNotFoundError:
                        continue
                messagebox.showwarning("无终端", "未能找到任何终端程序。")
                return False
                
        elif system == "Windows":
            subprocess.Popen(["start", "cmd"], shell=True)
            return True
        else:
            messagebox.showwarning("不支持的系统", f"系统 {system} 暂不支持打开终端")
            return False
    except Exception as e:
        messagebox.showerror("打开终端失败", str(e))
        return False