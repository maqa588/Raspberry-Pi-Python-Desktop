import os
import sys
import datetime
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, Image
import numpy as np
import cv2 
import time 
import platform

# --- 导入 ultralytics 库 ---
try:
    from ultralytics import YOLO
except ImportError:
    messagebox.showerror("依赖缺失", "请先安装 ultralytics 库: pip install ultralytics")
    class YOLO:
        def __init__(self, *args, **kwargs):
            raise ImportError("ultralytics not found")

# --- 路径调整以适应项目结构 ---
current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)

# --- YOLOv11n Core ML 配置 (专为 macOS 优化) ---
# 已更新为 YOLOv11n 模型
COREML_MODEL_PATH = os.path.join(current_dir, "models", "yolov11n_coreml")

CONFIDENCE_THRESHOLD = 0.4 # 检测框置信度阈值
NMS_THRESHOLD = 0.4        # 非极大值抑制阈值
INPUT_SIZE = (640, 640) 

# --- 相机应用主类 ---
class CameraApp:
    def __init__(self, master):
        self.master = master
        
        # 强制检查平台和 Core ML 文件
        if platform.system() != "Darwin" or not os.path.exists(COREML_MODEL_PATH):
             msg = "错误：此版本专为 macOS Core ML 设计，请确保：\n1. 操作系统为 macOS。\n2. models 目录下存在 yolov11n_coreml (.mlpackage) 文件包。"
             messagebox.showerror("配置错误", msg)
             self.master.destroy()
             return

        self.master.title("macOS 高性能摄像头应用 (YOLOv11n Core ML/ANE)")
        
        self.MASTER_WIDTH = 1200
        self.MASTER_HEIGHT = 700
        self.master.geometry(f"{self.MASTER_WIDTH}x{self.MASTER_HEIGHT}")
        self.master.resizable(True, True) 

        self.cap = None
        if not self._initialize_camera_robust(retries=10, delay_ms=500):
            messagebox.showerror("相机错误", "无法访问本机摄像头。请检查权限和连接。")
            self.master.destroy()
            return

        self.preview_label = None
        self.fps_label = None
        self.last_time = time.time()
        self.after_id = None
        self.photo = None 
        
        # 优化设置：每 3 帧进行一次 YOLO 检测
        self.frame_count = 0
        self.detection_interval = 3 
        self.last_detected_frame = None 
        self.detection_time = 0.0 
        
        self.net = None
        self.classes = {} 
        self.device = 'coreml' # 强制标记使用 Core ML
        self._load_yolo_model()
        
        if not self.net:
             self.master.destroy()
             return

        self.master.protocol("WM_DELETE_WINDOW", self.confirm_exit)

        self.init_ui()
        # 初始加载时强制检测一次
        self.frame_count = self.detection_interval - 1 
        self.update_preview()

    def _initialize_camera_robust(self, retries=10, delay_ms=500):
        """尝试初始化摄像头并设置参数"""
        for attempt in range(retries):
            if self.cap:
                self.cap.release()
            
            self.cap = cv2.VideoCapture(0)
            
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280) 
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                # 尝试设置相机捕获帧率为 30 FPS，以支持流畅的 Core ML 运行
                self.cap.set(cv2.CAP_PROP_FPS, 30) 
                return True
            
            time.sleep(delay_ms / 1000) 
            
        return False

    def _load_yolo_model(self):
        """加载 Core ML 模型"""
        try:
            if not os.path.exists(COREML_MODEL_PATH):
                 raise FileNotFoundError(f"Core ML 模型文件未找到。请检查 {COREML_MODEL_PATH}")
                 
            self.net = YOLO(COREML_MODEL_PATH)
            self.classes = self.net.names
            print("🎉 YOLOv11n 模型 (Core ML) 加载成功。ANE 加速已启用。")

        except Exception as e:
            messagebox.showerror("模型加载失败", f"加载 Core ML 模型时发生致命错误: {e}")
            self.net = None 

    def init_ui(self):
        """初始化 Tkinter 界面"""
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        main_frame = tk.Frame(self.master, bg="#2c3e50", padx=10, pady=10)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 2. 右侧：按钮区域 (宽度固定)
        RIGHT_FRAME_WIDTH = 180 
        right_frame = tk.Frame(main_frame, bg="#34495e", padx=10, pady=10, width=RIGHT_FRAME_WIDTH)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0)) 
        right_frame.pack_propagate(False) 

        tk.Label(right_frame, text="操作面板", bg="#34495e", fg="#ecf0f1", font=('Arial', 12, 'bold')).pack(pady=10)

        base_button_style = {
            'width': 15, 'height': 2, 'fg': 'white', 'activeforeground': 'white',
            'font': ('Arial', 10, 'bold'), 'bd': 0, 'relief': tk.FLAT
        }

        btn_photo = tk.Button(right_frame, text="拍照 (带识别框)", command=self.take_photo, 
                              bg='#3498db', activebackground='#2980b9', **base_button_style)
        btn_photo.pack(pady=10)

        btn_exit = tk.Button(right_frame, text="退出应用", command=self.confirm_exit, 
                             bg='#e74c3c', activebackground='#c0392b', **base_button_style)
        btn_exit.pack(pady=10)


        # 3. 左侧：视频预览区域
        left_frame = tk.Frame(main_frame, bg='black', bd=2, relief=tk.SUNKEN)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True) 

        self.preview_label = tk.Label(left_frame, bg='black')
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        
        self.fps_label = tk.Label(left_frame, text="FPS: 0.0 | 推理: 0.0ms", fg="#ecf0f1", bg="black", font=('Arial', 10, 'bold'))
        self.fps_label.place(relx=0.01, rely=0.01, anchor="nw")
        
        self.master.update_idletasks()


    def detect_objects(self, img_bgr):
        """
        [Core ML 逻辑] 在图像帧上运行推理并绘制结果。
        Core ML 模型由 macOS 原生驱动，无需指定 device。
        """
        if not self.net:
            return img_bgr 

        # 1. 运行推理 (ultralytics 自动调用 Core ML 引擎)
        results = self.net.predict(
            source=img_bgr, 
            conf=CONFIDENCE_THRESHOLD, 
            iou=NMS_THRESHOLD, 
            imgsz=INPUT_SIZE[0],
            verbose=False, 
            # 不需要 device 参数，Core ML 自动使用 ANE/GPU
        )

        result_frame = img_bgr.copy()
        
        if not results or not results[0].boxes:
            return result_frame

        # 2. 绘制结果
        res = results[0]
        
        # 遍历所有检测到的边界框
        for box in res.boxes:
            # 提取边界框坐标 (x1, y1, x2, y2)。必须调用 .cpu().int().tolist()
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().int().tolist())
            conf = box.conf[0].item()                       # 提取置信度
            cls = int(box.cls[0].item())                    # 提取类别ID
            
            label = self.classes.get(cls, "Unknown")
            color = (0, 255, 0) # 绿色 BGR
            
            # 绘制矩形
            cv2.rectangle(result_frame, (x1, y1), (x2, y2), color, 2)
            
            # 绘制标签和置信度
            text = f"{label}: {conf:.2f}"
            text_y = max(y1 - 10, 30) 
            cv2.putText(result_frame, text, (x1, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        return result_frame 

    def update_preview(self):
        """
        捕获帧，执行条件检测，并显示。
        """
        if not self.cap or not self.cap.isOpened():
             self.master.after(1000, self.confirm_exit)
             return
             
        current_time = time.time()
        fps = 1.0 / (current_time - self.last_time) if (current_time - self.last_time) > 0 else 0
        self.last_time = current_time
        self.frame_count += 1
        
        ret, current_frame_bgr = self.cap.read()
        
        if not ret:
            self.master.after(1, self.update_preview) 
            return
        
        display_frame_bgr = current_frame_bgr.copy()
        
        # --- 性能分流逻辑 ---
        if self.frame_count >= self.detection_interval and self.net:
            # 执行目标检测
            start_detection = time.time()
            self.last_detected_frame = self.detect_objects(current_frame_bgr)
            self.detection_time = time.time() - start_detection
            self.frame_count = 0 
            
            if self.last_detected_frame is not None:
                display_frame_bgr = self.last_detected_frame.copy()
            
        elif self.last_detected_frame is not None:
            # 非检测帧，显示上次带框的帧以保持视觉连贯性
            display_frame_bgr = self.last_detected_frame.copy()
        
        # --- 图像显示逻辑 ---
        detected_frame_rgb = cv2.cvtColor(display_frame_bgr, cv2.COLOR_BGR2RGB)
        
        preview_width = self.preview_label.winfo_width()
        preview_height = self.preview_label.winfo_height()
        
        if preview_width > 0 and preview_height > 0:
            # 使用 LANCZOS 进行高质量缩放
            image = Image.fromarray(detected_frame_rgb).resize((preview_width, preview_height), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(image)
            self.preview_label.config(image=self.photo)
        
        # 更新状态标签
        model_info = "Core ML (ANE)"
        self.fps_label.config(text=f"FPS: {fps:.1f} | 推理 ({model_info}): {self.detection_time*1000:.1f}ms (每{self.detection_interval}帧)")
        
        # 最小延迟（1ms），让 CPU 尽可能快地处理 UI 渲染和事件
        self.after_id = self.master.after(1, self.update_preview)

    def take_photo(self):
        """拍摄照片，运行检测并保存带识别框的图像。"""
        if not self.cap or not self.cap.isOpened():
            messagebox.showerror("拍照失败", "摄像头未成功初始化。")
            return
            
        if not os.path.exists("photos"):
            os.makedirs("photos")
        
        fname = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "_yolo_desktop.jpg"
        path = os.path.join("photos", fname)

        ret, frame_bgr = self.cap.read()
        if not ret:
            messagebox.showerror("拍照失败", "无法从摄像头捕获图像。")
            return
        
        # 拍照时强制执行一次检测
        detected_frame_bgr = self.detect_objects(frame_bgr) 
        
        cv2.imwrite(path, detected_frame_bgr)
        
        messagebox.showinfo("照片已保存", f"带识别框的照片已保存为: {path}")

    def confirm_exit(self):
        """释放摄像头并退出应用。"""
        if messagebox.askyesno("退出", "你真的要退出吗？"):
            if self.cap and self.cap.isOpened():
                self.cap.release()
            
            if self.after_id:
                self.master.after_cancel(self.after_id)
                
            self.master.destroy()

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = CameraApp(root)
        root.mainloop()
    except Exception as e:
        print(f"应用启动失败: {e}")
        if "ultralytics" in str(e):
             messagebox.showerror("启动失败", "缺少 ultralytics 依赖项，请检查安装。")
        sys.exit(1)
