import os
import sys

current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file_path))
sys.path.insert(0, project_root)

from system.button.about import show_system_about, show_developer_about

import datetime
import tkinter as tk
from tkinter import messagebox
from picamera2 import Picamera2
from PIL import Image, ImageTk
import numpy as np

# --- 相机应用主类 ---
class CameraApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Raspberry Pi Camera")
        self.master.geometry("480x320")
        self.master.resizable(False, False)

        # 初始化 Picamera2 实例并配置
        self.picam2 = Picamera2()
        self.preview_config = self.picam2.create_preview_configuration(main={"size": (640, 480)})
        self.picam2.configure(self.preview_config)

        self.preview_label = None
        
        # 退出事件绑定，这里使用 confirm_exit
        self.master.protocol("WM_DELETE_WINDOW", self.confirm_exit)

        self.init_ui()

        # 启动相机预览
        self.picam2.start()
        self.update_preview()

    def init_ui(self):
        # ------------------------------------------------------------------
        # 创建自定义顶部栏
        # ------------------------------------------------------------------
        top_bar_frame = tk.Frame(self.master, bg="lightgray", height=30)
        top_bar_frame.pack(side=tk.TOP, fill=tk.X)

        # 文件菜单按钮
        file_mb = tk.Menubutton(top_bar_frame, text="文件", activebackground="gray", bg="lightgray")
        file_mb.pack(side=tk.LEFT, padx=5)
        file_menu = tk.Menu(file_mb, tearoff=0)
        file_menu.add_command(label="拍照", command=self.take_photo)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.confirm_exit)
        file_mb.config(menu=file_menu)

        # 关于菜单按钮
        about_mb = tk.Menubutton(top_bar_frame, text="关于", activebackground="gray", bg="lightgray")
        about_mb.pack(side=tk.LEFT, padx=5)
        about_menu = tk.Menu(about_mb, tearoff=0)
        about_menu.add_command(label="系统信息", command=lambda: show_system_about(self.master))
        about_menu.add_command(label="关于开发者", command=lambda: show_developer_about(self.master))
        about_mb.config(menu=about_menu)

        # 自定义退出按钮
        quit_button = tk.Button(top_bar_frame, text="X", command=self.confirm_exit, relief=tk.FLAT, bg="lightgray", fg="red", padx=5)
        quit_button.pack(side=tk.RIGHT, padx=5)

        # ------------------------------------------------------------------
        
        # 创建主框架来容纳相机预览和按钮
        main_frame = tk.Frame(self.master, bg="grey")
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 左侧相机预览框架
        left_frame = tk.Frame(main_frame, width=387, height=290, bg='black')
        left_frame.pack(side=tk.LEFT, padx=(0, 10), pady=0)
        left_frame.pack_propagate(False)

        # 摄像头预览显示区域
        self.preview_label = tk.Label(left_frame, bg='black')
        self.preview_label.pack(fill=tk.BOTH, expand=True)

        # 右侧控制按钮框架
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=0)

        # 按钮布局（竖向放置）
        btn_photo = tk.Button(right_frame, text="拍照", command=self.take_photo, width=12)
        btn_photo.pack(pady=(5, 5))

        btn_exit = tk.Button(right_frame, text="返回", command=self.confirm_exit, width=12)
        btn_exit.pack(pady=(5, 5))
        
        # 强制 Tkinter 立即更新窗口
        self.master.update_idletasks()

    def update_preview(self):
        frame = self.picam2.capture_array()
        image = Image.fromarray(frame).resize((387, 290))
        
        photo = ImageTk.PhotoImage(image)
        self.preview_label.config(image=photo)
        self.preview_label.image = photo
        
        self.master.after(30, self.update_preview)

    def take_photo(self):
        if not os.path.exists("photos"):
            os.makedirs("photos")
        fname = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".jpg"
        path = os.path.join("photos", fname)

        cap_cfg = self.picam2.create_still_configuration(main={"size": (2592, 1944)})
        self.picam2.switch_mode_and_capture_file(cap_cfg, path)
        messagebox.showinfo("照片已保存", f"保存为: {path}")

    def confirm_exit(self):
        if messagebox.askyesno("退出", "你真的要退出吗？"):
            self.picam2.stop()
            self.master.destroy()

# 如果你在主程序中通过 subprocess 启动这个脚本，
# 确保主程序传递的命令行参数是 "camera_rpi_only"
# 这样就可以在 app.py 里正确地分流到这个脚本了。
if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()