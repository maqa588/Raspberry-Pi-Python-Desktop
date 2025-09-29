import os
import sys
import datetime
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import numpy as np
import cv2 
import time 
import platform
import threading
import queue
from platformdirs import user_pictures_dir

# ----------------------------------------------------------------------
# Windows 专有配置
# ----------------------------------------------------------------------
# 在 Windows 上，明确指定 DirectShow 后端以获得更好的摄像头性能和稳定性
# 如果遇到问题，可以尝试 cv2.CAP_MSMF (Microsoft Media Foundation)
CAMERA_BACKEND = cv2.CAP_DSHOW 

# --- 导入 ultralytics 库 ---
try:
    from ultralytics import YOLO
    # 假设 NCNN 格式模型导出后位于此文件夹
    NCNN_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "yolo11n_ncnn_model")
    
    # 关键设置: 使用 'cpu'，NCNN 在 Windows 上通常利用 CPU 或 Vulkan (需特定编译)
    DEFAULT_DEVICE = 'cpu' 
    ACCEL_NAME = 'NCNN Native (CPU Fallback)'

except ImportError:
    messagebox.showerror("依赖缺失", "请先安装 ultralytics 库: pip install ultralytics")
    class YOLO:
        def __init__(self, *args, **kwargs):
            raise ImportError("ultralytics not found")
    NCNN_MODEL_DIR = ""
    DEFAULT_DEVICE = 'cpu'
    ACCEL_NAME = 'CPU'

# --- 常量定义 ---
CONFIDENCE_THRESHOLD = 0.4 
NMS_THRESHOLD = 0.4        
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
TARGET_CAP_FPS = 30
FRAME_TIME_MS = 1000 / TARGET_CAP_FPS
MODEL_INFERENCE_SIZE = 640
PREDICT_IMG_SIZE = (MODEL_INFERENCE_SIZE, MODEL_INFERENCE_SIZE)

# 初始窗口大小设置
INITIAL_WINDOW_WIDTH = 1000
INITIAL_WINDOW_HEIGHT = 600

# 定义照片保存的根目录
PHOTO_SAVE_DIR = os.path.join(user_pictures_dir(), "YOLO NCNN Photos")
print(f"照片将保存到: {PHOTO_SAVE_DIR}")

processed_frame_queue = queue.Queue(maxsize=1) 
stats_queue = queue.Queue(maxsize=1) 

# --- 后台工作线程类 ---
class CameraWorker(threading.Thread):
    def __init__(self, model_dir, device_name):
        super().__init__()
        self.cap = None
        self.running = True
        self.net = None
        self.model_dir = model_dir
        self.device = device_name
        self.frame_count = 0
        # 每隔 4 帧进行一次检测，保证预览流畅
        self.detection_interval = 4 
        self.classes = {}

    def _initialize_camera(self):
        """初始化摄像头，使用 Windows DirectShow 后端"""
        # 明确指定 DirectShow 后端
        self.cap = cv2.VideoCapture(0, CAMERA_BACKEND)
        if self.cap.isOpened():
            # 尝试设置分辨率和帧率
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH) 
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            self.cap.set(cv2.CAP_PROP_FPS, TARGET_CAP_FPS) 
            print(f"相机工作线程启动，目标 FPS: {self.cap.get(cv2.CAP_PROP_FPS):.1f} (实际值可能有所不同)")
            return True
        return False

    def _load_yolo_model(self):
        """加载 YOLO NCNN 模型"""
        if not os.path.exists(self.model_dir):
             print(f"后台工作线程: 错误！NCNN 模型目录不存在于: {self.model_dir}")
             print("请先运行 model.export(format=\"ncnn\") 生成此目录。")
             return False

        try:
            self.net = YOLO(self.model_dir) 
            self.classes = self.net.names
            print(f"🎉 后台工作线程: YOLO NCNN 模型加载成功。")
            print(f"🎉 后台工作线程: 推理设备已设置为 '{ACCEL_NAME}' (请求 device='{self.device}')。")
            return True
        except Exception as e:
            print(f"❌ NCNN 模型加载失败: {e}")
            return False

    def detect_objects(self, img_bgr):
        """在帧上运行推理并绘制结果"""
        if not self.net:
            return img_bgr, 0.0

        start_detection = time.time()
        try:
            # 推理调用
            results = self.net.predict(
                source=img_bgr, 
                conf=CONFIDENCE_THRESHOLD, 
                iou=NMS_THRESHOLD, 
                imgsz=PREDICT_IMG_SIZE,
                verbose=False, 
                device=self.device, 
            )
        except Exception as e:
            print(f"NCNN 推理错误: {e}") 
            return img_bgr, 0.0

        detection_time = time.time() - start_detection
        result_frame = img_bgr.copy()
        
        if not results or not results[0].boxes:
            return result_frame, detection_time

        # 绘制结果
        res = results[0]
        for box in res.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].int().tolist())
            conf = box.conf[0].item()                      
            cls = int(box.cls[0].item())                   
            
            label = self.classes.get(cls, "Unknown")
            color = (0, 255, 0) # 绿色 BGR
            
            cv2.rectangle(result_frame, (x1, y1), (x2, y2), color, 3) 
            text = f"{label}: {conf:.2f}"
            text_y = max(y1 - 15, 30) 
            cv2.putText(result_frame, text, (x1, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 3)
            
        return result_frame, detection_time


    def run(self):
        """线程主循环"""
        if not self._initialize_camera() or not self._load_yolo_model():
            self.running = False
            if self.cap: self.cap.release()
            return

        last_frame_time = time.time()
        last_detected_frame = None
        detection_time = 0.0
        fps_start_time = time.time()
        cap_frame_count = 0

        while self.running:
            current_time = time.time()
            elapsed_time = current_time - last_frame_time
            sleep_time = (FRAME_TIME_MS / 1000) - elapsed_time
            if sleep_time > 0: time.sleep(sleep_time)
            last_frame_time = time.time()

            ret, current_frame_bgr = self.cap.read()
            if not ret: continue

            cap_frame_count += 1
            if current_time - fps_start_time >= 1.0:
                 cap_fps = cap_frame_count / (current_time - fps_start_time) 
                 if stats_queue.full():
                    try: stats_queue.get_nowait()
                    except queue.Empty: pass
                 # 后台线程只在每秒结束时推送一次统计数据
                 stats_queue.put((cap_fps, detection_time))
                 fps_start_time = current_time
                 cap_frame_count = 0
            
            display_frame_bgr = current_frame_bgr.copy()

            if self.frame_count >= self.detection_interval:
                processed_frame, detection_time = self.detect_objects(current_frame_bgr)
                last_detected_frame = processed_frame
                self.frame_count = 0 
            
            if last_detected_frame is not None:
                display_frame_bgr = last_detected_frame
            
            self.frame_count += 1

            if processed_frame_queue.full():
                try: processed_frame_queue.get_nowait()
                except queue.Empty: pass
            processed_frame_queue.put(display_frame_bgr)

        if self.cap: self.cap.release()

    def stop(self):
        self.running = False


# --- 相机应用主类 (Tkinter UI) ---
class App:
    def __init__(self, master):
        self.master = master
        # 检查是否为 Windows 平台
        if platform.system() != "Windows":
             messagebox.showerror("配置错误", "此版本专为 Windows 设计。")
             self.master.destroy()
             return

        # 1. 设置窗口初始大小 
        self.master.geometry(f"{INITIAL_WINDOW_WIDTH}x{INITIAL_WINDOW_HEIGHT}")
        
        # 2. 初始化模型和 UI
        self.classes = {}
        try:
            temp_model = YOLO(NCNN_MODEL_DIR)
            self.classes = temp_model.names
            self.device_info = ACCEL_NAME
            del temp_model
        except Exception as e:
            messagebox.showerror("模型加载失败", f"请确认已导出 NCNN 模型到 '{NCNN_MODEL_DIR}'。错误: {e}")
            self.master.destroy()
            return
            
        self.master.title(f"Windows 高性能摄像头应用 (线程化 NCNN - {ACCEL_NAME}) - 1280x720p")
        
        self.worker = CameraWorker(NCNN_MODEL_DIR, DEFAULT_DEVICE)
        self.worker.daemon = True 
        self.worker.start()
        
        if not self.worker.is_alive():
             messagebox.showerror("启动失败", "摄像头工作线程未能成功启动。")
             self.master.destroy()
             return

        self.after_id = None
        self.photo = None 
        self.canvas_image = None 
        
        # 状态变量，用于存储上一次成功的 FPS 和推理时间，防止 UI 闪烁。
        self.current_cap_fps = 0.0
        self.current_detection_time = 0.0
        
        self.init_ui()
        
        # 3. 强制在 UI 渲染后调用一次 resize 
        self.master.after(100, self._initial_resize_and_centering)
        
        self.master.protocol("WM_DELETE_WINDOW", self.confirm_exit)
        self.update_preview()

    def init_ui(self):
        """初始化 Tkinter 界面，并设置 16:9 比例锁定"""
        main_frame = tk.Frame(self.master, bg="#2c3e50", padx=10, pady=10)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        RIGHT_FRAME_WIDTH = 200 
        right_frame = tk.Frame(main_frame, bg="#34495e", padx=10, pady=10, width=RIGHT_FRAME_WIDTH)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0)) 
        right_frame.pack_propagate(False) 

        tk.Label(right_frame, text="操作面板 (NCNN)", bg="#34495e", fg="#ecf0f1", font=('Arial', 12, 'bold')).pack(pady=10)

        base_button_style = {'width': 18, 'height': 2, 'fg': 'white', 'activeforeground': 'white',
                             'font': ('Arial', 10, 'bold'), 'bd': 0, 'relief': tk.FLAT}

        btn_photo = tk.Button(right_frame, text="拍照 (1280x720)", command=self.take_photo, 
                              bg='#3498db', activebackground='#2980b9', **base_button_style)
        btn_photo.pack(pady=10)
        
        tk.Label(right_frame, text=f"分辨率 (Cam): {CAMERA_WIDTH}x{CAMERA_HEIGHT}", bg="#34495e", fg="#bdc3c7", font=('Arial', 10)).pack(pady=(20, 5))
        tk.Label(right_frame, text=f"模型输入 H x W: {PREDICT_IMG_SIZE[0]}x{PREDICT_IMG_SIZE[1]} (NCNN)", bg="#34495e", fg="#bdc3c7", font=('Arial', 10)).pack(pady=5)
        tk.Label(right_frame, text=f"加速: {self.device_info}", bg="#34495e", fg="#bdc3c7", font=('Arial', 10, 'bold')).pack(pady=5)
        
        btn_exit = tk.Button(right_frame, text="退出应用", command=self.confirm_exit, 
                             bg='#e74c3c', activebackground='#c0392b', **base_button_style)
        btn_exit.pack(pady=(40, 10))

        # ------------------------------------------------------------------
        # 锁定 16:9 比例的 Frame (容器)
        # ------------------------------------------------------------------
        self.aspect_frame = tk.Frame(main_frame, bg='black', bd=2, relief=tk.SUNKEN)
        self.aspect_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Grid Setup for Centering：配置 aspect_frame 内部的 Grid 布局
        self.aspect_frame.grid_rowconfigure(0, weight=1)
        self.aspect_frame.grid_columnconfigure(0, weight=1)

        # 绑定尺寸变化事件
        self.aspect_frame.bind('<Configure>', self._on_frame_resize)

        # 创建 Canvas (画布)
        self.preview_canvas = tk.Canvas(self.aspect_frame, bg='black', highlightthickness=0)
        self.preview_canvas.grid(row=0, column=0) 
        
        self.fps_label = tk.Label(self.aspect_frame, text="相机 FPS: 0.0 | 推理: 0.0ms", fg="#ecf0f1", bg="black", font=('Arial', 10, 'bold'))
        # FPS Label 使用 place 浮动在 Canvas 上方
        self.fps_label.place(relx=0.01, rely=0.01, anchor="nw")
        
        self.master.update_idletasks()

    def _on_frame_resize(self, event):
        """
        当 aspect_frame 尺寸改变时调用。
        使用 Grid 居中机制，并严格约束 Canvas 的尺寸为 16:9。
        """
        w = event.width  # aspect_frame 容器宽度
        h = event.height # aspect_frame 容器高度
        
        target_aspect_ratio = 16.0 / 9.0

        # 1. 尝试将宽度设置为容器宽度，计算对应的高度 (宽度优先)
        max_w_for_h = int(h * target_aspect_ratio)
        max_h_for_w = int(w / target_aspect_ratio) 

        new_w = w
        new_h = max_h_for_w
        
        # 2. 如果宽度优先计算出的高度超过了容器的高度，则以高度为限制 (确保整个画面可见)
        if new_h > h:
            new_h = h
            new_w = max_w_for_h

        # 最小尺寸限制
        if new_w < 100 or new_h < 50:
            return

        # 关键：更新 Canvas 的 width 和 height 配置。
        # Grid 机制会自动将这个固定尺寸的 Canvas 居中到 aspect_frame 的中心。
        self.preview_canvas.config(width=new_w, height=new_h)


    def _initial_resize_and_centering(self):
        """
        用于解决窗口刚打开时 Canvas 未能正确居中和调整大小的问题。
        """
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
                # 如果队列为空，则保持使用上一次的值（不会归零）
                pass 

            # 使用状态变量更新 UI，而不是使用 try-except 块内的局部变量
            self.fps_label.config(
                text=f"相机 FPS: {self.current_cap_fps:.1f} (目标 {TARGET_CAP_FPS}) | 推理: {self.current_detection_time*1000:.1f}ms (每{self.worker.detection_interval}帧)"
            )
            
            detected_frame_rgb = cv2.cvtColor(display_frame_bgr, cv2.COLOR_BGR2RGB)
            
            # 获取当前 Canvas 的实际尺寸 (由 _on_frame_resize 决定)
            preview_width = self.preview_canvas.winfo_width()
            preview_height = self.preview_canvas.winfo_height()

            if preview_width > 0 and preview_height > 0:
                image = Image.fromarray(detected_frame_rgb)
                
                # 图像缩放至 Canvas 的尺寸
                image = image.resize((preview_width, preview_height), Image.Resampling.LANCZOS)
                
                self.photo = ImageTk.PhotoImage(image)

                # 使用 Canvas 绘制图像
                self.preview_canvas.delete("all") # 清除上一次绘制的图像
                # 将图像中心点精确放置在 Canvas 的中心 (preview_width/2, preview_height/2)
                self.canvas_image = self.preview_canvas.create_image(
                    preview_width // 2, 
                    preview_height // 2, 
                    image=self.photo, 
                    anchor=tk.CENTER # 确保图像的锚点是中心
                )
            
        except queue.Empty:
            pass 
        except Exception as e:
            print(f"UI 更新错误: {e}")
            
        self.after_id = self.master.after(1, self.update_preview)

    def take_photo(self):
        """[主线程] 拍照操作：从队列中获取最新的带框帧并保存到系统照片目录。"""
        if not self.worker.is_alive():
             messagebox.showerror("拍照失败", "工作线程未运行。")
             return
             
        if not os.path.exists(PHOTO_SAVE_DIR): os.makedirs(PHOTO_SAVE_DIR)

        frame_bgr = None
        try:
            # 等待 100ms 以确保从工作线程获取到至少一帧数据
            frame_bgr = processed_frame_queue.get(timeout=0.1)
            
            # 确保我们拿到的是最新的那一帧，清空队列中可能存在的旧帧
            while not processed_frame_queue.empty():
                frame_bgr = processed_frame_queue.get_nowait()
                
        except queue.Empty: 
            frame_bgr = None # 如果等待 100ms 仍然为空，则失败
             
        if frame_bgr is None:
             messagebox.showerror("拍照失败", "未获取到有效的帧数据，请等待视频流启动。")
             return

        fname = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "_yolo_ncnn_windows.jpg"
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
                self.worker.stop()
                self.worker.join(timeout=2)
            if self.after_id:
                self.master.after_cancel(self.after_id)
            self.master.destroy()

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app_instance = App(root)
        root.mainloop()
    except Exception as e:
        print(f"应用启动失败: {e}")
        sys.exit(1)
