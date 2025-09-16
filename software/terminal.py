# system/terminal.py

import platform
import subprocess
import tkinter as tk
from tkinter import messagebox
import os
from system.config import WINDOW_WIDTH, WINDOW_HEIGHT
import psutil
from PIL import Image, ImageTk

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
        self.developer_avatar_path = "icons/developer_avatar.png"
    
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
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)

        # 创建顶部菜单栏
        self.menubar = tk.Menu(self.root)
        file_menu = tk.Menu(self.menubar, tearoff=0)
        file_menu.add_command(label="退出", command=self.on_quit)
        self.menubar.add_cascade(label="文件", menu=file_menu)
        about_menu = tk.Menu(self.menubar, tearoff=0)
        about_menu.add_command(label="系统信息", command=self.show_system_about)
        about_menu.add_command(label="关于开发者", command=self.show_developer_about)
        self.menubar.add_cascade(label="关于", menu=about_menu)
        self.root.config(menu=self.menubar)

        # 创建一个 Frame 作为 xterm 的容器
        self.term_frame = tk.Frame(self.root, width=480, height=290)
        self.term_frame.pack(fill=tk.BOTH, expand=True)

        # 强制 Tkinter 立即更新窗口
        self.root.update_idletasks()

    def show_system_about(self):
        # 定义子窗口尺寸
        win_width, win_height = 350, 200
        # 计算居中位置
        x_pos = (WINDOW_WIDTH - win_width) // 2
        y_pos = (WINDOW_HEIGHT - win_height) // 2
        
        # 创建一个顶级（悬浮）窗口
        about_window = tk.Toplevel(self.root)
        about_window.title("系统信息")
        about_window.geometry(f"{win_width}x{win_height}+{x_pos}+{y_pos}")
        about_window.resizable(False, False)

        # 创建一个标签列表，用于实时更新
        info_labels = []
        for _ in range(4):
            label = tk.Label(about_window, text="", font=("Helvetica", 12), justify="left")
            label.pack(anchor="w", padx=10, pady=5)
            info_labels.append(label)

        # 添加一个用于关闭窗口的按钮
        close_button = tk.Button(about_window, text="关闭", command=about_window.destroy)
        close_button.pack(pady=10)

        # 定义一个更新信息的函数
        def update_info():
            # 获取系统架构和发行版信息
            arch = platform.machine()
            distro_name = platform.platform(terse=True)
            
            # 获取内存和CPU信息
            mem = psutil.virtual_memory()
            cpu_usage = psutil.cpu_percent(interval=None) # interval=None表示非阻塞获取

            # 更新标签文本
            info_labels[0].config(text=f"系统架构: {arch}")
            info_labels[1].config(text=f"发行版: {distro_name}")
            info_labels[2].config(text=f"内存占用: {mem.percent}% ({mem.used / (1024**3):.2f} GB)")
            info_labels[3].config(text=f"CPU 占用: {cpu_usage}%")
            
            # 每秒钟调用一次自身以实现实时更新
            about_window.after(1000, update_info)

        # 首次调用函数以显示信息
        update_info()

    def show_developer_about(self):
        # 定义子窗口尺寸
        win_width, win_height = 450, 250
        # 计算居中位置
        x_pos = (WINDOW_WIDTH - win_width) // 2
        y_pos = (WINDOW_HEIGHT - win_height) // 2

        # 创建一个顶级（悬浮）窗口
        about_window = tk.Toplevel(self.root)
        about_window.title("关于开发者")
        about_window.geometry(f"{win_width}x{win_height}+{x_pos}+{y_pos}")
        about_window.resizable(False, False)

        main_frame = tk.Frame(about_window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # --- 左侧：开发者头像 ---
        left_frame = tk.Frame(main_frame, width=150, height=150) # 预设头像区域大小
        left_frame.pack(side="left", fill="y", padx=(0, 10))
        left_frame.pack_propagate(False) # 防止 Frame 随内容大小变化

        avatar_label = tk.Label(left_frame)
        avatar_label.pack(expand=True)

        # 尝试加载开发者头像
        try:
            # 拼接正确的相对路径
            current_script_dir = os.path.dirname(__file__) # 获取当前脚本所在目录
            avatar_full_path = os.path.join(current_script_dir, "..", self.developer_avatar_path)
            
            original_image = Image.open(avatar_full_path)
            # 缩放图片以适应 Frame 大小，保持宽高比
            original_image.thumbnail((140, 140), Image.LANCZOS) # LANCZOS 是高质量缩放滤镜
            self.developer_photo = ImageTk.PhotoImage(original_image) # 保持引用，防止被垃圾回收

            avatar_label.config(image=self.developer_photo)
        except FileNotFoundError:
            avatar_label.config(text="无头像", font=("Helvetica", 12))
            print(f"警告: 找不到开发者头像文件: {self.developer_avatar_path}")
        except Exception as e:
            avatar_label.config(text="加载头像失败", font=("Helvetica", 10))
            print(f"加载开发者头像时发生错误: {e}")

        # --- 右侧：详细信息 ---
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True)

        # 开发者信息列表
        developer_info_list = [
            "开发者: Spencer Maqa",
            "项目名称: Raspberry Pi Python Desktop",
            "版本: 0.1.1-alpha",
            "联系方式: maqa588@163.com",
            "项目仓库: https://github.com/maqa588/",
            "Raspberry-Pi-Python-Desktop/",
            "辽宁大学Python程序设计课程 课程设计"
        ]

        # 逐行创建标签显示信息
        for info_text in developer_info_list:
            label = tk.Label(right_frame, text=info_text, font=("Helvetica", 10), justify="left", anchor="w")
            label.pack(fill="x", pady=2)

        # --- 底部：关闭按钮 ---
        close_button = tk.Button(about_window, text="关闭", command=about_window.destroy, font=("Helvetica", 10))
        close_button.pack(pady=10) # 底部按钮与主内容之间留出一些间距
    
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
