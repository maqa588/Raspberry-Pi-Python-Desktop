import time
import cv2
import numpy as np
from picamera2 import Picamera2
import os

# ⚠️ PyTorch 依赖警告:
# 此代码需要安装 PyTorch 的 CPU 版本，通常使用 pip3 install torch torchvision numpy。
try:
    import torch
    # 强制禁用梯度计算，确保只在推理模式下运行
    torch.no_grad().__enter__()
except ImportError:
    print("⚠️ 无法导入 PyTorch 库。请确保已安装 PyTorch CPU 版本 (pip3 install torch)。")
    torch = None
    
class CameraAppRpiPyTorch:
    def __init__(self):
        # --- 1. PyTorch 模型配置 (本地加载) ---
        self.MODEL_PATH = "software/camera_pi/models/yolov5n.pt" # 指定本地模型路径
        self.NAMES_PATH = "software/camera_pi/models/coco.names" # 指定本地类别文件路径
        self.CONFIDENCE_THRESHOLD = 0.4
        
        print("⚙️ 初始化 PyTorch 模型...")
        self.model = None
        self.input_width = 320 
        self.input_height = 320 
        
        # 尝试从本地文件加载类别标签
        self.CLASSES = self._load_classes()

        if torch:
            try:
                # 警告: 使用 torch.load 加载 YOLOv5 .pt 文件要求本地安装有 
                # 足够的信息来重建模型结构 (通常需要 ultralytics 包环境支持)。
                # 假设 yolov5n.pt 是一个包含完整模型结构和权重的 PyTorch Checkpoint
                
                if not os.path.exists(self.MODEL_PATH):
                     raise FileNotFoundError(f"模型文件未找到: {self.MODEL_PATH}")

                # 加载 PyTorch 模型Checkpoint，映射到 CPU
                checkpoint = torch.load(self.MODEL_PATH, map_location=torch.device('cpu'))
                
                # 尝试从 checkpoint 中提取模型对象
                # 注意: 这里的 'model' 键是 YOLOv5 checkpoint 的标准结构
                if 'model' in checkpoint:
                    self.model = checkpoint['model'].float()
                    self.model.eval()  # 设置为评估模式
                    self.model.to('cpu')
                    print(f"✅ PyTorch 模型 ({self.MODEL_PATH}) 从本地加载成功。")
                    
                    # 尝试更新类别标签（如果模型Checkpoint中包含更准确的names）
                    if 'names' in checkpoint and len(checkpoint['names']) > 0:
                        self.CLASSES = checkpoint['names']
                        
                else:
                    raise ValueError("加载的模型文件不包含预期的'model'结构。")

            except Exception as e:
                print(f"⚠️ 无法从本地加载 PyTorch 模型 {self.MODEL_PATH}。请确认文件路径正确且格式兼容。")
                print(f"原始错误: {e}")
                self.model = None 

        # --- 2. 摄像头和 UI 配置 ---
        self.picam2 = Picamera2()
        # 摄像头分辨率 480x320
        config = self.picam2.create_preview_configuration(main={"size": (480, 320)})
        self.picam2.configure(config)
        self.picam2.start()

        # UI 参数
        self.button_size = 40
        self.button_margin = 10
        self.window_name = "CameraApp - PyTorch RPi (Local)"
        self.should_exit = False
        self.frame_width = 480
        self.frame_height = 320
        
        # 随机生成颜色用于绘制边界框
        np.random.seed(42)
        # 确保颜色列表长度足够
        self.COLORS = np.random.uniform(0, 255, size=(max(80, len(self.CLASSES)), 3))
    
    def _load_classes(self):
        """从本地文件加载类别标签"""
        try:
            with open(self.NAMES_PATH, 'r') as f:
                classes = [line.strip() for line in f.readlines()]
            print(f"✅ 类别标签从本地文件 {self.NAMES_PATH} 加载成功。")
            return classes
        except FileNotFoundError:
            print(f"⚠️ 类别文件未找到: {self.NAMES_PATH}。使用默认标签。")
            return ["person", "object"]
        
    def mouse_callback(self, event, x, y, flags, param):
        """OpenCV 鼠标事件回调函数，用于检测 X 按钮点击。"""
        if event == cv2.EVENT_LBUTTONDOWN:
            x0 = self.frame_width - self.button_size - self.button_margin
            y0 = self.button_margin
            x1 = self.frame_width - self.button_margin
            y1 = self.button_margin + self.button_size
            
            if (x >= x0 and x <= x1 and y >= y0 and y <= y1):
                print("❌ X按钮被点击，退出程序...")
                self.should_exit = True

    def run(self):
        """主循环，用于捕获、推理和显示视频帧。"""
        print("▶️ 启动摄像头预览和 PyTorch 本地推理...")
        fps_counter = 0
        start_time = time.time()
        
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback, None) 

        while True:
            # 获取一帧图像 (RGB numpy array)
            frame = self.picam2.capture_array()
            # 将 RGB 转换为 BGR 用于 OpenCV 绘制
            annotated_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            self.frame_height, self.frame_width, _ = annotated_frame.shape

            # --- 核心 PyTorch 推理逻辑 ---
            if self.model:
                # 1. 推理：直接将 numpy 图像传入模型
                # model() 内部会处理 RGB/BGR 转换、缩放和归一化
                results = self.model(frame, size=self.input_width)
                
                # 2. 后处理：使用 results.pred 获取原始检测结果 (张量)
                # results.pred 包含 NMS 后的结果，格式通常是 [x1, y1, x2, y2, confidence, class_id]
                detections = results.pred[0].cpu().numpy()
                
                # 3. 遍历检测结果并绘制
                for detection in detections:
                    # 检查置信度
                    confidence = detection[4]
                    if confidence > self.CONFIDENCE_THRESHOLD:
                        
                        # 提取边界框和类别
                        x1, y1, x2, y2 = detection[:4].astype(int)
                        class_id = int(detection[5])
                        
                        # 由于 YOLOv5 模型的输出坐标已根据输入尺寸 (self.input_width) 缩放回原图尺寸 (frame_width/height), 
                        # 我们可以直接使用这些坐标进行绘制。

                        if class_id < len(self.CLASSES):
                            label = f"{self.CLASSES[class_id]}: {confidence:.2f}"
                            # 使用 class_id 模运算确保颜色索引不越界
                            color = self.COLORS[class_id % len(self.COLORS)] 

                            # 绘制边界框
                            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                            
                            # 绘制标签背景和文字
                            y_pos = y1 - 15 if y1 - 15 > 15 else y1 + 15
                            cv2.putText(annotated_frame, label, (x1, y_pos),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                        
            # --- UI 绘制 (FPS & 退出按钮) ---
            
            # FPS 计算
            fps_counter += 1
            elapsed = time.time() - start_time
            fps = fps_counter / elapsed if elapsed > 0 else 0
            
            if elapsed >= 1.0:
                fps_counter = 0
                start_time = time.time()
                
            cv2.putText(annotated_frame, f"FPS: {fps:.2f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # 绘制右上角 X 按钮
            x0 = self.frame_width - self.button_size - self.button_margin
            y0 = self.button_margin
            x1 = self.frame_width - self.button_margin
            y1 = self.button_margin + self.button_size
            
            cv2.rectangle(annotated_frame, (x0, y0), (x1, y1), (0, 0, 255), -1) 
            cv2.putText(annotated_frame, "X", (x0 + 10, y0 + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            # 显示画面
            cv2.imshow(self.window_name, annotated_frame)

            # 检查退出条件
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or self.should_exit:
                print("程序退出中...")
                break

        # 清理资源
        self.picam2.stop()
        cv2.destroyAllWindows()
        print("✅ 摄像头和窗口已关闭。")

if __name__ == "__main__":
    try:
        app = CameraAppRpiPyTorch()
        app.run()
    except Exception as e:
        print(f"发生错误: {e}")
        print("请确保 'picamera2', 'opencv-python' 和 PyTorch CPU 版本已正确安装。")
