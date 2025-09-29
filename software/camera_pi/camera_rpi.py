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

# ----------------------------------------------------------------------
# 路径调整以适应新的 software/camera_pi/ 目录结构 (用户要求)
# ----------------------------------------------------------------------
current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)

# 向上追溯三级以找到项目根目录 (project_root -> software -> camera_pi -> camera_pi.py)
# 这是一个占位符路径设置，用于模拟大型项目结构
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
sys.path.insert(0, project_root)
# --- 路径调整结束 ---

# 假设这些导入在项目中可用
try:
    # 从项目根目录导入 system 模块
    from system.button.about import show_system_about, show_developer_about
except ImportError:
    # 定义占位函数以防导入失败，确保代码能运行
    def show_system_about(root): messagebox.showinfo("系统信息", "此为系统信息占位符。\n请在实际项目中实现 'system.button.about' 模块。")
    def show_developer_about(root): messagebox.showinfo("开发者信息", "此为开发者信息占位符。\n作者：Gemini LLM\n项目：Raspberry Pi YOLO 摄像头应用")
    print("警告: 未能导入 system.button.about，使用占位函数。")

# ----------------------------------------------------------------------
# 树莓派及模型配置
# ----------------------------------------------------------------------
try:
    # 尝试导入必要的库
    from ultralytics import YOLO
    from picamera2 import Picamera2 # type: ignore
    MODEL_PATH = "yolo11n.pt" # YOLOv8 nano 模型
    
    # 检查平台
    if platform.system() != "Linux" or not os.path.exists('/dev/vchiq'):
        print("警告: 当前环境可能不是树莓派或缺少必要的硬件接口。")
    
except ImportError:
    messagebox.showerror("依赖缺失", "请确保安装了以下库:\n1. ultralytics: pip install ultralytics\n2. picamera2: pip install picamera2\n3. OpenCV: pip install opencv-python")
    
    # 定义占位符类，防止程序崩溃
    class YOLO:
        def __init__(self, *args, **kwargs): raise ImportError("ultralytics not found")
    class Picamera2:
        def __init__(self, *args, **kwargs): raise ImportError("picamera2 not found")
        def start(self): pass
        def configure(self, *args): pass
        def capture_array(self): return np.zeros((320, 480, 3), dtype=np.uint8)
        def stop(self): pass

# --- 常量定义 ---
CONFIDENCE_THRESHOLD = 0.4 
NMS_THRESHOLD = 0.4        
CAMERA_WIDTH = 480        # 树莓派目标分辨率
CAMERA_HEIGHT = 320
TARGET_CAP_FPS = 30
FRAME_TIME_MS = 1000 / TARGET_CAP_FPS
PREDICT_IMG_SIZE = 480    # 模型输入尺寸
CAMERA_ASPECT_RATIO = CAMERA_WIDTH / CAMERA_HEIGHT # 3:2

# 初始窗口大小设置
INITIAL_WINDOW_WIDTH = 800
INITIAL_WINDOW_HEIGHT = 500

# 定义照片保存的根目录
# 在 Linux (树莓派) 上通常是 ~/Pictures
PHOTO_SAVE_DIR = os.path.join(os.path.expanduser('~'), "Pictures", "YOLO_Pi_Photos")
print(f"照片将保存到: {PHOTO_SAVE_DIR}")

processed_frame_queue = queue.Queue(maxsize=1) 
stats_queue = queue.Queue(maxsize=1) 

# --- 后台工作线程类 ---
class CameraWorker(threading.Thread):
    def __init__(self, model_path):
        super().__init__()
        self.picam2 = None
        self.running = True
        self.net = None
        self.model_path = model_path
        self.frame_count = 0
        self.detection_interval = 4 # 每隔 4 帧进行一次检测
        self.device = 'cpu' # 树莓派默认使用 CPU 进行推理

    def _initialize_camera(self):
        """初始化 Picamera2"""
        try:
            self.picam2 = Picamera2()
            self.picam2.preview_configuration.main.size = (CAMERA_WIDTH, CAMERA_HEIGHT)
            self.picam2.preview_configuration.main.format = "RGB888" # YOLO 默认使用 RGB
            self.picam2.preview_configuration.align()
            self.picam2.configure("preview")
            self.picam2.start()
            print(f"✅ Picamera2 启动成功，分辨率: {CAMERA_WIDTH}x{CAMERA_HEIGHT}")
            return True
        except Exception as e:
            print(f"❌ Picamera2 启动失败: {e}")
            return False

    def _load_yolo_model(self):
        """加载 YOLO 模型"""
        try:
            self.net = YOLO(self.model_path) 
            print(f"🎉 后台工作线程: YOLO 模型加载成功 ({self.model_path})。")
            return True
        except Exception as e:
            print(f"❌ YOLO 模型加载失败: {e}")
            return False

    def detect_objects(self, img_rgb):
        """在帧上运行推理"""
        if not self.net:
            return img_rgb, 0.0

        start_detection = time.time()
        try:
            # 推理调用，使用当前帧作为源
            # YOLO plot() 函数需要 RGB 输入
            results = self.net.predict(
                source=img_rgb, 
                conf=CONFIDENCE_THRESHOLD, 
                iou=NMS_THRESHOLD, 
                imgsz=PREDICT_IMG_SIZE,
                verbose=False, 
                device=self.device, 
            )
        except Exception as e:
            print(f"YOLO 推理错误: {e}") 
            return img_rgb, 0.0

        detection_time = time.time() - start_detection
        
        # results[0].plot() 直接返回带有 BGR 格式绘制结果的 numpy 数组
        # 我们需要在主线程中将其转回 RGB 进行显示
        if results and results[0].orig_img is not None:
             # YOLOv8 的 plot 函数返回 BGR 格式的图像
             result_frame_bgr = results[0].plot() 
             return result_frame_bgr, detection_time
        
        # 如果推理失败，返回原始帧
        return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR), detection_time 


    def run(self):
        """线程主循环"""
        if not self._initialize_camera() or not self._load_yolo_model():
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
                 # 后台线程在每秒结束时推送一次统计数据
                 stats_queue.put((cap_fps, detection_time))
                 fps_start_time = current_time
                 cap_frame_count = 0
            
            # 默认显示 BGR 格式的原始帧 (需要转换)
            display_frame_bgr = cv2.cvtColor(current_frame_rgb, cv2.COLOR_RGB2BGR)

            if self.frame_count >= self.detection_interval:
                # detect_objects 返回 BGR 格式和推理时间
                processed_frame_bgr, detection_time = self.detect_objects(current_frame_rgb)
                last_detected_frame_bgr = processed_frame_bgr
                self.frame_count = 0 
            
            if last_detected_frame_bgr is not None:
                display_frame_bgr = last_detected_frame_bgr
            
            self.frame_count += 1

            if processed_frame_queue.full():
                try: processed_frame_queue.get_nowait()
                except queue.Empty: pass
            # 推送 BGR 帧到队列
            processed_frame_queue.put(display_frame_bgr) 

        if self.picam2: self.picam2.stop()

    def stop(self):
        self.running = False


# --- 相机应用主类 (Tkinter UI) ---
class App:
    def __init__(self, master):
        self.master = master
        # 严格检查平台，提示用户这是树莓派应用
        if platform.system() != "Linux":
             print("警告: 此应用专为 Linux/树莓派设计，但在非 Linux 平台运行。Picamera2 可能会失败。")

        self.master.geometry(f"{INITIAL_WINDOW_WIDTH}x{INITIAL_WINDOW_HEIGHT}")
        self.master.title(f"树莓派 YOLO 摄像头应用 (Picamera2 - {CAMERA_WIDTH}x{CAMERA_HEIGHT}p)")
        
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
        
        # 状态变量，用于存储上一次成功的 FPS 和推理时间，防止 UI 闪烁。
        self.current_cap_fps = 0.0
        self.current_detection_time = 0.0
        
        self.init_ui()
        self.master.after(100, self._initial_resize_and_centering)
        
        self.master.protocol("WM_DELETE_WINDOW", self.confirm_exit)
        self.update_preview()

    def init_ui(self):
        """初始化 Tkinter 界面，并设置 Menubar"""
        
        # --- Menubar (用户要求) ---
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

        main_frame = tk.Frame(self.master, bg="#2c3e50", padx=10, pady=10)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        RIGHT_FRAME_WIDTH = 180 
        right_frame = tk.Frame(main_frame, bg="#34495e", padx=5, pady=5, width=RIGHT_FRAME_WIDTH)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0)) 
        right_frame.pack_propagate(False) 

        tk.Label(right_frame, text="树莓派 YOLO", bg="#34495e", fg="#ecf0f1", font=('Arial', 12, 'bold')).pack(pady=5)
        
        # 统计信息显示在右侧面板底部
        self.stats_label = tk.Label(right_frame, text="初始化中...", bg="#34495e", fg="#bdc3c7", font=('Arial', 9), justify=tk.LEFT)
        self.stats_label.pack(side=tk.BOTTOM, pady=10)

        # ------------------------------------------------------------------
        # 锁定 3:2 比例的 Frame (容器)
        # ------------------------------------------------------------------
        self.aspect_frame = tk.Frame(main_frame, bg='black', bd=2, relief=tk.SUNKEN)
        self.aspect_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.aspect_frame.grid_rowconfigure(0, weight=1)
        self.aspect_frame.grid_columnconfigure(0, weight=1)

        self.aspect_frame.bind('<Configure>', self._on_frame_resize)

        # 创建 Canvas (画布)
        self.preview_canvas = tk.Canvas(self.aspect_frame, bg='black', highlightthickness=0)
        self.preview_canvas.grid(row=0, column=0) 
        
        # FPS Label 浮动在 Canvas 左上角
        self.fps_label = tk.Label(self.aspect_frame, text="FPS: 0.0 | 推理: 0.0ms", fg="#00ff00", bg="black", font=('Arial', 10, 'bold'))
        self.fps_label.place(relx=0.01, rely=0.01, anchor="nw")
        
        self.master.update_idletasks()

    def _on_frame_resize(self, event):
        """
        当 aspect_frame 尺寸改变时调用。
        严格约束 Canvas 的尺寸为 3:2 (480x320 比例)。
        """
        w = event.width  # aspect_frame 容器宽度
        h = event.height # aspect_frame 容器高度
        
        target_aspect_ratio = CAMERA_ASPECT_RATIO # 3.0 / 2.0

        # 1. 尝试将宽度设置为容器宽度，计算对应的高度 (宽度优先)
        max_h_for_w = int(w / target_aspect_ratio) 
        
        new_w = w
        new_h = max_h_for_w
        
        # 2. 如果宽度优先计算出的高度超过了容器的高度，则以高度为限制 (确保整个画面可见)
        if new_h > h:
            new_h = h
            new_w = int(h * target_aspect_ratio)

        # 最小尺寸限制
        if new_w < 100 or new_h < 50:
            return

        # 更新 Canvas 尺寸，Grid 机制会居中它
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
            # 获取 BGR 格式的帧
            display_frame_bgr = processed_frame_queue.get_nowait()
            
            # 尝试获取新数据，如果成功则更新状态变量
            try: 
                new_cap_fps, new_detection_time = stats_queue.get_nowait()
                self.current_cap_fps = new_cap_fps
                self.current_detection_time = new_detection_time
            except queue.Empty: 
                # 如果队列为空，则保持使用上一次的值（不会归零/闪烁）
                pass 

            # 使用状态变量更新 UI
            self.fps_label.config(
                text=f"相机 FPS: {self.current_cap_fps:.1f} | 推理: {self.current_detection_time*1000:.1f}ms (每{self.worker.detection_interval}帧)"
            )
            self.stats_label.config(
                 text=f"分辨率: {CAMERA_WIDTH}x{CAMERA_HEIGHT}\n模型: {MODEL_PATH}\n设备: CPU\nFPS: {self.current_cap_fps:.1f}"
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
            
        # 以极短间隔（1ms）再次调度更新
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
             
        fname = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "_yolo_pi.jpg"
        path = os.path.join(PHOTO_SAVE_DIR, fname)
        try:
            # cv2.imwrite 接受 BGR 格式
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
        app_instance = App(root)
        root.mainloop()
    except Exception as e:
        print(f"应用启动失败: {e}")
        sys.exit(1)
