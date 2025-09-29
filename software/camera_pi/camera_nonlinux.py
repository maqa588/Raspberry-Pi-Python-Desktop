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
# 此处的路径逻辑用于处理模块导入，确保在不同运行环境下能找到 system 模块
current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)

# 向上追溯三级以找到项目根目录
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
# 模型文件路径相对于当前脚本所在的目录
# 假设 models 目录与此脚本在同一目录下
YOLO_MODEL_PATH = os.path.join(current_dir, "models", "yolov8n.onnx")
CLASS_NAMES_PATH = os.path.join(current_dir, "models", "coco.names")

CONFIDENCE_THRESHOLD = 0.5
NMS_THRESHOLD = 0.4
INPUT_SIZE = (320, 320) # 保持一致的推理尺寸

# --- 相机应用主类 (CV2 版本) ---
class CameraApp:
    def __init__(self, master):
        self.master = master
        self.master.title(f"{platform.system()} Camera with YOLO Detection")
        # 保持窗口大小不变
        self.master.geometry("480x320")
        self.master.resizable(False, False)

        # 初始化 CV2 摄像头
        self.cap = cv2.VideoCapture(0) # 尝试默认摄像头 (索引 0)
        
        # 检查摄像头是否打开
        if not self.cap.isOpened():
            messagebox.showerror("相机错误", "无法访问本机摄像头。请确保摄像头已连接且未被占用。")
            self.master.destroy()
            return

        # 尝试设置分辨率 (640x480 是常见的默认捕获/保存分辨率)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.preview_label = None
        self.fps_label = None
        self.last_time = time.time()
        self.after_id = None # 用于管理 tk.after 循环
        
        # YOLO 模型相关属性
        self.net = None
        self.classes = []
        self._load_yolo_model()
        
        self.master.protocol("WM_DELETE_WINDOW", self.confirm_exit)

        self.init_ui()
        self.update_preview()

    def _load_yolo_model(self):
        """加载 YOLO 模型和类别名称 (与 Pi 版本相同)"""
        try:
            with open(CLASS_NAMES_PATH, 'r', encoding='utf-8') as f:
                self.classes = [line.strip() for line in f.readlines()]
            
            # 使用 DNN 读取 ONNX 模型
            self.net = cv2.dnn.readNet(YOLO_MODEL_PATH)
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        except FileNotFoundError:
            messagebox.showerror("模型文件缺失", 
                f"YOLOv8 模型文件或类别文件未找到。\n请确保文件位于:\n{YOLO_MODEL_PATH}\n{CLASS_NAMES_PATH}")
            self.net = None
        except Exception as e:
            messagebox.showerror("模型加载失败", f"加载 YOLO 模型时发生错误: {e}")
            self.net = None 

    def init_ui(self):
        """初始化 Tkinter 界面，使用原生菜单栏。"""
        # 1. 创建原生菜单栏 (Windows/macOS)
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
        # 由于使用了原生菜单栏，移除顶部 bar_frame
        main_frame = tk.Frame(self.master, bg="grey")
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 左侧：视频预览区域 (固定大小，与 Pi 版本一致)
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

        # 将 "返回" 按钮改为 "退出" 按钮，功能保持一致
        btn_exit = tk.Button(right_frame, text="退出", command=self.confirm_exit, width=12)
        btn_exit.pack(pady=(5, 5))
        
        self.master.update_idletasks()

    def detect_objects(self, frame):
        """
        在给定的图像帧上运行 YOLOv8 推理并绘制结果 (与 Pi 版本相同)。
        
        Args:
            frame (np.array): 包含图像数据的 NumPy 数组 (RGB).
        
        Returns:
            np.array: 带有边界框和标签的图像 (BGR).
        """
        if not self.net:
            # 如果模型未加载，直接返回转换回 BGR 的原图
            return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) 

        img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # 1. 创建 Blob
        # 使用 320x320 作为推理尺寸，与 Pi 版本保持一致
        blob = cv2.dnn.blobFromImage(img, 1/255.0, INPUT_SIZE, swapRB=False, crop=False)
        
        # 2. 运行推理
        self.net.setInput(blob)
        # 确保获取输出层名称
        layer_names = self.net.getLayerNames()
        output_layers_names = [layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
        
        outputs = self.net.forward(output_layers_names)
        
        # 3. 后处理（解析输出）
        height, width, _ = img.shape
        boxes = []
        confidences = []
        class_ids = []

        # YOLOv8 模型的输出通常是 (batch_size, num_detections, 4+num_classes)
        # 这里处理第一个输出 (通常是检测结果)
        # outputs[0].shape: (1, 84, N) -> 转置为 (N, 84)
        output = outputs[0].transpose()
        
        for detection in output:
            # 前四个元素是中心x, 中心y, 宽度, 高度
            # 之后的元素是置信度分数 (对于 YOLOv8, 是 [score, class_scores...])
            
            # YOLOv8 的输出格式通常是 [cx, cy, w, h, class_1_score, class_2_score, ...]
            # 需要找到最高分数和对应的类别ID
            scores = detection[4:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            
            if confidence > CONFIDENCE_THRESHOLD:
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                
                # 计算左上角坐标
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
        # 1. FPS 计时
        current_time = time.time()
        fps = 1.0 / (current_time - self.last_time) if (current_time - self.last_time) > 0 else 0
        self.last_time = current_time
        
        # 2. 捕获帧 (BGR)
        ret, frame_bgr = self.cap.read()
        
        if not ret:
            # 无法读取帧，停止循环并通知用户
            if self.after_id:
                self.master.after_cancel(self.after_id)
            messagebox.showerror("错误", "无法读取摄像头帧，即将退出。")
            self.master.destroy()
            return

        # 3. BGR -> RGB，用于 detect_objects (内部会转回 BGR)
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        
        # 4. 目标检测 (返回 BGR 图像)
        detected_frame_bgr = self.detect_objects(frame_rgb)

        # 5. BGR -> RGB 用于 PIL 显示
        detected_frame_rgb = cv2.cvtColor(detected_frame_bgr, cv2.COLOR_BGR2RGB)
        
        # 6. 调整大小以适应预览框 (387x290)
        preview_width = 387
        preview_height = 290
        image = Image.fromarray(detected_frame_rgb).resize((preview_width, preview_height), Image.LANCZOS)
        
        # 7. 显示
        photo = ImageTk.PhotoImage(image)
        self.preview_label.config(image=photo)
        self.preview_label.image = photo # 保持引用
        
        # 8. 更新 FPS
        self.fps_label.config(text=f"FPS: {fps:.1f}")
        
        # 9. 循环更新
        self.after_id = self.master.after(30, self.update_preview)

    def take_photo(self):
        """
        拍摄照片，运行检测并保存带识别框的图像。
        保存分辨率为摄像头实际捕获的分辨率。
        """
        if not os.path.exists("photos"):
            os.makedirs("photos")
        
        fname = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "_yolo.jpg"
        path = os.path.join("photos", fname)

        # 1. 捕获帧
        ret, frame_bgr = self.cap.read()
        if not ret:
            messagebox.showerror("拍照失败", "无法从摄像头捕获图像。")
            return
        
        # 获取实际分辨率
        height, width, _ = frame_bgr.shape
        
        # 2. BGR -> RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        
        # 3. 运行目标检测 (返回 BGR 图像)
        detected_frame_bgr = self.detect_objects(frame_rgb)

        # 4. 保存图像
        cv2.imwrite(path, detected_frame_bgr)
        
        messagebox.showinfo("照片已保存", f"带识别框的照片已保存为: {path} (分辨率: {width}x{height})")


    def confirm_exit(self):
        """释放摄像头并退出应用。"""
        if messagebox.askyesno("退出", "你真的要退出吗？"):
            if self.cap.isOpened():
                self.cap.release()
            
            # 取消 tk.after 循环
            if self.after_id:
                self.master.after_cancel(self.after_id)
                
            self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()
