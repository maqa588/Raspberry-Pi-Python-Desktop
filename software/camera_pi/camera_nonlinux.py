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

# --- 路径调整 ---
current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
sys.path.insert(0, project_root)

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

CONFIDENCE_THRESHOLD = 0.4
NMS_THRESHOLD = 0.4
INPUT_SIZE = (640, 640) 

# --- 相机应用主类 (CV2 版本) ---
class CameraApp:
    def __init__(self, master):
        self.master = master
        self.master.title(f"{platform.system()} 桌面摄像头应用 (YOLOv5 检测)")
        
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
        
        # 性能优化参数
        self.frame_count = 0
        self.detection_interval = 5  # 每 5 帧进行一次 YOLO 检测
        self.last_detected_frame = None # 存储上次带框选的帧
        self.detection_time = 0.0 # 存储上次检测时间
        
        # YOLO 模型相关属性
        self.net = None
        self.classes = []
        self._load_yolo_model()
        
        self.master.protocol("WM_DELETE_WINDOW", self.confirm_exit)

        self.init_ui()
        self.update_preview()

    def _initialize_camera_robust(self, retries=10, delay_ms=500):
        """尝试初始化摄像头，以解决 macOS 权限提示延迟的问题。"""
        print(f"尝试初始化摄像头 (0)，最多重试 {retries} 次...")
        
        for attempt in range(retries):
            if self.cap:
                self.cap.release()
            
            # 使用默认后端
            self.cap = cv2.VideoCapture(0)
            
            if self.cap.isOpened():
                print(f"摄像头在第 {attempt + 1} 次尝试时成功打开。")
                # 尝试设置高分辨率，获取更好的检测效果
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
            
            # 保持使用 CPU 后端以确保兼容性，但会利用 MKL/OpenBLAS 优化
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU) 

            print(f"YOLOv5 Model loaded from: {YOLO_MODEL_PATH}. DNN Target set to CPU.")

        except FileNotFoundError:
            messagebox.showerror("模型文件缺失", f"YOLOv5s 模型文件或类别文件未找到。")
            self.net = None
        except Exception as e:
            messagebox.showerror("模型加载失败", f"加载 YOLO 模型时发生错误: {e}")
            self.net = None 

    def init_ui(self):
        """初始化 Tkinter 界面，使用 pack 布局并修复宽度问题。"""
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        # 文件菜单和关于菜单略... (为简洁省略，但实际应保留)

        # 1. 主内容区域布局
        main_frame = tk.Frame(self.master, bg="#2c3e50", padx=10, pady=10)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 2. 右侧：按钮区域 (先 pack 右侧，并设置一个固定的最小宽度)
        # 关键修复：确保 right_frame 宽度固定
        RIGHT_FRAME_WIDTH = 180 
        right_frame = tk.Frame(main_frame, bg="#34495e", padx=10, pady=10, width=RIGHT_FRAME_WIDTH)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0)) # 右侧靠右，垂直填充
        right_frame.pack_propagate(False) # 关键：防止内部组件影响其固定宽度

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


        # 3. 左侧：视频预览区域
        # 关键修复：left_frame 填充剩余空间
        left_frame = tk.Frame(main_frame, bg='black', bd=2, relief=tk.SUNKEN)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True) # 占据所有剩余空间

        self.preview_label = tk.Label(left_frame, bg='black')
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        
        self.fps_label = tk.Label(left_frame, text="FPS: 0.0 | 推理: 0.0ms", fg="#ecf0f1", bg="black", font=('Arial', 10, 'bold'))
        self.fps_label.place(relx=0.01, rely=0.01, anchor="nw")
        
        self.master.update_idletasks()


    def detect_objects(self, img_bgr):
        """
        在给定的图像帧上运行 YOLOv5 推理并绘制结果。
        """
        if not self.net:
            return img_bgr 

        height, width, _ = img_bgr.shape
        
        # 1. 创建 Blob
        blob = cv2.dnn.blobFromImage(img_bgr, 1/255.0, INPUT_SIZE, swapRB=True, crop=False) 
        
        # 2. 运行推理
        self.net.setInput(blob)
        output_layers_names = self.net.getUnconnectedOutLayersNames()
        outputs = self.net.forward(output_layers_names)
        
        # 3. 后处理
        boxes = []
        confidences = []
        class_ids = []
        
        output_data = outputs[0]
        if output_data.ndim == 3:
            output_data = output_data[0] # 获取 (N, 85) 维度
            
        for detection in output_data:
            # 这里的 detection 是 [cx, cy, w, h, objectness, class_scores...]
            objectness_score = detection[4]
            class_scores = detection[5:]
            
            # 确保 objectness 足够高
            if objectness_score > CONFIDENCE_THRESHOLD:
                class_id = np.argmax(class_scores)
                # 最终置信度：Objectness * Class Score
                confidence = objectness_score * class_scores[class_id] 
                
                if confidence > CONFIDENCE_THRESHOLD:
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
        indices = cv2.dnn.NMSBoxes(boxes, confidences, NMS_THRESHOLD, NMS_THRESHOLD)
        
        # 5. 绘制结果
        result_frame = img_bgr.copy() # 在副本上绘制
        if len(indices) > 0:
            for i in indices.flatten():
                box = boxes[i]
                x, y, w, h = box
                label = str(self.classes[class_ids[i]]) if class_ids[i] < len(self.classes) else "Unknown"
                confidence = confidences[i]
                
                color = (0, 255, 0) # 绿色 BGR
                cv2.rectangle(result_frame, (x, y), (x + w, y + h), color, 2)
                
                text = f"{label}: {confidence:.2f}"
                # 确保文本不会超出顶部边界
                text_y = max(y - 10, 30) 
                cv2.putText(result_frame, text, (x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        return result_frame # 返回 BGR 格式的图像

    def update_preview(self):
        """
        捕获帧，执行条件检测，并显示。
        这是性能优化的核心部分。
        """
        if not self.cap or not self.cap.isOpened():
             self.master.after(1000, self.confirm_exit)
             return
             
        # FPS 计时
        current_time = time.time()
        fps = 1.0 / (current_time - self.last_time) if (current_time - self.last_time) > 0 else 0
        self.last_time = current_time
        self.frame_count += 1
        
        # 捕获帧 (BGR)
        ret, current_frame_bgr = self.cap.read()
        
        if not ret:
            self.master.after(100, self.update_preview) 
            return
        
        display_frame_bgr = current_frame_bgr.copy()
        
        # --- 性能分流逻辑 ---
        if self.frame_count % self.detection_interval == 0 and self.net:
            # 执行目标检测（耗时操作）
            start_detection = time.time()
            self.last_detected_frame = self.detect_objects(current_frame_bgr)
            self.detection_time = time.time() - start_detection
            display_frame_bgr = self.last_detected_frame
            
        elif self.last_detected_frame is not None:
            # 如果不是检测帧，但之前有检测结果，我们把框选结果叠加到当前帧上
            # 这是一个简化的方法：直接显示上次带框的帧，保持框选不动
            display_frame_bgr = self.last_detected_frame
        
        # --- 图像显示逻辑 ---
        detected_frame_rgb = cv2.cvtColor(display_frame_bgr, cv2.COLOR_BGR2RGB)
        
        # 调整大小以适应预览框
        preview_width = self.preview_label.winfo_width()
        preview_height = self.preview_label.winfo_height()
        
        if preview_width > 0 and preview_height > 0:
            # 使用 PIL 缩放
            image = Image.fromarray(detected_frame_rgb).resize((preview_width, preview_height), Image.LANCZOS)
            
            self.photo = ImageTk.PhotoImage(image)
            self.preview_label.config(image=self.photo)
        
        # 更新状态标签
        self.fps_label.config(text=f"FPS: {fps:.1f} | 推理: {self.detection_time*1000:.1f}ms (每{self.detection_interval}帧)")
        
        # 循环更新
        self.after_id = self.master.after(30, self.update_preview)

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
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        detected_frame_bgr = self.detect_objects(frame_bgr) # 注意：这里传入的是 BGR 帧
        
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
        sys.exit(1)
