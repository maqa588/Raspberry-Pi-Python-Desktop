# system/app_logic.py
import tkinter as tk
import threading
from tkinter import messagebox
import tkinter.colorchooser as colorchooser
import platform
import psutil
from PIL import Image, ImageTk
import os

from system.config import WINDOW_WIDTH, WINDOW_HEIGHT
from software.terminal import open_terminal_system
from software.browser import open_browser_system

class LogicHandler:
    def __init__(self, master, app_instance):
        self.master = master
        self.app = app_instance
        self._status_reset_after_id = None
        self.icons = {}
        self.developer_avatar_path = "icons/developer_avatar.png"

    def edit_background_color(self):
        # 弹出一个颜色选择对话框
        color_code = colorchooser.askcolor(title="选择桌面背景颜色")
        if color_code:
            # color_code是一个元组 ((R, G, B), '#hex_code')
            # 我们只需要十六进制的颜色码
            hex_color = color_code[1]
            self.app.ui.canvas.config(bg=hex_color)
            self.app.icon_manager.save_background_color(hex_color) # 将颜色传递给 IconManager
            self.app.ui.set_status_text(f"背景颜色已更改为: {hex_color}")
            self.open_reset()

    def show_system_about(self):
        # 定义子窗口尺寸
        win_width, win_height = 350, 200
        # 计算居中位置
        x_pos = (WINDOW_WIDTH - win_width) // 2
        y_pos = (WINDOW_HEIGHT - win_height) // 2
        
        # 创建一个顶级（悬浮）窗口
        about_window = tk.Toplevel(self.master)
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
        about_window = tk.Toplevel(self.master)
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
            "版本: 0.1.0-alpha",
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

    def get_command_for_icon(self, icon_id):
        if icon_id == "terminal":
            return self.open_terminal
        elif icon_id == "browser":
            return self.open_browser
        elif icon_id == "files":
            return self.open_file_manager
        elif icon_id == "editor":
            return self.open_editor
        else:
            return lambda: messagebox.showinfo("操作", f"双击了图标: {icon_id}\n请在此处实现您的功能！")

    def open_terminal(self):
        loading_window = self._show_loading_message("执行打开终端的操作...")
        def run_task():
            success = open_terminal_system()
            self.master.after(0, self._update_status_and_destroy_window, success, loading_window, "终端")
        threading.Thread(target=run_task).start()

    def open_browser(self):
        loading_window = self._show_loading_message("执行打开浏览器的操作...")
        
        # run_task 函数需要访问 self 来获取 self.app
        def run_task():
            # 在这里将 app_instance (即 self.app) 传递给函数
            success = open_browser_system(self.app)
            self.master.after(0, self._update_status_and_destroy_window, success, loading_window, "浏览器")
        
        threading.Thread(target=run_task).start()

    def open_file_manager(self):
        print("执行打开文件管理器的操作...")
        messagebox.showinfo("操作", "正在打开文件管理器...")

    def open_editor(self):
        print("执行打开文件编辑器的操作...")
        messagebox.showinfo("操作", "正在打开文件编辑器...")

    def menu_placeholder_function(self):
        messagebox.showinfo("提示", "此菜单功能待实现！")
        
    def open_reset(self):
        if hasattr(self, "_status_reset_after_id") and self._status_reset_after_id is not None:
            self.master.after_cancel(self._status_reset_after_id)
        self._status_reset_after_id = self.master.after(3000, lambda: self.app.ui.set_status_text("就绪"))

    def _show_loading_message(self, message):
        loading_window = tk.Toplevel(self.master)
        loading_window.title("请稍候")
        loading_window.update_idletasks()
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        loading_width = loading_window.winfo_width()
        loading_height = loading_window.winfo_height()
        position_x = parent_x + (parent_width // 2) - (loading_width // 2)
        position_y = parent_y + (parent_height // 2) - (loading_height // 2)
        loading_window.geometry(f"+{position_x}+{position_y}")
        loading_window.wait_visibility()
        loading_window.grab_set()
        tk.Label(loading_window, text=message, padx=20, pady=10).pack(pady=10)
        return loading_window
    
    def _update_status_and_destroy_window(self, success, window, app_name):
        try:
            window.destroy()
        except tk.TclError:
            pass
        if success:
            self.app.ui.set_status_text(f"{app_name}已启动")
            self.open_reset()
        else:
            self.app.ui.set_status_text(f"打开{app_name}失败")
            self.open_reset()

    def start_pan(self, event):
        if not self.app.ui.canvas.find_withtag(tk.CURRENT):
             self.app.ui.canvas.scan_mark(event.x, event.y)

    def pan_view(self, event):
        if not self.app.ui.canvas.find_withtag(tk.CURRENT):
            self.app.ui.canvas.scan_dragto(event.x, event.y, gain=1)