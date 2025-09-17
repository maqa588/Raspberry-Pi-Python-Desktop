import os
import signal
import datetime
import subprocess
import tkinter as tk
from tkinter import messagebox
from picamera2 import Picamera2
from PIL import Image, ImageTk
import numpy as np
from system.button.about import show_system_about, show_developer_about
from system.config import WINDOW_HEIGHT, WINDOW_WIDTH

# --- 相机应用主类 ---
class CameraApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Raspberry Pi Camera")
        self.master.geometry("480x320") # 调整窗口尺寸
        self.master.resizable(False, False)

        # 初始化 Picamera2 实例并配置
        self.picam2 = Picamera2()
        self.preview_config = self.picam2.create_preview_configuration(main={"size": (640, 480)})
        self.picam2.configure(self.preview_config)

        self.preview_label = None
        self.create_menu()
        self.init_ui()

        # 启动相机预览
        self.picam2.start()
        self.update_preview()

    def create_menu(self):
        menubar = tk.Menu(self.master)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="拍照", command=self.take_photo)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.confirm_exit)
        menubar.add_cascade(label="文件", menu=file_menu)

        about_menu = tk.Menu(menubar, tearoff=0)
        about_menu.add_command(label="系统信息", command=lambda: show_system_about(self.master))
        about_menu.add_command(label="关于开发者", command=lambda: show_developer_about(self.master))
        menubar.add_cascade(label="关于", menu=about_menu)

        self.master.config(menu=menubar)

    def init_ui(self):
        # 创建主框架来容纳相机预览和按钮
        main_frame = tk.Frame(self.master, bg="grey")
        main_frame.place(x=0, y=30, width={WINDOW_WIDTH}, height={WINDOW_HEIGHT}) # 占据菜单栏以下的所有空间

        # 左侧相机预览框架
        left_frame = tk.Frame(main_frame, width=387, height=290, bg='black')
        left_frame.pack(side=tk.LEFT, padx=(0, 10), pady=0)
        left_frame.pack_propagate(False) # 防止子组件调整框架大小

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
        
        # 退出事件绑定
        self.master.protocol("WM_DELETE_WINDOW", self.confirm_exit)

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

# 捕获 Ctrl+C 信号，实现优雅退出
def sigint_handler(sig, frame):
    root = tk.Tk()
    app = root.winfo_children()[0] if root.winfo_children() else None
    if isinstance(app, CameraApp):
        app.picam2.stop()
    root.quit()