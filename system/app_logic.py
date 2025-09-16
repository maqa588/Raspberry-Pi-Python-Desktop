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
from software.file_manager import open_file_manager

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
            success = open_terminal_system(self.app)
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
        loading_window = self._show_loading_message("执行打开文件浏览器的操作...")
        
        # run_task 函数需要访问 self 来获取 self.app
        def run_task():
            # 在这里将 app_instance (即 self.app) 传递给函数
            success = open_file_manager(self.app)
            self.master.after(0, self._update_status_and_destroy_window, success, loading_window, "文件浏览器")
        
        threading.Thread(target=run_task).start()

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