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
    
class CameraAppRpiTorchScript:
    def __init__(self):
        # --- 1. PyTorch 模型配置 (本地加载) ---
        self.MODEL_PATH = "software/camera_pi/models/yolov5n.torchscript" 
        self.NAMES_PATH = "software/camera_pi/models/coco.names" 
        self.CONFIDENCE_THRESHOLD = 0.4
        
        print("⚙️ 初始化 TorchScript 模型...")
        self.model = None
        # 模型输入尺寸必须与导出时的尺寸一致，这里仍然假定是 320x320
        self.input_width = 320 
        self.input_height = 320 
        
        # 尝试从本地文件加载类别标签
        self.CLASSES = self._load_classes()

        if torch:
            try:
                if not os.path.exists(self.MODEL_PATH):
                     raise FileNotFoundError(f"模型文件未找到: {self.MODEL_PATH}。\n请注意，为解决依赖问题，需要使用 .torchscript 格式的模型。")

                # 加载 TorchScript 模型: torch.jit.load()
                self.model = torch.jit.load(self.MODEL_PATH, map_location=torch.device('cpu'))
                self.model.eval()  # 设置为评估模式
                print(f"✅ TorchScript 模型 ({self.MODEL_PATH}) 从本地加载成功。")
                        
            except Exception as e:
                print(f"⚠️ 无法从本地加载 TorchScript 模型 {self.MODEL_PATH}。请确认文件路径正确且已转换为 TorchScript 格式。")
                print(f"原始错误: {e}")
                self.model = None 

        # --- 2. 摄像头和 UI 配置 ---
        self.picam2 = Picamera2()
        # 摄像头分辨率 480x320，显式指定格式为 RGB888 (3通道) 以避免 4 通道错误
        config = self.picam2.create_preview_configuration(main={"size": (480, 320), "format": "RGB888"})
        self.picam2.configure(config)
        self.picam2.start()

        # UI 参数
        self.button_size = 40
        self.button_margin = 10
        self.window_name = "CameraApp - PyTorch RPi (TorchScript)"
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
            
            # ⚠️ 安全检查: 如果 picamera2 仍输出 4 通道 (e.g., XBGR8888)，则强制转换为 RGB。
            if frame.shape[2] == 4:
                # 假设 picamera2 的 4 通道输出是 RGBA/RGBX
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB) 
            
            # 将 RGB (3通道) 转换为 BGR 用于 OpenCV 绘制 (这是显示器的标准颜色空间)
            annotated_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            self.frame_height, self.frame_width, _ = annotated_frame.shape

            # --- 核心 PyTorch 推理逻辑 ---
            if self.model:
                # 1. 手动预处理：TorchScript 模型不接受 'size' 参数，必须手动缩放和转换。
                
                # 调整大小：从 480x320 缩放到模型需要的 320x320
                img_resized = cv2.resize(frame, (self.input_width, self.input_height), interpolation=cv2.INTER_LINEAR)
                
                # 转换为 Tensor，并移动到 CPU
                img_tensor = torch.from_numpy(img_resized).to('cpu').float()
                
                # 归一化 (0-255 -> 0.0-1.0) 和 维度调整 (HWC -> CHW -> BCHW)
                # 结果形状应为 (1, 3, 320, 320)
                input_tensor = img_tensor.permute(2, 0, 1).unsqueeze(0) / 255.0

                # 2. 推理：现在只传入一个张量，解决 forward() 参数过多的错误
                # results_tensor 应该是一个 [1, N, 6] 格式的张量
                results_tensor = self.model(input_tensor)
                
                # 3. 后处理：假设模型的输出是经过 NMS 后的 [N, 6] 格式：
                # [x1, y1, x2, y2, confidence, class_id] 且坐标是相对于 320x320 输入的。
                
                # 处理模型输出可能是一个元组的情况
                if isinstance(results_tensor, tuple):
                    results_tensor = results_tensor[0]
                    
                # 确保张量是 [N, 6] 格式，并转为 numpy
                # 检查输出是否为空，如果为空，则跳过
                if results_tensor.ndim > 1:
                    detections = results_tensor.squeeze(0).cpu().numpy() 
                else:
                    detections = np.empty((0, 6))

                # 计算缩放因子，用于将 320x320 的坐标映射回 480x320 的原始画面
                scale_x = self.frame_width / self.input_width  # 480 / 320 = 1.5
                scale_y = self.frame_height / self.input_height # 320 / 320 = 1.0

                # 4. 遍历检测结果并绘制
                for detection in detections:
                    # 检查置信度
                    confidence = detection[4]
                    if confidence > self.CONFIDENCE_THRESHOLD:
                        
                        # 提取边界框和类别
                        x1, y1, x2, y2 = detection[:4].astype(int)
                        class_id = int(detection[5])
                        
                        # 坐标缩放回原始画面尺寸 (480x320)
                        x1_scaled = int(x1 * scale_x)
                        y1_scaled = int(y1 * scale_y)
                        x2_scaled = int(x2 * scale_x)
                        y2_scaled = int(y2 * scale_y)
                        
                        if class_id < len(self.CLASSES):
                            label = f"{self.CLASSES[class_id]}: {confidence:.2f}"
                            # 使用 class_id 模运算确保颜色索引不越界
                            color = self.COLORS[class_id % len(self.COLORS)] 

                            # 绘制边界框
                            cv2.rectangle(annotated_frame, (x1_scaled, y1_scaled), (x2_scaled, y2_scaled), color, 2)
                            
                            # 绘制标签背景和文字
                            y_pos = y1_scaled - 15 if y1_scaled - 15 > 15 else y1_scaled + 15
                            cv2.putText(annotated_frame, label, (x1_scaled, y_pos),
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
        app = CameraAppRpiTorchScript()
        app.run()
    except Exception as e:
        print(f"发生错误: {e}")
        print("请确保 'picamera2', 'opencv-python' 和 PyTorch CPU 版本已正确安装。")
