import tkinter as tk
import threading
from tkinter import messagebox
import tkinter.colorchooser as colorchooser
import platform
import psutil
from PIL import Image, ImageTk
import os

class LogicHandler:
    def __init__(self, app_instance, icon_manager, ui, app_launchers):
        self.app = app_instance
        self.icon_manager = icon_manager
        self.ui = ui
        self.master = app_instance.root
        self._status_reset_after_id = None
        self.icons = {}
        self.developer_avatar_path = "icons/developer_avatar.png"
        
        # 接收外部传入的启动函数字典
        self.app_launchers = app_launchers

    def edit_background_color(self):
        color_code = colorchooser.askcolor(title="选择桌面背景颜色")
        if color_code:
            hex_color = color_code[1]
            self.ui.canvas.config(bg=hex_color)
            self.icon_manager.save_background_color(hex_color)
            self.ui.set_status_text(f"背景颜色已更改为: {hex_color}")
            self.open_reset()
    
    def edit_label_color(self):
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
        elif icon_id == "deepseek":
            return self.open_deepseek
        elif icon_id == "games":
            return self.open_game
        elif icon_id == "rss_reader": # <-- 新增：RSS 阅读器图标的映射
            return self.open_rss_reader
        else:
            return lambda: messagebox.showinfo("操作", f"双击了图标: {icon_id}\n请在此处实现您的功能！")

    def _launch_app_thread(self, app_key, app_name):
        """通用的应用启动函数，使用线程来避免阻塞主UI。"""
        loading_window = self._show_loading_message(f"执行打开{app_name}的操作...")
        
        def run_task():
            # 从字典中获取并调用对应的启动函数
            launcher_func = self.app_launchers.get(app_key)
            if launcher_func:
                # 启动函数需要接收 app_instance 作为参数
                success = launcher_func(self.app)
                self.master.after(0, self._update_status_and_destroy_window, success, loading_window, app_name)
            else:
                self.master.after(0, self._update_status_and_destroy_window, False, loading_window, app_name)
        
        threading.Thread(target=run_task).start()

    def open_terminal(self):
        self._launch_app_thread("terminal", "终端")

    def open_browser(self):
        self._launch_app_thread("browser", "浏览器")

    def open_file_manager(self):
        self._launch_app_thread("file_manager", "文件浏览器")

    def open_editor(self):
        self._launch_app_thread("editor", "文件编辑器")

    def open_camera(self):
        self._launch_app_thread("camera", "相机")
    
    def open_deepseek(self):
        self._launch_app_thread("deepseek", "Deepseek")

    def open_game(self):
        self._launch_app_thread("games", "游戏")
        
    def open_rss_reader(self): # <-- 新增：RSS 阅读器启动方法
        self._launch_app_thread("rss_reader", "RSS 阅读器")

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
