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

# --- 路径调整以适应新的 software/camera_pi/ 目录结构 ---
current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)

# 向上追溯三级以找到项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
sys.path.insert(0, project_root)
# --- 路径调整结束 ---

# 导入占位函数以确保代码完整性
try:
    from system.button.about import show_system_about, show_developer_about
except ImportError:
    def show_system_about(root): messagebox.showinfo("系统信息", "此为系统信息占位符。")
    def show_developer_about(root): messagebox.showinfo("开发者信息", "此为开发者信息占位符。")
    print("警告: 未能导入 system.button.about，使用占位函数。")

# --- YOLOv5 配置和工具 ---
YOLO_MODEL_PATH = os.path.join(current_dir, "models", "yolov5s.onnx")
CLASS_NAMES_PATH = os.path.join(current_dir, "models", "coco.names")

CONFIDENCE_THRESHOLD = 0.5
NMS_THRESHOLD = 0.4
INPUT_SIZE = (640, 640) 

# --- 相机应用主类 (CV2 版本) ---
class CameraApp:
    def __init__(self, master):
        self.master = master
        self.master.title(f"{platform.system()} 桌面摄像头应用 (YOLOv5 检测)")
        
        # 放大窗口尺寸以适应桌面
        self.MASTER_WIDTH = 1000
        self.MASTER_HEIGHT = 600
        self.master.geometry(f"{self.MASTER_WIDTH}x{self.MASTER_HEIGHT}")
        self.master.resizable(True, True) 

        self.cap = None
        
        if not self._initialize_camera_robust(retries=10, delay_ms=500):
            # 如果摄像头初始化失败，直接退出应用，避免后续错误
            messagebox.showerror("相机错误", "无法访问本机摄像头。请检查权限和连接。")
            self.master.destroy()
            return

        self.preview_label = None
        self.fps_label = None
        self.last_time = time.time()
        self.after_id = None
        self.photo = None # 用于防止 PhotoImage 被垃圾回收
        
        # YOLO 模型相关属性
        self.net = None
        self.classes = []
        self._load_yolo_model()
        
        self.master.protocol("WM_DELETE_WINDOW", self.confirm_exit)

        self.init_ui()
        self.update_preview()

    def _initialize_camera_robust(self, retries=10, delay_ms=500):
        """尝试初始化摄像头，并进行多次重试，以解决 macOS 权限提示延迟的问题。"""
        print(f"尝试初始化摄像头 (0)，最多重试 {retries} 次...")
        
        for attempt in range(retries):
            if self.cap:
                self.cap.release()
            
            # 使用 cv2.CAP_DSHOW 可能会改善 Windows 性能，但 macOS 保持默认
            self.cap = cv2.VideoCapture(0)
            
            if self.cap.isOpened():
                print(f"摄像头在第 {attempt + 1} 次尝试时成功打开。")
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280) 
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                return True
            
            print(f"摄像头打开失败 {attempt + 1}/{retries}。等待 {delay_ms/1000} 秒...")
            time.sleep(delay_ms / 1000) 
            
        print("所有摄像头初始化尝试均失败。")
        return False

    def _load_yolo_model(self):
        """加载 YOLO 模型和类别名称，并尝试设置 DNN 后端加速。"""
        try:
            with open(CLASS_NAMES_PATH, 'r', encoding='utf-8') as f:
                self.classes = [line.strip() for line in f.readlines()]
            
            self.net = cv2.dnn.readNet(YOLO_MODEL_PATH)
            
            # --- 性能优化尝试 ---
            # 默认使用 CPU (MKL/OpenBLAS 加速)
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            
            # 在 macOS 上，如果安装了支持 Metal/OpenCL 的 OpenCV 版本，可以尝试 TARGET_OPENCL 或 TARGET_CPU
            # 由于默认安装的 OpenCV 很难利用 GPU，我们保留 TARGET_CPU 以确保兼容性，但性能瓶颈依然在 CPU 推理。
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU) 

            # 注意：若要真正启用 GPU (如 CUDA/cuDNN)，需要专门编译 OpenCV，这在虚拟环境中非常复杂。
            print(f"YOLOv5 Model loaded from: {YOLO_MODEL_PATH}. DNN Target set to CPU.")

        except FileNotFoundError:
            messagebox.showerror("模型文件缺失", f"YOLOv5s 模型文件或类别文件未找到。\n请确保文件位于:\n{YOLO_MODEL_PATH}")
            self.net = None
        except Exception as e:
            messagebox.showerror("模型加载失败", f"加载 YOLO 模型时发生错误: {e}")
            self.net = None 

    def init_ui(self):
        """初始化 Tkinter 界面，使用原生菜单栏和新布局。"""
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        # 菜单略...

        # 1. 主内容区域布局
        main_frame = tk.Frame(self.master, bg="#2c3e50", padx=10, pady=10)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 2. 左侧：视频预览区域 (使用更大的尺寸)
        # 关键修复点：允许 left_frame 填充并扩展
        left_frame = tk.Frame(main_frame, bg='black', bd=2, relief=tk.SUNKEN)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # 关键修复点：使用中央 Frame 来容纳 Label，确保 Label 居中
        self.preview_label = tk.Label(left_frame, bg='black')
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        
        self.fps_label = tk.Label(left_frame, text="FPS: 0.0", fg="#ecf0f1", bg="black", font=('Arial', 10, 'bold'))
        self.fps_label.place(relx=0.01, rely=0.01, anchor="nw")

        # 3. 右侧：按钮区域 
        right_frame = tk.Frame(main_frame, bg="#34495e", padx=10, pady=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        tk.Label(right_frame, text="操作面板", bg="#34495e", fg="#ecf0f1", font=('Arial', 12, 'bold')).pack(pady=10)

        base_button_style = {
            'width': 15,
            'height': 2,
            'fg': 'white', 
            'activeforeground': 'white',
            'font': ('Arial', 10, 'bold'),
            'bd': 0, 
            'relief': tk.FLAT
        }

        btn_photo = tk.Button(right_frame, text="拍照 (带识别框)", command=self.take_photo, 
                              bg='#3498db', activebackground='#2980b9', **base_button_style)
        btn_photo.pack(pady=10)

        btn_exit = tk.Button(right_frame, text="退出应用", command=self.confirm_exit, 
                             bg='#e74c3c', activebackground='#c0392b', **base_button_style)
        btn_exit.pack(pady=10)
        
        self.master.update_idletasks()


    def detect_objects(self, frame):
        """
        在给定的图像帧上运行 YOLOv5 推理并绘制结果。
        修复了 YOLOv5 ONNX 输出的解析逻辑。
        """
        if not self.net:
            return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) 

        img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        height, width, _ = img.shape
        
        # 1. 创建 Blob
        # swapRB=True 是 YOLOv5 的常见要求 (BGR -> RGB)
        blob = cv2.dnn.blobFromImage(img, 1/255.0, INPUT_SIZE, swapRB=True, crop=False) 
        
        # 2. 运行推理
        self.net.setInput(blob)
        output_layers_names = self.net.getUnconnectedOutLayersNames()
        outputs = self.net.forward(output_layers_names)
        
        # 3. 后处理（解析 YOLOv5 原始输出）
        boxes = []
        confidences = []
        class_ids = []
        
        # outputs[0] 是 (1, num_detections, 5 + num_classes)
        # 关键修复点：确保循环遍历检测结果
        output_data = outputs[0]
        # 如果 output_data 是 (1, N, 85) 的形式，则使用 output_data[0]
        if output_data.ndim == 3:
            output_data = output_data[0]
            
        for detection in output_data:
            # detection[0:4] = cx, cy, w, h
            # detection[4] = objectness score
            # detection[5:] = class scores
            
            scores = detection[5:] 
            class_id = np.argmax(scores)
            confidence = scores[class_id] * detection[4] # 乘以目标置信度
            
            if confidence > CONFIDENCE_THRESHOLD:
                # 坐标归一化到 (0, 1) 范围，需乘以图像尺寸
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)
                
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)

        # 4. 非极大值抑制 (NMS)
        indices = cv2.dnn.NMSBoxes(boxes, confidences, CONFIDENCE_THRESHOLD, NMS_THRESHOLD)
        
        # 5. 绘制结果
        if len(indices) > 0:
            for i in indices.flatten():
                box = boxes[i]
                x, y, w, h = box
                label = str(self.classes[class_ids[i]]) if class_ids[i] < len(self.classes) else "Unknown"
                confidence = confidences[i]
                
                # 随机生成颜色以区分不同类别（可选，这里保持绿色）
                color = (0, 255, 0) # 绿色 BGR
                cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
                
                text = f"{label}: {confidence:.2f}"
                cv2.putText(img, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        return img # 返回 BGR 格式的图像

    def update_preview(self):
        """捕获帧，进行检测，并显示。"""
        if not self.cap or not self.cap.isOpened():
             self.master.after(1000, self.confirm_exit)
             return
             
        # FPS 计时
        current_time = time.time()
        fps = 1.0 / (current_time - self.last_time) if (current_time - self.last_time) > 0 else 0
        self.last_time = current_time
        
        # 捕获帧 (BGR)
        ret, frame_bgr = self.cap.read()
        
        if not ret:
            print("无法读取摄像头帧，等待重试...")
            self.master.after(100, self.update_preview) 
            return

        # 目标检测 (返回 BGR 图像)
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        start_detection = time.time()
        detected_frame_bgr = self.detect_objects(frame_rgb)
        detection_time = time.time() - start_detection
        
        # BGR -> RGB 用于 PIL 显示
        detected_frame_rgb = cv2.cvtColor(detected_frame_bgr, cv2.COLOR_BGR2RGB)
        
        # 调整大小以适应预览框
        preview_width = self.preview_label.winfo_width()
        preview_height = self.preview_label.winfo_height()
        
        if preview_width > 0 and preview_height > 0:
            # 缩放图像以适应 Label
            image = Image.fromarray(detected_frame_rgb).resize((preview_width, preview_height), Image.LANCZOS)
            
            # 显示
            self.photo = ImageTk.PhotoImage(image)
            self.preview_label.config(image=self.photo)
        
        # 更新 FPS 和检测时间
        self.fps_label.config(text=f"FPS: {fps:.1f} | 推理: {detection_time*1000:.1f}ms")
        
        # 循环更新
        # 如果检测时间过长，可以适当减少调用间隔（但 30ms 已经是 Tkinter 动画的最小间隔了）
        self.after_id = self.master.after(30, self.update_preview)

    # ... take_photo 和 confirm_exit 函数保持不变 ...
    def take_photo(self):
        """
        拍摄照片，运行检测并保存带识别框的图像。
        """
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
        
        height, width, _ = frame_bgr.shape
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        detected_frame_bgr = self.detect_objects(frame_rgb)

        cv2.imwrite(path, detected_frame_bgr)
        
        messagebox.showinfo("照片已保存", f"带识别框的照片已保存为: {path} (分辨率: {width}x{height})")


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
        sys.exit(1)
