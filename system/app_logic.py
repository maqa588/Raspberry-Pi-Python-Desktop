import tkinter as tk
import threading
from tkinter import messagebox
import tkinter.colorchooser as colorchooser
import platform
import psutil
from PIL import Image, ImageTk
import os
import sys 
import traceback 
import inspect
from pathlib import Path
import subprocess

# --- 辅助函数：启动独立应用 (支持类和函数两种入口) ---
def start_sub_process_app(module_path: str, entry_name: str):
    """
    【此函数在子进程中执行】
    通过动态导入并调用模块内的主类/函数来启动独立应用窗口。
    它假设项目根目录已在 sys.path 中。
    
    Args:
        module_path (str): 要导入的模块路径，例如 'software.deepseek_app'。
        entry_name (str): 模块内的主类或主启动函数的名称，例如 'App' 或 'create_pong_game'。
    """
    try:
        # 1. 动态导入目标模块
        module = __import__(module_path, fromlist=[entry_name])
        
        # 2. 获取入口点
        entry_point = getattr(module, entry_name)
        
        print(f"子进程启动模块: {module_path}")
        
        if inspect.isclass(entry_point):
            # 适用于标准的 Tkinter App 类 (e.g., CameraApp)
            app_root = tk.Tk()
            app_root.title(module_path.split('.')[-1].replace('_', ' ').title())
            entry_point(app_root) 
            app_root.mainloop()
        elif callable(entry_point):
            # 适用于启动函数 (e.g., create_deepseek_ui, create_pong_game)
            entry_point()
        else:
             messagebox.showerror("启动失败", f"模块 {module_path} 中的入口 {entry_name} 既不是类也不是可执行函数。")
        
    except ImportError:
        messagebox.showerror("启动失败", f"无法导入模块: {module_path}。请检查文件路径和依赖。")
        traceback.print_exc()
    except AttributeError:
        messagebox.showerror("启动失败", f"模块 {module_path} 缺少入口类/函数: {entry_name}。")
        traceback.print_exc()
    except Exception as e:
        messagebox.showerror("启动失败", f"启动应用 {module_path} 时发生未知错误: {e}")
        traceback.print_exc()
    
    # 子进程执行完毕后退出
    sys.exit()


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
        # 所有的 open_xxx 方法都委托给 _launch_app_thread
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
        elif icon_id == "rss_reader":
            return self.open_rss_reader
        else:
            return lambda: messagebox.showinfo("操作", f"双击了图标: {icon_id}\n请在此处实现您的功能！")

    def _launch_app_thread(self, app_key, app_name):
        """通用的应用启动函数，使用线程来避免阻塞主UI。"""
        # 确保启动器函数存在
        launcher_func = self.app_launchers.get(app_key)
        if not launcher_func:
            self._update_status_and_destroy_window(False, None, app_name)
            return

        loading_window = self._show_loading_message(f"执行打开{app_name}的操作...")
        
        def run_task():
            # launcher_func 负责调用 subprocess.Popen
            try:
                # 启动函数通常需要知道项目根路径或其他上下文，这里我们假设它只接收 app_instance
                # 在 app.py 中，open_xxx 函数已经被定义为 subprocess.Popen 的封装
                success = launcher_func(self.app)
                self.master.after(0, self._update_status_and_destroy_window, success, loading_window, app_name)
            except Exception as e:
                print(f"Error launching {app_name}: {e}")
                traceback.print_exc()
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
        
    def open_rss_reader(self):
        self._launch_app_thread("rss_reader", "RSS 阅读器")

    def menu_placeholder_function(self):
        messagebox.showinfo("提示", "此菜单功能待实现！")
        
    def open_reset(self):
        if self._status_reset_after_id is not None:
            self.master.after_cancel(self._status_reset_after_id)
        self._status_reset_after_id = self.master.after(3000, lambda: self.ui.set_status_text("就绪"))

    def _show_loading_message(self, message):
        loading_window = tk.Toplevel(self.master)
        # 设置窗口样式和居中
        loading_window.title("请稍候")
        loading_window.config(bg="#34495e")
        loading_window.attributes('-alpha', 0.95) # 半透明
        loading_window.overrideredirect(True) # 隐藏边框

        label = tk.Label(loading_window, text=message, padx=20, pady=10, bg="#34495e", fg="white", font=('Arial', 10, 'bold'))
        label.pack(pady=10)
        
        # 居中逻辑
        self.master.update_idletasks()
        loading_width = label.winfo_reqwidth() + 40
        loading_height = label.winfo_reqheight() + 20
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        position_x = parent_x + (parent_width // 2) - (loading_width // 2)
        position_y = parent_y + (parent_height // 2) - (loading_height // 2)
        loading_window.geometry(f"{loading_width}x{loading_height}+{position_x}+{position_y}")
        
        loading_window.wait_visibility()
        loading_window.grab_set()
        return loading_window
    
    def _update_status_and_destroy_window(self, success, window, app_name):
        # 确保窗口关闭前解除 grab 状态
        if window:
            try:
                window.grab_release()
                window.destroy()
            except tk.TclError:
                pass
        
        if success:
            self.ui.set_status_text(f"{app_name}已启动")
            self.open_reset()
        else:
            # 只有当 window 为 None 时，才弹错误框 (这种情况应该极少发生)
            if window is None:
                 messagebox.showerror("启动失败", f"打开{app_name}失败，可能是启动器函数不存在。")
            self.ui.set_status_text(f"打开{app_name}失败")
            self.open_reset()

    def start_pan(self, event):
        if not self.ui.canvas.find_withtag(tk.CURRENT):
             self.ui.canvas.scan_mark(event.x, event.y)

    def pan_view(self, event):
        if not self.ui.canvas.find_withtag(tk.CURRENT):
            self.ui.canvas.scan_dragto(event.x, event.y, gain=1)