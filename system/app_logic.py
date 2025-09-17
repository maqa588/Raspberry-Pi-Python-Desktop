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
from software.camera import open_camera_system

class LogicHandler:
    # 构造函数现在接收 app_instance, icon_manager 和 ui 的引用
    def __init__(self, app_instance, icon_manager, ui):
        self.app = app_instance
        self.icon_manager = icon_manager
        self.ui = ui
        self.master = app_instance.root # 假设 root 是主窗口
        self._status_reset_after_id = None
        self.icons = {} # 这个icons属性可能不再需要，因为可以通过self.icon_manager访问
        self.developer_avatar_path = "icons/developer_avatar.png"

    def edit_background_color(self):
        """
        弹出颜色选择对话框，更改桌面背景的颜色
        """
        color_code = colorchooser.askcolor(title="选择桌面背景颜色")
        if color_code:
            hex_color = color_code[1]
            self.ui.canvas.config(bg=hex_color)
            self.icon_manager.save_background_color(hex_color)
            self.ui.set_status_text(f"背景颜色已更改为: {hex_color}")
            self.open_reset()
    
    def edit_label_color(self):
        """
        弹出颜色选择对话框，更改所有图标文字的颜色
        """
        color_code = colorchooser.askcolor(title="选择图标文字颜色")
        if color_code:
            hex_color = color_code[1]
            self.icon_manager.save_label_color(hex_color)
            self.ui.set_status_text(f"图标文字颜色已更改为: {hex_color}")
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
        elif icon_id == "camera":
            return self.open_camera
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
        
        def run_task():
            success = open_browser_system(self.app)
            self.master.after(0, self._update_status_and_destroy_window, success, loading_window, "浏览器")
        
        threading.Thread(target=run_task).start()

    def open_file_manager(self):
        loading_window = self._show_loading_message("执行打开文件浏览器的操作...")
        
        def run_task():
            success = open_file_manager(self.app)
            self.master.after(0, self._update_status_and_destroy_window, success, loading_window, "文件浏览器")
        
        threading.Thread(target=run_task).start()

    def open_editor(self):
        print("执行打开文件编辑器的操作...")
        messagebox.showinfo("操作", "正在打开文件编辑器...")

    def open_camera(self):
        loading_window = self._show_loading_message("执行打开相机的操作...")
        def run_task():
            success = open_camera_system(self.app)
            self.master.after(0, self._update_status_and_destroy_window, success, loading_window, "相机")
        threading.Thread(target=run_task).start()

    def menu_placeholder_function(self):
        messagebox.showinfo("提示", "此菜单功能待实现！")
        
    def open_reset(self):
        if self._status_reset_after_id is not None:
            self.master.after_cancel(self._status_reset_after_id)
        self._status_reset_after_id = self.master.after(3000, lambda: self.ui.set_status_text("就绪"))

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
            self.ui.set_status_text(f"{app_name}已启动")
            self.open_reset()
        else:
            self.ui.set_status_text(f"打开{app_name}失败")
            self.open_reset()

    def start_pan(self, event):
        if not self.ui.canvas.find_withtag(tk.CURRENT):
             self.ui.canvas.scan_mark(event.x, event.y)

    def pan_view(self, event):
        if not self.ui.canvas.find_withtag(tk.CURRENT):
            self.ui.canvas.scan_dragto(event.x, event.y, gain=1)