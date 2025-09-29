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

# --- 路径调整以适应项目结构 ---
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

# --- YOLOv5 7.0 配置 ---
# 请确保您的 yolov5s.onnx 或相应模型文件位于 models 目录下
YOLO_MODEL_PATH = os.path.join(current_dir, "models", "yolov5s.onnx")
CLASS_NAMES_PATH = os.path.join(current_dir, "models", "coco.names")

CONFIDENCE_THRESHOLD = 0.4 # 检测框置信度阈值
NMS_THRESHOLD = 0.4        # 非极大值抑制阈值
INPUT_SIZE = (640, 640) 

# --- 相机应用主类 ---
class CameraApp:
    def __init__(self, master):
        self.master = master
        self.master.title(f"{platform.system()} 桌面摄像头应用 (YOLOv5 7.0 检测)")
        
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
        
        # 性能优化参数：每 5 帧进行一次 YOLO 检测
        self.frame_count = 0
        self.detection_interval = 5 
        self.last_detected_frame = None 
        self.detection_time = 0.0 
        
        self.net = None
        self.classes = []
        self._load_yolo_model()
        
        self.master.protocol("WM_DELETE_WINDOW", self.confirm_exit)

        self.init_ui()
        self.update_preview()

    def _initialize_camera_robust(self, retries=10, delay_ms=500):
        """尝试初始化摄像头"""
        # ... (略)
        for attempt in range(retries):
            if self.cap:
                self.cap.release()
            
            # 使用默认后端
            self.cap = cv2.VideoCapture(0)
            
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280) 
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                return True
            
            time.sleep(delay_ms / 1000) 
            
        return False

    def _load_yolo_model(self):
        """加载 YOLO 模型并设置平台加速目标（DirectML/Metal 提示）"""
        try:
            with open(CLASS_NAMES_PATH, 'r', encoding='utf-8') as f:
                self.classes = [line.strip() for line in f.readlines()]
            
            self.net = cv2.dnn.readNet(YOLO_MODEL_PATH)
            
            # --- 平台特定的加速目标设置 ---
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            
            if platform.system() == "Windows":
                # Windows上尝试OpenCL/OpenVINO (如果可用)，模拟DirectML加速
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL) 
                print("OpenCV DNN Target: 尝试 OPENCL (Windows)")
                print("提示: 真正的 DirectML 加速需要特殊编译的 OpenCV 版本，当前为通用加速设置。")
            elif platform.system() == "Darwin": # macOS
                # macOS 保持 optimized CPU，会使用 Metal/MPS 优化后的 CPU 路径
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                print("OpenCV DNN Target: CPU (macOS)")
                print("提示: 真正的 Metal 加速需要特殊编译的 OpenCV 版本，当前为 CPU 优化路径。")
            else: # Linux 或其他
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                print("OpenCV DNN Target: CPU (Other OS)")

        except FileNotFoundError:
            messagebox.showerror("模型文件缺失", f"YOLO 模型文件或类别文件未找到。请检查 {YOLO_MODEL_PATH}")
            self.net = None
        except Exception as e:
            messagebox.showerror("模型加载失败", f"加载 YOLO 模型时发生错误: {e}")
            self.net = None 

    def init_ui(self):
        """初始化 Tkinter 界面，使用固定宽度的右侧面板。"""
        # ... (布局代码保持不变，确保右侧按钮区宽度固定)
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        main_frame = tk.Frame(self.master, bg="#2c3e50", padx=10, pady=10)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 2. 右侧：按钮区域 (宽度固定，防止侵蚀)
        RIGHT_FRAME_WIDTH = 180 
        right_frame = tk.Frame(main_frame, bg="#34495e", padx=10, pady=10, width=RIGHT_FRAME_WIDTH)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0)) 
        right_frame.pack_propagate(False) # 关键：防止内部组件影响其固定宽度

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
        [YOLOv5 7.0 专用解析] 在图像帧上运行推理并绘制结果。
        """
        if not self.net:
            return img_bgr 

        height, width, _ = img_bgr.shape
        
        # 1. 创建 Blob
        blob = cv2.dnn.blobFromImage(img_bgr, 1/255.0, INPUT_SIZE, swapRB=True, crop=False) 
        self.net.setInput(blob)
        output_layers_names = self.net.getUnconnectedOutLayersNames()
        outputs = self.net.forward(output_layers_names)
        
        # 2. 后处理
        boxes = []
        confidences = []
        class_ids = []
        
        # YOLO ONNX 输出通常是 (1, N, 5 + num_classes)
        output_data = outputs[0]
        if output_data.ndim == 3:
            output_data = output_data[0] 
            
        for detection in output_data:
            # 数组结构: [center_x, center_y, box_w, box_h, objectness, class_1_score, class_2_score, ...]
            
            # 步骤 A: 提取分数
            objectness_score = detection[4]
            # 类别分数从索引 5 开始
            class_scores = detection[5:]
            class_id = np.argmax(class_scores)
            
            # 最终置信度：Objectness * Class Score
            confidence = objectness_score * class_scores[class_id] 
            
            if confidence > CONFIDENCE_THRESHOLD:
                # 步骤 B: 提取并转换坐标
                center_x = detection[0] * width
                center_y = detection[1] * height
                w = detection[2] * width
                h = detection[3] * height
                
                # 转换为左上角坐标 (x, y)
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)
                w = int(w)
                h = int(h)
                
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)

        # 3. 非极大值抑制 (NMS)
        indices = cv2.dnn.NMSBoxes(boxes, confidences, NMS_THRESHOLD, NMS_THRESHOLD)
        
        # 4. 绘制结果
        result_frame = img_bgr.copy() 
        if len(indices) > 0:
            for i in indices.flatten():
                box = boxes[i]
                x, y, w, h = box
                label = str(self.classes[class_ids[i]]) if class_ids[i] < len(self.classes) else "Unknown"
                confidence = confidences[i]
                
                color = (0, 255, 0) # 绿色 BGR
                cv2.rectangle(result_frame, (x, y), (x + w, y + h), color, 2)
                
                text = f"{label}: {confidence:.2f}"
                text_y = max(y - 10, 30) 
                cv2.putText(result_frame, text, (x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        return result_frame 

    def update_preview(self):
        """
        捕获帧，执行条件检测，并显示（每 N 帧检测）。
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
            self.master.after(100, self.update_preview) 
            return
        
        display_frame_bgr = current_frame_bgr.copy()
        
        # --- 性能分流逻辑 ---
        if self.frame_count % self.detection_interval == 0 and self.net:
            # 执行目标检测（耗时操作）
            start_detection = time.time()
            self.last_detected_frame = self.detect_objects(current_frame_bgr)
            self.detection_time = time.time() - start_detection
            # 确保即使检测失败，也有一个可以复制的帧
            if self.last_detected_frame is not None:
                display_frame_bgr = self.last_detected_frame.copy()
            
        elif self.last_detected_frame is not None:
            # 非检测帧，显示上次带框的帧
            display_frame_bgr = self.last_detected_frame.copy()
        
        # --- 图像显示逻辑 ---
        detected_frame_rgb = cv2.cvtColor(display_frame_bgr, cv2.COLOR_BGR2RGB)
        
        preview_width = self.preview_label.winfo_width()
        preview_height = self.preview_label.winfo_height()
        
        if preview_width > 0 and preview_height > 0:
            image = Image.fromarray(detected_frame_rgb).resize((preview_width, preview_height), Image.LANCZOS)
            self.photo = ImageTk.PhotoImage(image)
            self.preview_label.config(image=self.photo)
        
        # 更新状态标签
        self.fps_label.config(text=f"FPS: {fps:.1f} | 推理: {self.detection_time*1000:.1f}ms (每{self.detection_interval}帧)")
        
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
        sys.exit(1)
