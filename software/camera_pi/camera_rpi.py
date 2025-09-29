import os
import sys
import datetime
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import numpy as np
import cv2 # 导入 OpenCV
import time # 用于计时和调试
import platform

# --- 路径调整以适应新的 software/camera_pi/ 目录结构 ---
current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)

# 向上追溯三级以找到项目根目录 (project_root -> software -> camera_pi -> camera_pi.py)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
sys.path.insert(0, project_root)
# --- 路径调整结束 ---

# 假设这些导入在项目中可用
try:
    # 从项目根目录导入 system 模块
    from system.button.about import show_system_about, show_developer_about
except ImportError:
    # 定义占位函数以防导入失败，确保代码能运行
    def show_system_about(root): messagebox.showinfo("系统信息", "此为系统信息占位符。")
    def show_developer_about(root): messagebox.showinfo("开发者信息", "此为开发者信息占位符。")
    print("警告: 未能导入 system.button.about，使用占位函数。")

# --- YOLO 配置和工具 ---
# 沿用 YOLOv5s 模型，因为它与旧版 OpenCV 兼容
YOLO_MODEL_PATH = os.path.join(current_dir, "models", "yolov5s.onnx") 
CLASS_NAMES_PATH = os.path.join(current_dir, "models", "coco.names")

CONFIDENCE_THRESHOLD = 0.5
NMS_THRESHOLD = 0.4
INPUT_SIZE = (640, 640) # YOLOv5s 标准输入

# --- 相机应用主类 (CV2 版本) ---
class CameraApp:
    def __init__(self, master):
        self.master = master
        self.master.title(f"{platform.system()} Camera with YOLO Detection")
        self.master.geometry("480x320")
        self.master.resizable(False, False)

        # 初始化 CV2 摄像头 (增强鲁棒性)
        self.cap = None
        self._initialize_camera() # 调用新的初始化函数
        
        # 检查摄像头是否成功打开
        if not self.cap or not self.cap.isOpened():
            messagebox.showerror("相机错误", "无法访问本机摄像头。请确保摄像头已连接、启用且未被占用。")
            # 尝试销毁窗口时，如果 self.cap 存在则释放它
            if self.cap: self.cap.release()
            self.master.destroy()
            return

        # 尝试设置分辨率
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.preview_label = None
        self.fps_label = None
        self.last_time = time.time()
        self.after_id = None
        
        # YOLO 模型相关属性
        self.net = None
        self.classes = []
        self._load_yolo_model()
        
        self.master.protocol("WM_DELETE_WINDOW", self.confirm_exit)

        self.init_ui()
        self.update_preview()

    def _initialize_camera(self):
        """尝试以多种方式初始化摄像头，以解决 GStreamer 错误。"""
        # 1. 默认尝试 (可能使用 GStreamer，您遇到的问题)
        print("尝试使用默认后端 (Index 0)...")
        self.cap = cv2.VideoCapture(0)
        
        # 2. 如果默认失败，强制使用 V4L2 (推荐用于树莓派)
        if not self.cap.isOpened():
            print("默认后端失败，尝试强制使用 V4L2 后端 (Index 0)...")
            # 释放第一次尝试
            self.cap.release()
            self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
            
        # 3. 如果 V4L2 仍失败，尝试使用 libcamera 后端 (如果您的系统支持)
        if not self.cap.isOpened():
            print("V4L2 后端失败，尝试使用 LIPCAMEARA 后端 (Index 0)...")
            self.cap.release()
            # 注意: cv2.CAP_LIBCAMERA 需要 OpenCV 编译时支持 libcamera，但值得一试
            self.cap = cv2.VideoCapture(0, cv2.CAP_LIBCAMERA)
        
        # 4. 如果所有尝试都失败，返回 None
        if not self.cap.isOpened():
            print("所有摄像头初始化尝试均失败。")
            self.cap = None

    def _load_yolo_model(self):
        """加载 YOLO 模型和类别名称"""
        try:
            with open(CLASS_NAMES_PATH, 'r', encoding='utf-8') as f:
                self.classes = [line.strip() for line in f.readlines()]
            
            self.net = cv2.dnn.readNet(YOLO_MODEL_PATH)
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            print(f"YOLOv5 Model loaded from: {YOLO_MODEL_PATH}")

        except FileNotFoundError:
            messagebox.showerror("模型文件缺失", 
                f"YOLOv5s 模型文件或类别文件未找到。\n请确保文件位于:\n{YOLO_MODEL_PATH}")
            self.net = None
        except Exception as e:
            messagebox.showerror("模型加载失败", f"加载 YOLO 模型时发生错误: {e}")
            self.net = None 

    def init_ui(self):
        """初始化 Tkinter 界面，使用原生菜单栏。"""
        # 1. 创建原生菜单栏
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
        
        # 2. 主内容区域布局
        main_frame = tk.Frame(self.master, bg="grey")
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 左侧：视频预览区域 (固定大小)
        left_frame = tk.Frame(main_frame, width=387, height=290, bg='black')
        left_frame.pack(side=tk.LEFT, padx=(0, 10), pady=0)
        left_frame.pack_propagate(False)

        self.preview_label = tk.Label(left_frame, bg='black')
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        
        # FPS 叠加显示
        self.fps_label = tk.Label(left_frame, text="FPS: 0.0", fg="yellow", bg="black", font=('Arial', 8))
        self.fps_label.place(relx=0.02, rely=0.02, anchor="nw")

        # 右侧：按钮区域
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=0)

        btn_photo = tk.Button(right_frame, text="拍照 (带识别框)", command=self.take_photo, width=12)
        btn_photo.pack(pady=(5, 5))

        btn_exit = tk.Button(right_frame, text="退出", command=self.confirm_exit, width=12)
        btn_exit.pack(pady=(5, 5))
        
        self.master.update_idletasks()

    def detect_objects(self, frame):
        """
        在给定的图像帧上运行 YOLOv5 推理并绘制结果。
        """
        if not self.net:
            return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) 

        img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        height, width, _ = img.shape
        
        # 1. 创建 Blob
        blob = cv2.dnn.blobFromImage(img, 1/255.0, INPUT_SIZE, swapRB=True, crop=False) 
        
        # 2. 运行推理
        self.net.setInput(blob)
        output_layers_names = self.net.getUnconnectedOutLayersNames()
        outputs = self.net.forward(output_layers_names)
        
        # 3. 后处理（解析 YOLOv5/YOLOv8 原始输出）
        boxes = []
        confidences = []
        class_ids = []
        
        for output in outputs:
            for detection in output:
                # 结合目标置信度和类别分数
                scores = detection[5:] 
                class_id = np.argmax(scores)
                confidence = detection[4] * scores[class_id]
                
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
        indices = cv2.dnn.NMSBoxes(boxes, confidences, CONFIDENCE_THRESHOLD, NMS_THRESHOLD)
        
        # 5. 绘制结果
        if len(indices) > 0:
            for i in indices.flatten():
                box = boxes[i]
                x, y, w, h = box
                label = str(self.classes[class_ids[i]]) if class_ids[i] < len(self.classes) else "Unknown"
                confidence = confidences[i]
                
                color = (0, 255, 0) # 绿色 BGR
                cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
                
                text = f"{label}: {confidence:.2f}"
                cv2.putText(img, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return img # 返回 BGR 格式的图像

    def update_preview(self):
        """
        捕获 CV2 帧，进行目标检测，并在预览标签中显示。
        """
        if not self.cap:
             # 如果 cap 为 None，不再尝试读取帧
             self.master.after(1000, self.confirm_exit)
             return
             
        # FPS 计时
        current_time = time.time()
        fps = 1.0 / (current_time - self.last_time) if (current_time - self.last_time) > 0 else 0
        self.last_time = current_time
        
        # 捕获帧 (BGR)
        ret, frame_bgr = self.cap.read()
        
        if not ret:
            # 无法读取帧，停止循环并通知用户
            if self.after_id:
                self.master.after_cancel(self.after_id)
            messagebox.showerror("错误", "无法读取摄像头帧，即将退出。")
            self.master.destroy()
            return

        # BGR -> RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        
        # 目标检测 (返回 BGR 图像)
        detected_frame_bgr = self.detect_objects(frame_rgb)

        # BGR -> RGB 用于 PIL 显示
        detected_frame_rgb = cv2.cvtColor(detected_frame_bgr, cv2.COLOR_BGR2RGB)
        
        # 调整大小以适应预览框 (387x290)
        preview_width = 387
        preview_height = 290
        image = Image.fromarray(detected_frame_rgb).resize((preview_width, preview_height), Image.LANCZOS)
        
        # 显示
        photo = ImageTk.PhotoImage(image)
        self.preview_label.config(image=photo)
        self.preview_label.image = photo 
        
        # 更新 FPS
        self.fps_label.config(text=f"FPS: {fps:.1f}")
        
        # 循环更新
        self.after_id = self.master.after(30, self.update_preview)

    def take_photo(self):
        """
        拍摄照片，运行检测并保存带识别框的图像。
        """
        if not self.cap:
            messagebox.showerror("拍照失败", "摄像头未成功初始化。")
            return
            
        if not os.path.exists("photos"):
            os.makedirs("photos")
        
        fname = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "_yolo.jpg"
        path = os.path.join("photos", fname)

        # 捕获帧
        ret, frame_bgr = self.cap.read()
        if not ret:
            messagebox.showerror("拍照失败", "无法从摄像头捕获图像。")
            return
        
        # 获取实际分辨率
        height, width, _ = frame_bgr.shape
        
        # BGR -> RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        
        # 运行目标检测 (返回 BGR 图像)
        detected_frame_bgr = self.detect_objects(frame_rgb)

        # 保存图像
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
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()
