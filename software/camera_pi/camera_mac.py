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

# --- 导入 ultralytics 库 ---
try:
    # 尝试导入 PyTorch，确保 PyTorch 已正确安装且支持 MPS
    import torch
    if platform.system() == "Darwin" and not torch.backends.mps.is_available():
        # 如果是 macOS 但 MPS 不可用，将退回到 CPU，但需要通知用户
        print("警告：PyTorch 的 MPS 后端不可用，将使用 CPU 进行推理。")
        DEFAULT_DEVICE = 'cpu'
    elif platform.system() == "Darwin":
        DEFAULT_DEVICE = 'mps'
    else:
        DEFAULT_DEVICE = 'cpu' # 非 macOS 系统默认为 CPU

    from ultralytics import YOLO
except ImportError:
    messagebox.showerror("依赖缺失", "请先安装 ultralytics 库: pip install ultralytics")
    class YOLO:
        def __init__(self, *args, **kwargs):
            raise ImportError("ultralytics not found")
    DEFAULT_DEVICE = 'cpu' # 如果 ultralytics 都没装，给一个默认值

# --- 常量定义 ---

APP_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
# *** 更改模型路径为 PyTorch 模型 (.pt) ***
# 请确保您的 'models' 目录下有 yolov8n.pt 或其他 .pt 模型
COREML_MODEL_PATH = os.path.join(APP_ROOT_DIR, "models", "yolov8n.pt") 

CONFIDENCE_THRESHOLD = 0.4 
NMS_THRESHOLD = 0.4        
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720 # 摄像头实际捕获尺寸

# 推理目标 FPS
TARGET_CAP_FPS = 30
FRAME_TIME_MS = 1000 / TARGET_CAP_FPS # 约 33.33ms

# 模型推理尺寸
MODEL_INFERENCE_SIZE = 640
PREDICT_IMG_SIZE = (MODEL_INFERENCE_SIZE, MODEL_INFERENCE_SIZE) # (640, 640) HxW

# --- 线程安全队列 ---
processed_frame_queue = queue.Queue(maxsize=1) 
stats_queue = queue.Queue(maxsize=1) 

# --- 后台工作线程类 ---
class CameraWorker(threading.Thread):
    def __init__(self, model_path, classes):
        super().__init__()
        self.cap = None
        self.running = True
        self.net = None
        self.classes = classes
        self.model_path = model_path
        self.frame_count = 0
        # 保持 4 帧检测一次，以保证预览流畅度
        self.detection_interval = 4 
        
        # *** 设置推理设备为 MPS ***
        self.device = DEFAULT_DEVICE
        
    def _initialize_camera(self):
        """尝试初始化摄像头并设置 30 FPS"""
        self.cap = cv2.VideoCapture(0)
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH) 
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            
            # 明确设置 30 FPS 限制
            self.cap.set(cv2.CAP_PROP_FPS, TARGET_CAP_FPS) 
            
            actual_w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            print(f"相机工作线程启动，分辨率: {actual_w}x{actual_h}, 目标 FPS: {actual_fps}")
            return True
        return False

    def _load_yolo_model(self):
        """加载 PyTorch 模型并指定 MPS 设备"""
        if not os.path.exists(self.model_path):
             print(f"后台工作线程: 错误！模型文件不存在于: {self.model_path}")
             print("请确认已下载 PyTorch 模型文件（例如 yolov8n.pt）并放置在 'models/' 目录下。")
             return False

        try:
            # 加载 PyTorch 模型，ultralytics 会自动处理
            self.net = YOLO(self.model_path) 
            print(f"🎉 后台工作线程: YOLO 模型 ({os.path.basename(self.model_path)}) 加载成功。")
            print(f"🎉 后台工作线程: 推理设备已设置为 '{self.device}'。")
            # 预热模型 (第一次推理会比较慢)
            # self.net.predict(source=np.zeros((1, 640, 640, 3), dtype=np.uint8), device=self.device, verbose=False)
            return True
        except Exception as e:
            print(f"❌ PyTorch 模型加载失败: {e}")
            return False

    def detect_objects(self, img_bgr):
        """在帧上运行推理并绘制结果"""
        if not self.net:
            return img_bgr, 0.0

        start_detection = time.time()
        try:
            # *** 明确指定 device 为 self.device ('mps' 或 'cpu') ***
            results = self.net.predict(
                source=img_bgr, 
                conf=CONFIDENCE_THRESHOLD, 
                iou=NMS_THRESHOLD, 
                imgsz=PREDICT_IMG_SIZE,
                verbose=False, 
                device=self.device, 
            )
        except Exception as e:
            # 这里的错误通常是 PyTorch 或 MPS 运行时的错误
            print(f"PyTorch/MPS 推理错误: {e}")
            return img_bgr, 0.0

        detection_time = time.time() - start_detection
        result_frame = img_bgr.copy()
        
        if not results or not results[0].boxes:
            return result_frame, detection_time

        # 绘制结果
        res = results[0]
        for box in res.boxes:
            # 注意: MPS 设备上的张量需要先移动到 CPU 再转换为列表
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().int().tolist())
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
        if not self._initialize_camera():
            self.running = False
            return
            
        if not self._load_yolo_model():
            self.running = False
            if self.cap: self.cap.release()
            return

        last_frame_time = time.time()
        last_detected_frame = None
        detection_time = 0.0
        
        # 记录每秒帧率 (Cap FPS)
        fps_start_time = time.time()
        cap_frame_count = 0

        while self.running:
            
            # **帧率限制**: 强制 30 FPS 延迟
            # 计算需要等待的时间（毫秒转换为秒）
            current_time = time.time()
            elapsed_time = current_time - last_frame_time
            sleep_time = (FRAME_TIME_MS / 1000) - elapsed_time
            if sleep_time > 0:
                 time.sleep(sleep_time)
            
            # 更新时间戳
            last_frame_time = time.time()

            ret, current_frame_bgr = self.cap.read()
            if not ret:
                continue

            # 真实的相机捕获 FPS 统计
            cap_frame_count += 1
            if current_time - fps_start_time >= 1.0:
                 # 使用上次的 current_time 作为分母的起点，确保时间准确性
                 cap_fps = cap_frame_count / (current_time - fps_start_time) 
                 # 队列更新统计数据
                 if stats_queue.full():
                    try: stats_queue.get_nowait()
                    except queue.Empty: pass
                 stats_queue.put((cap_fps, detection_time))
                 
                 fps_start_time = current_time
                 cap_frame_count = 0
            
            # 使用上次检测到的帧作为当前显示帧的基准
            display_frame_bgr = current_frame_bgr.copy()

            # --- 性能分流逻辑 (只在工作线程执行检测) ---
            if self.frame_count >= self.detection_interval:
                processed_frame, detection_time = self.detect_objects(current_frame_bgr)
                last_detected_frame = processed_frame
                self.frame_count = 0 
            
            if last_detected_frame is not None:
                display_frame_bgr = last_detected_frame
            
            self.frame_count += 1

            # --- 更新帧队列：将处理好的帧传回主线程 ---
            if processed_frame_queue.full():
                try: processed_frame_queue.get_nowait()
                except queue.Empty: pass
            processed_frame_queue.put(display_frame_bgr)


        # --- 退出清理 ---
        if self.cap:
            self.cap.release()
        print("后台工作线程已退出。")

    def stop(self):
        self.running = False


# --- 相机应用主类 (Tkinter UI) ---
class App:
    def __init__(self, master):
        self.master = master
        
        # 此应用主要用于 macOS 上的 MPS 加速
        if platform.system() != "Darwin":
             msg = "错误：此版本专为 macOS (PyTorch + MPS) 设计。"
             messagebox.showerror("配置错误", msg)
             self.master.destroy()
             return

        # 1. 检查模型路径并在 UI 线程提前加载模型获取类别信息
        try:
            if not os.path.exists(COREML_MODEL_PATH):
                 raise FileNotFoundError(f"模型文件不存在。请确认路径: {COREML_MODEL_PATH}")

            # 仅加载模型以获取类别信息 (names)
            temp_model = YOLO(COREML_MODEL_PATH)
            self.classes = temp_model.names
            del temp_model
        except Exception as e:
            messagebox.showerror("模型加载失败", f"无法加载模型获取类别信息或路径错误: {e}")
            self.master.destroy()
            return
            
        # 更新应用标题以反映 MPS 模式
        self.master.title("macOS 高性能摄像头应用 (线程化 PyTorch + MPS) - 1280x720p")
        
        CONTROL_PANEL_WIDTH = 200
        self.MASTER_WIDTH = CAMERA_WIDTH + CONTROL_PANEL_WIDTH + 20
        self.MASTER_HEIGHT = CAMERA_HEIGHT + 20
        self.master.geometry(f"{self.MASTER_WIDTH}x{self.MASTER_HEIGHT}")
        self.master.resizable(True, True) 

        # 2. 启动工作线程
        self.worker = CameraWorker(COREML_MODEL_PATH, self.classes)
        self.worker.daemon = True 
        self.worker.start()
        
        if not self.worker.is_alive():
             messagebox.showerror("启动失败", "摄像头工作线程未能成功启动。")
             self.master.destroy()
             return

        self.after_id = None
        self.photo = None 
        self.init_ui()
        self.master.protocol("WM_DELETE_WINDOW", self.confirm_exit)

        # 3. 启动 Tkinter 的 UI 更新循环
        self.update_preview()


    def init_ui(self):
        """初始化 Tkinter 界面"""
        main_frame = tk.Frame(self.master, bg="#2c3e50", padx=10, pady=10)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 2. 右侧：按钮区域 (宽度固定)
        RIGHT_FRAME_WIDTH = 200 
        right_frame = tk.Frame(main_frame, bg="#34495e", padx=10, pady=10, width=RIGHT_FRAME_WIDTH)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0)) 
        right_frame.pack_propagate(False) 

        tk.Label(right_frame, text="操作面板 (线程化)", bg="#34495e", fg="#ecf0f1", font=('Arial', 12, 'bold')).pack(pady=10)

        base_button_style = {
            'width': 18, 'height': 2, 'fg': 'white', 'activeforeground': 'white',
            'font': ('Arial', 10, 'bold'), 'bd': 0, 'relief': tk.FLAT
        }

        btn_photo = tk.Button(right_frame, text="拍照 (1280x720)", command=self.take_photo, 
                              bg='#3498db', activebackground='#2980b9', **base_button_style)
        btn_photo.pack(pady=10)
        
        # 显示模型推理的 WxH 尺寸
        tk.Label(right_frame, text=f"分辨率 (Cam): {CAMERA_WIDTH}x{CAMERA_HEIGHT}", bg="#34495e", fg="#bdc3c7", font=('Arial', 10)).pack(pady=(20, 5))
        tk.Label(right_frame, text=f"模型输入 H x W: {PREDICT_IMG_SIZE[0]}x{PREDICT_IMG_SIZE[1]} (PyTorch)", bg="#34495e", fg="#bdc3c7", font=('Arial', 10)).pack(pady=5)
        # *** 更新加速文本以反映 MPS 模式 ***
        tk.Label(right_frame, text=f"加速: PyTorch ({self.worker.device.upper()})", bg="#34495e", fg="#bdc3c7", font=('Arial', 10)).pack(pady=5)
        
        btn_exit = tk.Button(right_frame, text="退出应用", command=self.confirm_exit, 
                             bg='#e74c3c', activebackground='#c0392b', **base_button_style)
        btn_exit.pack(pady=(40, 10))


        # 3. 左侧：视频预览区域
        left_frame = tk.Frame(main_frame, bg='black', bd=2, relief=tk.SUNKEN, 
                              width=CAMERA_WIDTH, height=CAMERA_HEIGHT)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True) 

        self.preview_label = tk.Label(left_frame, bg='black')
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        
        self.fps_label = tk.Label(left_frame, text="相机 FPS: 0.0 | 推理: 0.0ms", fg="#ecf0f1", bg="black", font=('Arial', 10, 'bold'))
        self.fps_label.place(relx=0.01, rely=0.01, anchor="nw")
        
        self.master.update_idletasks()


    def update_preview(self):
        """
        [主线程] 从队列中读取已处理的帧和性能数据并更新 UI。
        """
        try:
            # 1. 从队列获取帧 (非阻塞)
            display_frame_bgr = processed_frame_queue.get_nowait()
            
            # 2. 从队列获取统计数据 (非阻塞)
            cap_fps = 0.0
            detection_time = 0.0
            try:
                cap_fps, detection_time = stats_queue.get_nowait()
            except queue.Empty:
                pass # 如果统计数据没更新，保持上次的值

            # 3. 更新统计标签
            self.fps_label.config(text=f"相机 FPS: {cap_fps:.1f} (目标 {TARGET_CAP_FPS}) | 推理: {detection_time*1000:.1f}ms (每{self.worker.detection_interval}帧)")
            
            # 4. 图像转换和显示
            detected_frame_rgb = cv2.cvtColor(display_frame_bgr, cv2.COLOR_BGR2RGB)
            
            preview_width = self.preview_label.winfo_width()
            preview_height = self.preview_label.winfo_height()

            if preview_width > 0 and preview_height > 0:
                image = Image.fromarray(detected_frame_rgb)
                
                if preview_width != CAMERA_WIDTH or preview_height != CAMERA_HEIGHT:
                    image = image.resize((preview_width, preview_height), Image.Resampling.LANCZOS)
                
                self.photo = ImageTk.PhotoImage(image)
                self.preview_label.config(image=self.photo)
            
        except queue.Empty:
            pass # 队列为空是正常的，表示工作线程还没产生新帧
        except Exception as e:
            print(f"UI 更新错误: {e}")
            
        # 5. 调度下一次更新，间隔时间设置得极短 (1ms)
        self.after_id = self.master.after(1, self.update_preview)

    def take_photo(self):
        """[主线程] 拍照操作：从队列中获取最新的带框帧并保存。"""
        if not self.worker.is_alive():
             messagebox.showerror("拍照失败", "工作线程未运行。")
             return
             
        if not os.path.exists("photos"):
            os.makedirs("photos")

        # 尝试从队列中获取最新的已处理帧
        frame_bgr = None
        try:
            # 清空队列，确保拿到最新的那一帧
            while not processed_frame_queue.empty():
                 frame_bgr = processed_frame_queue.get_nowait()
        except queue.Empty:
             pass
             
        if frame_bgr is None:
             messagebox.showerror("拍照失败", "未获取到有效的帧数据，请等待视频流启动。")
             return

        fname = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "_yolo_mps_threaded.jpg"
        path = os.path.join("photos", fname)

        cv2.imwrite(path, frame_bgr)
        messagebox.showinfo("照片已保存", f"带识别框的 1280x720 照片已保存为: {path}")

    def confirm_exit(self):
        """停止线程并退出应用。"""
        if messagebox.askyesno("退出", "你真的要退出吗？"):
            # 1. 停止工作线程
            if self.worker.is_alive():
                self.worker.stop()
                self.worker.join(timeout=2) # 等待线程安全退出

            # 2. 停止主线程循环
            if self.after_id:
                self.master.after_cancel(self.after_id)
                
            self.master.destroy()

if __name__ == "__main__":
    try:
        # 强制检查平台，MPS 仅在 macOS 上可用
        if platform.system() != "Darwin":
             msg = "错误：此高性能版本专为 macOS (PyTorch + MPS) 设计。"
             messagebox.showerror("配置错误", msg)
             sys.exit(1)
             
        # 避免 Tkinter 在 macOS 上出现双 Dock 图标 (需要 pyobjc)
        if platform.system() == "Darwin":
            try:
                import AppKit
                AppKit.NSApp.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
            except ImportError:
                pass

        root = tk.Tk()
        app_instance = App(root)
        root.mainloop()
    except Exception as e:
        print(f"应用启动失败: {e}")
        sys.exit(1)
