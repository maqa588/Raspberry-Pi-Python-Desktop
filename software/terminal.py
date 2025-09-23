# system/terminal.py
import platform
import subprocess
import tkinter as tk
from tkinter import messagebox
import sys
import os

current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file_path))
sys.path.insert(0, project_root)

from system.config import TERMINAL_WIDTH, TERMINAL_HEIGHT
from system.button.about import show_system_about, show_developer_about
from system.wireless.wifi import show_wifi_configure
from system.wireless.bluetooth import show_bluetooth_configure

class TerminalApp:
    def __init__(self, desktop_app):
        """
        初始化终端应用
        """
        self.root = None
        self.xterm_process = None
        self.term_frame = None
        self.menubar = None
        self.desktop_app = desktop_app
    
    def on_quit(self):
        """处理退出逻辑"""
        print("尝试退出...")
        if self.xterm_process and self.xterm_process.poll() is None:
            print("xterm 进程仍在运行，尝试终止...")
            self.xterm_process.terminate()
            # 等待进程退出，以防万一
            try:
                self.xterm_process.wait(timeout=2)
                print("xterm 进程已终止。")
            except subprocess.TimeoutExpired:
                print("无法在规定时间内终止 xterm，强制关闭。")
                self.xterm_process.kill()
        
        print("销毁 Tkinter 窗口...")
        if self.root:
            self.root.destroy()
        print("退出完成。")
    
    def create_gui(self):
        """创建 GUI 界面"""
        # 创建 Tkinter 窗口
        self.root = tk.Tk()
        self.root.title("嵌入式终端")
        self.root.geometry(f"{TERMINAL_WIDTH}x{TERMINAL_HEIGHT}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)

        # 创建一个 Frame 作为自定义顶部栏的容器
        top_bar_frame = tk.Frame(self.root, bg="lightgray", height=30)
        top_bar_frame.pack(side=tk.TOP, fill=tk.X)

        # 文件菜单按钮
        file_mb = tk.Menubutton(top_bar_frame, text="文件", activebackground="gray", bg="lightgray")
        file_mb.pack(side=tk.LEFT, padx=5)
        file_menu = tk.Menu(file_mb, tearoff=0)
        file_menu.add_command(label="退出", command=self.on_quit)
        file_mb.config(menu=file_menu)

        # 关于菜单按钮
        about_mb = tk.Menubutton(top_bar_frame, text="关于", activebackground="gray", bg="lightgray")
        about_mb.pack(side=tk.LEFT, padx=5)
        about_menu = tk.Menu(about_mb, tearoff=0)
        about_menu.add_command(label="系统信息", command=lambda: show_system_about(self.root))
        about_menu.add_command(label="关于开发者", command=lambda: show_developer_about(self.root))
        about_mb.config(menu=about_menu)

        # 设置菜单按钮
        edit_mb = tk.Menubutton(top_bar_frame, text="设置", activebackground="gray", bg="lightgray")
        edit_mb.pack(side=tk.LEFT, padx=5)
        edit_menu = tk.Menu(edit_mb, tearoff=0)
        edit_menu.add_command(label="WIFI开关", command=lambda: show_wifi_configure(self.root))
        edit_menu.add_command(label="蓝牙开关", command=lambda: show_bluetooth_configure(self.root))
        edit_mb.config(menu=edit_menu)

        # 退出按钮
        quit_button = tk.Button(top_bar_frame, text="X", command=self.on_quit, relief=tk.FLAT, bg="lightgray", fg="red", padx=5)
        quit_button.pack(side=tk.RIGHT, padx=5)

        # 创建一个 Frame 作为 xterm 的容器
        self.term_frame = tk.Frame(self.root, width=480, height=290)
        self.term_frame.pack(fill=tk.BOTH, expand=True)

        # 强制 Tkinter 立即更新窗口
        self.root.update_idletasks()
    
    def start_xterm(self):
        """启动 xterm 终端"""
        try:
            # 获取 Frame 的窗口 ID
            window_id = self.term_frame.winfo_id()

            # 使用 subprocess.Popen 启动 xterm 并获取进程对象
            self.xterm_process = subprocess.Popen(['xterm', '-into', str(window_id)])
            return True
        except Exception as e:
            messagebox.showerror("启动 xterm 失败", str(e))
            return False
    
    def try_alternative_terminals(self):
        """尝试其他终端程序"""
        for cmd in (["x-terminal-emulator"], ["lxterminal"], ["gnome-terminal"], ["konsole"]):
            try:
                subprocess.Popen(cmd)
                return True
            except FileNotFoundError:
                continue
        messagebox.showwarning("无终端", "未能找到任何终端程序。")
        return False
    
    def open_linux_terminal(self):
        """在 Linux 系统上打开终端"""
        try:
            # 检查 xterm 是否安装
            subprocess.run(["xterm", "-v"], check=True, 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            self.create_gui()
            if self.start_xterm():
                # 启动 Tkinter 主循环
                self.root.mainloop()
                return True
            return False
            
        except (FileNotFoundError, subprocess.CalledProcessError):
            messagebox.showwarning("Xterm 未找到", "未能找到 xterm 程序，将尝试打开外部终端。")
            return self.try_alternative_terminals()
    
    def open_macos_terminal(self):
        """在 macOS 系统上打开终端"""
        try:
            subprocess.Popen(["open", "-a", "Terminal"])
            return True
        except Exception as e:
            messagebox.showerror("打开终端失败", str(e))
            return False
    
    def open_windows_terminal(self):
        """在 Windows 系统上打开终端"""
        try:
            subprocess.Popen(["start", "cmd"], shell=True)
            return True
        except Exception as e:
            messagebox.showerror("打开终端失败", str(e))
            return False
    
    def open_terminal_system(self):
        """
        跨平台打开终端的逻辑。
        在 Linux / 树莓派上实现 tkinter 中植入 xterm 的界面。
        返回 True 表示成功，False 表示失败。
        """
        system = platform.system()
        
        try:
            if system == "Darwin":
                return self.open_macos_terminal()
            elif system == "Linux":
                return self.open_linux_terminal()
            elif system == "Windows":
                return self.open_windows_terminal()
            else:
                messagebox.showwarning("不支持的系统", f"系统 {system} 暂不支持打开终端")
                return False
        except Exception as e:
            messagebox.showerror("打开终端失败", str(e))
            return False

# 全局函数，保持向后兼容
def open_terminal_system(desktop_app=None):
    """全局函数，创建 TerminalApp 实例并打开终端"""
    app = TerminalApp(desktop_app)
    return app.open_terminal_system()

# 如果直接运行此文件，可以测试功能
if __name__ == "__main__":
    app = TerminalApp()
    result = app.open_terminal_system()
    print(f"终端打开结果: {result}")
