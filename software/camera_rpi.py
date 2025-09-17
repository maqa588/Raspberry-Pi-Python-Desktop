import os
import sys

# 动态获取项目根目录并添加到 sys.path
current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file_path))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import datetime
import tkinter as tk
from tkinter import messagebox
from picamera2 import Picamera2
from PIL import Image, ImageTk
import numpy as np

# 从正确的路径导入模块
from system.button.about import show_system_about, show_developer_about

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
        # 移除 main_frame 上的 pady，并使用 fill=tk.BOTH, expand=True 确保其填充所有可用空间
        # 注意：菜单栏的高度通常由 Tkinter 自动管理，这里假设它占用 30px
        main_frame = tk.Frame(self.master, bg="grey") # 暂时用灰色背景查看其边界
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=0, padx=0) # 关键：移除默认的pady

        # 左侧相机预览框架
        left_frame = tk.Frame(main_frame, width=387, height=290, bg='black')
        # 确保 left_frame 的 pack 参数没有额外的 pady
        left_frame.pack(side=tk.LEFT, padx=(0, 10), pady=0) # 关键：移除 pady
        left_frame.pack_propagate(False) # 防止子组件调整框架大小

        # 摄像头预览显示区域
        self.preview_label = tk.Label(left_frame, bg='black')
        self.preview_label.pack(fill=tk.BOTH, expand=True)

        # 右侧控制按钮框架
        right_frame = tk.Frame(main_frame)
        # 确保 right_frame 的 pack 参数没有额外的 pady
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=0) # 关键：移除 pady

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

# 如果你在主程序中通过 subprocess 启动这个脚本，
# 确保主程序传递的命令行参数是 "camera_rpi_only"
# 这样就可以在 app.py 里正确地分流到这个脚本了。
if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()