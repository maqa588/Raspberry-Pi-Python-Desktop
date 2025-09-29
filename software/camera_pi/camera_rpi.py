import os
import sys
import datetime
import tkinter as tk
from tkinter import messagebox
from picamera2 import Picamera2 # type: ignore
from PIL import Image, ImageTk
import numpy as np
import cv2 # 导入 OpenCV
import time # 用于计时和调试

# --- 路径调整以适应新的 software/camera_pi/ 目录结构 ---
current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)

# 向上追溯三级以找到项目根目录 (project_root -> software -> camera_pi -> camera_rpi.py)
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
# 模型文件路径现在相对于当前脚本所在的目录
YOLO_MODEL_PATH = os.path.join(current_dir, "models", "yolov8n.onnx")
CLASS_NAMES_PATH = os.path.join(current_dir, "models", "coco.names")

CONFIDENCE_THRESHOLD = 0.5
NMS_THRESHOLD = 0.4
INPUT_SIZE = (320, 320) # 使用 320x320 以提高树莓派 Zero 2 W 的推理速度

# --- 相机应用主类 ---
class CameraApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Raspberry Pi Camera with YOLO Detection")
        self.master.geometry("480x320")
        self.master.resizable(False, False)

        # 初始化 Picamera2 实例并配置
        self.picam2 = Picamera2()
        # 预览分辨率使用 Pi Zero 2 W 可以处理的较低分辨率
        self.preview_config = self.picam2.create_preview_configuration(
            main={"size": (640, 480), "format": "RGB888"} # 使用 RGB 格式
        )
        self.picam2.configure(self.preview_config)

        self.preview_label = None
        self.fps_label = None # 用于显示帧率
        self.last_time = time.time()
        
        # YOLO 模型相关属性
        self.net = None
        self.classes = []
        self._load_yolo_model()
        
        self.master.protocol("WM_DELETE_WINDOW", self.confirm_exit)

        self.init_ui()

        # 启动相机预览
        try:
            self.picam2.start()
            self.update_preview()
        except Exception as e:
            messagebox.showerror("相机启动错误", f"无法启动 Picamera2：{e}\n请检查相机模块是否连接并启用。")
            self.master.destroy()

    def _load_yolo_model(self):
        """加载 YOLO 模型和类别名称"""
        try:
            # 1. 加载类别名称
            with open(CLASS_NAMES_PATH, 'r') as f:
                self.classes = [line.strip() for line in f.readlines()]
                
            # 2. 加载 ONNX 模型
            # 注意: ONNX 模型需要 OpenCV 编译时支持 DNN
            self.net = cv2.dnn.readNet(YOLO_MODEL_PATH)
            print(f"YOLO Model loaded from: {YOLO_MODEL_PATH}")
            print(f"Classes loaded: {len(self.classes)}")
            
            # 尝试使用 OpenVINO 或其他优化后端 (如果可用)
            # 在 Pi Zero 2 W 上，可能默认为 CPU (最兼容)
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            
        except FileNotFoundError:
            messagebox.showerror("模型文件缺失", 
                f"YOLOv8 模型文件或类别文件未找到。\n请确保文件位于:\n{YOLO_MODEL_PATH}\n{CLASS_NAMES_PATH}")
            self.net = None # 禁用检测功能
        except Exception as e:
            messagebox.showerror("模型加载失败", f"加载 YOLO 模型时发生错误: {e}")
            self.net = None # 禁用检测功能


    def init_ui(self):
        # ... (顶部栏 UI 保持不变) ...
        top_bar_frame = tk.Frame(self.master, bg="lightgray", height=30)
        top_bar_frame.pack(side=tk.TOP, fill=tk.X)

        file_mb = tk.Menubutton(top_bar_frame, text="文件", activebackground="gray", bg="lightgray")
        file_mb.pack(side=tk.LEFT, padx=5)
        file_menu = tk.Menu(file_mb, tearoff=0)
        file_menu.add_command(label="拍照 (带识别框)", command=self.take_photo)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.confirm_exit)
        file_mb.config(menu=file_menu)

        about_mb = tk.Menubutton(top_bar_frame, text="关于", activebackground="gray", bg="lightgray")
        about_mb.pack(side=tk.LEFT, padx=5)
        about_menu = tk.Menu(about_mb, tearoff=0)
        about_menu.add_command(label="系统信息", command=lambda: show_system_about(self.master))
        about_menu.add_command(label="关于开发者", command=lambda: show_developer_about(self.master))
        about_mb.config(menu=about_menu)

        quit_button = tk.Button(top_bar_frame, text="X", command=self.confirm_exit, relief=tk.FLAT, bg="lightgray", fg="red", padx=5)
        quit_button.pack(side=tk.RIGHT, padx=5)
        # ------------------------------------------------------------------
        
        # 创建主框架来容纳相机预览和按钮
        main_frame = tk.Frame(self.master, bg="grey")
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 左侧相机预览框架
        left_frame = tk.Frame(main_frame, width=387, height=290, bg='black')
        left_frame.pack(side=tk.LEFT, padx=(0, 10), pady=0)
        left_frame.pack_propagate(False)

        # 摄像头预览显示区域
        self.preview_label = tk.Label(left_frame, bg='black')
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        
        # FPS 显示标签
        self.fps_label = tk.Label(left_frame, text="FPS: 0.0", fg="yellow", bg="black", font=('Arial', 8))
        self.fps_label.place(relx=0.02, rely=0.02, anchor="nw")


        # 右侧控制按钮框架
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=0)

        # 按钮布局（竖向放置）
        btn_photo = tk.Button(right_frame, text="拍照 (带识别框)", command=self.take_photo, width=12)
        btn_photo.pack(pady=(5, 5))

        btn_exit = tk.Button(right_frame, text="返回", command=self.confirm_exit, width=12)
        btn_exit.pack(pady=(5, 5))
        
        self.master.update_idletasks()

    def detect_objects(self, frame):
        """
        在给定的图像帧上运行 YOLOv8 推理并绘制结果。
        
        Args:
            frame (np.array): 包含图像数据的 NumPy 数组 (RGB).
        
        Returns:
            np.array: 带有边界框和标签的图像 (BGR).
        """
        if not self.net:
            return frame # 如果模型未加载，直接返回原图

        # YOLO 模型通常期望 BGR 格式
        img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # 1. 创建 Blob
        # Scalefactor 1/255.0，转换为 BGR，不裁剪，图像尺寸 320x320
        blob = cv2.dnn.blobFromImage(img, 1/255.0, INPUT_SIZE, swapRB=False, crop=False)
        
        # 2. 运行推理
        self.net.setInput(blob)
        # 假设 YOLOv8 的 ONNX 输出层名称是 'output0'
        # 如果模型不同，这里可能需要调整
        output_layers_names = self.net.getUnconnectedOutLayersNames() 
        outputs = self.net.forward(output_layers_names)
        
        # 3. 后处理（解析输出）
        height, width, _ = img.shape
        boxes = []
        confidences = []
        class_ids = []

        # YOLOv8 的输出格式是 (batch, dimensions, num_detections)
        # 在 ONNX 中可能是 (1, 84, 8400)，其中 84 是 [x, y, w, h, confidence, class_scores...]
        
        # 迭代所有检测结果
        output = outputs[0].transpose() # 转换成 (num_detections, dimensions)
        
        for detection in output:
            scores = detection[4:] # 类别分数从第 5 个元素开始
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            
            if confidence > CONFIDENCE_THRESHOLD:
                # 坐标是归一化后的中心点 (cx, cy, w, h)
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                
                # 转换为左上角坐标 (x, y, w, h)
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
                label = str(self.classes[class_ids[i]])
                confidence = confidences[i]
                
                # 绘制边界框
                color = (0, 255, 0) # 绿色 BGR
                cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
                
                # 绘制标签
                text = f"{label}: {confidence:.2f}"
                cv2.putText(img, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return img # 返回 BGR 格式的图像

    def update_preview(self):
        """
        捕获相机帧，进行目标检测，并在预览标签中显示。
        """
        # 1. FPS 计时
        current_time = time.time()
        fps = 1.0 / (current_time - self.last_time) if (current_time - self.last_time) > 0 else 0
        self.last_time = current_time
        
        # 2. 捕获帧 (RGB)
        frame = self.picam2.capture_array()
        
        # 3. 目标检测 (返回 BGR 图像)
        detected_frame_bgr = self.detect_objects(frame)

        # 4. BGR -> RGB 用于 PIL
        detected_frame_rgb = cv2.cvtColor(detected_frame_bgr, cv2.COLOR_BGR2RGB)
        
        # 5. 调整大小以适应预览框 (387x290)
        preview_width = 387
        preview_height = 290
        image = Image.fromarray(detected_frame_rgb).resize((preview_width, preview_height))
        
        # 6. 显示
        photo = ImageTk.PhotoImage(image)
        self.preview_label.config(image=photo)
        self.preview_label.image = photo
        
        # 7. 更新 FPS
        self.fps_label.config(text=f"FPS: {fps:.1f}")
        
        # 8. 循环更新
        self.master.after(30, self.update_preview) # 约 33ms/帧

    def take_photo(self):
        """
        拍摄照片，运行检测并保存带识别框的图像。
        为了内存和速度考虑，这里捕获并保存检测后的 640x480 图像，而不是全分辨率 (2592x1944)。
        """
        if not os.path.exists("photos"):
            os.makedirs("photos")
        
        fname = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "_yolo.jpg"
        path = os.path.join("photos", fname)

        # 1. 捕获用于检测的 640x480 帧 (RGB)
        capture_config = self.picam2.create_still_configuration(main={"size": (640, 480), "format": "RGB888"})
        self.picam2.switch_mode(capture_config)
        
        # 等待模式切换
        time.sleep(0.1) 
        
        # 捕获帧
        frame = self.picam2.capture_array()
        
        # 2. 运行目标检测 (返回 BGR 图像)
        detected_frame_bgr = self.detect_objects(frame)

        # 3. 保存图像
        cv2.imwrite(path, detected_frame_bgr)
        
        # 4. 切换回预览模式
        self.picam2.switch_mode(self.preview_config) 
        
        messagebox.showinfo("照片已保存", f"带识别框的照片已保存为: {path} (分辨率: 640x480)")


    def confirm_exit(self):
        """停止相机并退出应用。"""
        if messagebox.askyesno("退出", "你真的要退出吗？"):
            if self.picam2.started:
                try:
                    self.picam2.stop()
                except Exception as e:
                    print(f"Error stopping picamera2: {e}")
            self.master.destroy()

# 如果你在主程序中通过 subprocess 启动这个脚本，
# 确保主程序传递的命令行参数是 "camera_rpi_only"
if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()
