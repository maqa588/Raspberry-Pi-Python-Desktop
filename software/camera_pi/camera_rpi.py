import os
import sys
import datetime
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import numpy as np
import cv2 
import time 
import threading
import queue
from ultralytics import YOLO # 🚀 引入 Ultralytics YOLO 库

# ----------------------------------------------------------------------
# 路径调整以适应项目结构
# ----------------------------------------------------------------------
current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)

# 向上追溯三级以找到项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
sys.path.insert(0, project_root)
# --- 路径调整结束 ---

# 假设这些导入在项目中可用
try:
    from system.button.about import show_system_about, show_developer_about
except ImportError:
    def show_system_about(root): messagebox.showinfo("系统信息", "此为系统信息占位符。")
    def show_developer_about(root): messagebox.showinfo("开发者信息", "此为开发者信息占位符。")
    print("警告: 未能导入 system.button.about，使用占位函数。")

# ----------------------------------------------------------------------
# 树莓派及模型配置
# ----------------------------------------------------------------------
try:
    # 尝试导入 Picamera2
    from picamera2 import Picamera2
except ImportError:
    messagebox.showerror("依赖缺失", "请确保安装了 picamera2, opencv-python 和 ultralytics。")
    class Picamera2:
        def __init__(self, *args, **kwargs): raise ImportError("picamera2 not found")
        def start(self): pass
        def configure(self, *args): pass
        def capture_array(self): return np.zeros((480, 640, 3), dtype=np.uint8) 
        def stop(self): pass

# --- NCNN 模型文件路径 (Ultralytics 需要导出的模型文件夹路径) ---
# 注意：'yolo11n_ncnn_model' 必须是一个包含 param 和 bin 文件的目录
MODEL_PATH = os.path.join(current_dir, "models", "yolo11n_ncnn_model") 
# 检查模型文件夹是否存在
if not os.path.isdir(MODEL_PATH):
    print(f"❌ 警告: NCNN 模型文件夹未找到于 {MODEL_PATH}")


# --- 常量定义 ---
CONFIDENCE_THRESHOLD = 0.4 
NMS_THRESHOLD = 0.4        
CAMERA_WIDTH = 640        
CAMERA_HEIGHT = 480       
TARGET_CAP_FPS = 30
FRAME_TIME_MS = 1000 / TARGET_CAP_FPS
PREDICT_IMG_SIZE = 480    # NCNN 模型输入尺寸 (确保与导出的模型匹配)
CAMERA_ASPECT_RATIO = CAMERA_WIDTH / CAMERA_HEIGHT 

# 初始窗口大小设置
INITIAL_WINDOW_WIDTH = 480 
INITIAL_WINDOW_HEIGHT = 320

# 定义照片保存的根目录
PHOTO_SAVE_DIR = os.path.join(os.path.expanduser('~'), "Pictures", "NCNN_Pi_Photos")

processed_frame_queue = queue.Queue(maxsize=1) 
stats_queue = queue.Queue(maxsize=1) 


# --- 后台工作线程类 ---
class CameraWorker(threading.Thread):
    def __init__(self, model_path):
        super().__init__()
        self.picam2 = None
        self.running = True
        self.net = None # YOLO 模型对象
        self.model_path = model_path
        self.frame_count = 0
        self.detection_interval = 4 # 每隔 4 帧进行一次检测

    def _initialize_camera(self):
        """初始化 Picamera2 (使用 640x480)"""
        try:
            self.picam2 = Picamera2()
            self.picam2.preview_configuration.main.size = (CAMERA_WIDTH, CAMERA_HEIGHT) 
            self.picam2.preview_configuration.main.format = "RGB888" # RGB 格式
            self.picam2.preview_configuration.align()
            self.picam2.configure("preview")
            self.picam2.start()
            print(f"✅ Picamera2 启动成功，捕获分辨率: {CAMERA_WIDTH}x{CAMERA_HEIGHT}")
            return True
        except Exception as e:
            print(f"❌ Picamera2 启动失败: {e}")
            return False

    def _load_ncnn_model(self):
        """
        加载 Ultralytics YOLO NCNN 模型。
        这里我们使用 Ultralytics 提供的简单模式。
        """
        try:
            # 🚀 简单模式: 使用 YOLO('model_dir') 加载 NCNN 封装
            self.net = YOLO(self.model_path) 
            print(f"🎉 Ultralytics NCNN 模型加载成功: {self.model_path}")
            
            # 设置 NCNN 后端线程数（通常对 Pi 上的 CPU 优化很重要）
            # 注意: 此设置可能需要通过 Ultralytics NCNN 绑定的特定 API (如果有) 或 NCNN 环境变量来控制。
            # 这里我们假设 Ultralytics 默认使用多线程。

            return True
        except Exception as e:
            print(f"❌ Ultralytics NCNN 模型加载失败: {e}")
            return False

    def run(self):
        """线程主循环"""
        if not self._initialize_camera() or not self._load_ncnn_model():
            self.running = False
            return

        last_frame_time = time.time()
        last_detected_frame_bgr = None # 存储 BGR 格式的带识别框的帧
        detection_time = 0.0
        fps_start_time = time.time()
        cap_frame_count = 0

        while self.running:
            current_time = time.time()
            elapsed_time = current_time - last_frame_time
            sleep_time = (FRAME_TIME_MS / 1000) - elapsed_time
            if sleep_time > 0: time.sleep(sleep_time)
            last_frame_time = time.time()

            # Picamera2 捕获 RGB 格式
            current_frame_rgb = self.picam2.capture_array()
            
            cap_frame_count += 1
            if current_time - fps_start_time >= 1.0:
                 cap_fps = cap_frame_count / (current_time - fps_start_time) 
                 if stats_queue.full():
                    try: stats_queue.get_nowait()
                    except queue.Empty: pass
                 stats_queue.put((cap_fps, detection_time))
                 fps_start_time = current_time
                 cap_frame_count = 0
            
            # 默认显示 BGR 格式的原始帧
            display_frame_bgr = cv2.cvtColor(current_frame_rgb, cv2.COLOR_RGB2BGR)

            if self.frame_count >= self.detection_interval:
                start_detection = time.time()
                
                # 🚀 简单模式: Ultralytics 一步完成前处理、推理、后处理和 NMS
                try:
                    results = self.net(
                        current_frame_rgb, # 输入 RGB 帧
                        imgsz=PREDICT_IMG_SIZE, 
                        verbose=False, 
                        conf=CONFIDENCE_THRESHOLD, 
                        iou=NMS_THRESHOLD,
                        stream=False # 非流式模式
                    )
                    detection_time = time.time() - start_detection
                    
                    # 绘制结果：Ultralytics 的 .plot() 方法返回一个 BGR 格式的 NumPy 数组
                    # 包含边界框、标签和置信度
                    if results and len(results) > 0:
                        last_detected_frame_bgr = results[0].plot() 

                except Exception as e:
                    print(f"Ultralytics NCNN 推理失败: {e}")
                    detection_time = time.time() - start_detection
                
                self.frame_count = 0 
            
            # 如果有上次的识别结果，则显示带框的帧
            if last_detected_frame_bgr is not None:
                display_frame_bgr = last_detected_frame_bgr
            
            self.frame_count += 1

            if processed_frame_queue.full():
                try: processed_frame_queue.get_nowait()
                except queue.Empty: pass
            processed_frame_queue.put(display_frame_bgr) 

        if self.picam2: self.picam2.stop()

    def stop(self):
        self.running = False


# --- 相机应用主类 (Tkinter UI) ---
class App:
    def __init__(self, master):
        self.master = master
        
        # 设置窗口大小匹配屏幕分辨率 480x320
        self.master.geometry(f"{INITIAL_WINDOW_WIDTH}x{INITIAL_WINDOW_HEIGHT}")
        self.master.title(f"树莓派 Ultralytics NCNN 摄像头应用")
        
        # 启动工作线程，传入 NCNN 模型路径
        self.worker = CameraWorker(MODEL_PATH)
        self.worker.daemon = True 
        self.worker.start()
        
        if not self.worker.is_alive():
             messagebox.showerror("启动失败", "摄像头工作线程未能成功启动。")
             self.master.destroy()
             return

        self.after_id = None
        self.photo = None 
        self.canvas_image = None 
        
        self.current_cap_fps = 0.0
        self.current_detection_time = 0.0
        
        self.init_ui()
        self.master.after(100, self._initial_resize_and_centering)
        
        self.master.protocol("WM_DELETE_WINDOW", self.confirm_exit)
        self.update_preview()

    def init_ui(self):
        """初始化 Tkinter 界面，并设置 Menubar"""
        
        # --- Menubar ---
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="拍照 (带识别框)", command=self.take_photo)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.confirm_exit)
        menubar.add_cascade(label="文件", menu=file_menu)

        # 关于菜单
        about_menu = tk.Menu(menubar, tearoff=0)
        about_menu.add_command(label="系统信息", command=lambda: show_system_about(self.master))
        about_menu.add_command(label="关于开发者", command=lambda: show_developer_about(self.master))
        menubar.add_cascade(label="关于", menu=about_menu)
        # --- Menubar 结束 ---

        # UI 布局
        main_frame = tk.Frame(self.master, bg="#2c3e50")
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # ------------------------------------------------------------------
        # 锁定 4:3 比例的 Frame (容器) - 用于显示摄像头画面
        # ------------------------------------------------------------------
        self.aspect_frame = tk.Frame(main_frame, bg='black', bd=2, relief=tk.SUNKEN)
        self.aspect_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.aspect_frame.grid_rowconfigure(0, weight=1)
        self.aspect_frame.grid_columnconfigure(0, weight=1)

        self.aspect_frame.bind('<Configure>', self._on_frame_resize)

        # 创建 Canvas (画布)
        self.preview_canvas = tk.Canvas(self.aspect_frame, bg='black', highlightthickness=0)
        self.preview_canvas.grid(row=0, column=0) 
        
        # FPS Label 浮动在 Canvas 左上角
        self.fps_label = tk.Label(self.aspect_frame, text="FPS: 0.0 | 推理: 0.0ms", fg="#00ff00", bg="black", font=('Arial', 9, 'bold'))
        self.fps_label.place(relx=0.01, rely=0.01, anchor="nw")
        
        # 统计信息区域 (放在底部)
        info_frame = tk.Frame(self.master, bg="#34495e", padx=5, pady=2)
        info_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.stats_label = tk.Label(info_frame, 
                                    text=f"捕获: {CAMERA_WIDTH}x{CAMERA_HEIGHT} | 模型: Ultralytics NCNN | 输入: {PREDICT_IMG_SIZE}", 
                                    bg="#34495e", 
                                    fg="#bdc3c7", 
                                    font=('Arial', 8), 
                                    justify=tk.LEFT)
        self.stats_label.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.master.update_idletasks()

    def _on_frame_resize(self, event):
        """严格约束 Canvas 的尺寸为 4:3 (640x480 比例)。"""
        w = event.width  
        h = event.height 
        
        target_aspect_ratio = CAMERA_ASPECT_RATIO 

        # 尝试以容器高度为基准计算宽度
        new_w = int(h * target_aspect_ratio)
        new_h = h
        
        # 如果计算出的宽度超过了容器的宽度，则以宽度为限制
        if new_w > w:
            new_w = w
            new_h = int(w / target_aspect_ratio)

        if new_w < 100 or new_h < 50:
            return

        self.preview_canvas.config(width=new_w, height=new_h)


    def _initial_resize_and_centering(self):
        """强制在 UI 渲染后调用 resize"""
        self.master.update_idletasks()
        
        w = self.aspect_frame.winfo_width()
        h = self.aspect_frame.winfo_height()
        
        class MockEvent:
            def __init__(self, w, h):
                self.width = w
                self.height = h

        if w > 10 and h > 10:
            mock_event = MockEvent(w, h)
            self._on_frame_resize(mock_event)


    def update_preview(self):
        """[主线程] 从队列中读取已处理的帧和性能数据并更新 UI。"""
        try:
            display_frame_bgr = processed_frame_queue.get_nowait()
            
            # 尝试获取新数据，如果成功则更新状态变量
            try: 
                new_cap_fps, new_detection_time = stats_queue.get_nowait()
                self.current_cap_fps = new_cap_fps
                self.current_detection_time = new_detection_time
            except queue.Empty: 
                pass 

            # 更新 FPS Label
            self.fps_label.config(
                text=f"FPS: {self.current_cap_fps:.1f} | 推理: {self.current_detection_time*1000:.1f}ms (每{self.worker.detection_interval}帧)"
            )
            # 更新底部统计信息
            self.stats_label.config(
                 text=f"捕获: {CAMERA_WIDTH}x{CAMERA_HEIGHT} | 模型: Ultralytics NCNN | 输入: {PREDICT_IMG_SIZE} | 实时 FPS: {self.current_cap_fps:.1f}"
            )
            
            # 将 OpenCV (BGR) 格式转换为 PIL (RGB) 格式
            detected_frame_rgb = cv2.cvtColor(display_frame_bgr, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(detected_frame_rgb)
            
            # 获取当前 Canvas 的实际尺寸
            preview_width = self.preview_canvas.winfo_width()
            preview_height = self.preview_canvas.winfo_height()

            if preview_width > 0 and preview_height > 0:
                # 图像缩放至 Canvas 的尺寸
                image = image.resize((preview_width, preview_height), Image.Resampling.LANCZOS)
                
                self.photo = ImageTk.PhotoImage(image)

                self.preview_canvas.delete("all")
                self.canvas_image = self.preview_canvas.create_image(
                    preview_width // 2, 
                    preview_height // 2, 
                    image=self.photo, 
                    anchor=tk.CENTER
                )
            
        except queue.Empty:
            pass 
        except Exception as e:
            print(f"UI 更新错误: {e}") 
            
        self.after_id = self.master.after(1, self.update_preview)

    def take_photo(self):
        """[主线程] 拍照操作：从队列中获取最新的带框帧并保存。"""
        if not self.worker.is_alive():
             messagebox.showerror("拍照失败", "工作线程未运行。")
             return
             
        if not os.path.exists(PHOTO_SAVE_DIR): os.makedirs(PHOTO_SAVE_DIR)

        frame_bgr = None
        try:
            # 确保获取到最新的帧
            frame_bgr = processed_frame_queue.get(timeout=0.2)
            while not processed_frame_queue.empty():
                frame_bgr = processed_frame_queue.get_nowait()
                
        except queue.Empty: 
            messagebox.showerror("拍照失败", "未获取到有效的帧数据，请等待视频流启动。")
            return
             
        fname = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "_ultralytics_ncnn_pi.jpg"
        path = os.path.join(PHOTO_SAVE_DIR, fname)
        try:
            cv2.imwrite(path, frame_bgr)
            messagebox.showinfo("照片已保存", f"带识别框的照片已保存到:\n{path}")
        except Exception as e:
            messagebox.showerror("保存失败", f"无法保存照片到 {path}。错误: {e}")


    def confirm_exit(self):
        """停止线程并退出应用。"""
        if messagebox.askyesno("退出", "你真的要退出吗？"):
            if self.worker.is_alive():
                print("停止摄像头工作线程...")
                self.worker.stop()
                self.worker.join(timeout=2)
            if self.after_id:
                self.master.after_cancel(self.after_id)
            self.master.destroy()

if __name__ == "__main__":
    try:
        root = tk.Tk()
        root.resizable(False, False) 
        app_instance = App(root)
        root.mainloop()
    except Exception as e:
        print(f"应用启动失败: {e}")
        sys.exit(1)
