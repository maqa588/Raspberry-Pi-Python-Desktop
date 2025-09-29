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
        self.window_name = "CameraApp - PyTorch RPi (TorchScript)"
        self.should_exit = False
        self.frame_width = 480
        self.frame_height = 320
        
        # 恢复自定义 X 按钮参数
        self.button_size = 40
        self.button_margin = 10
        
        # 随机生成颜色用于绘制边界框 (用于类别区分)
        np.random.seed(42)
        # 确保颜色列表长度足够
        # 注意: OpenCV 使用 BGR 格式，所以这里生成的颜色是 BGR 顺序
        self.COLORS = np.random.uniform(0, 255, size=(max(80, len(self.CLASSES)), 3)).astype(int)
    
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
        
    # 恢复 mouse_callback 方法
    def mouse_callback(self, event, x, y, flags, param):
        """OpenCV 鼠标事件回调函数，用于检测 X 按钮点击。"""
        if event == cv2.EVENT_LBUTTONDOWN:
            # 按钮区域检查，使用当前帧尺寸
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
        
        # 修复画面变小问题：移除 WINDOW_NORMAL 标志，让窗口默认以图像尺寸显示
        cv2.namedWindow(self.window_name) 
        # 恢复鼠标回调
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
            
            # 记录原始帧尺寸
            original_h, original_w, _ = annotated_frame.shape
            self.frame_height, self.frame_width = original_h, original_w # 更新 UI 尺寸

            # --- 核心 PyTorch 推理逻辑 ---
            if self.model:
                # 1. Letterbox 预处理和缩放计算
                
                # Letterbox 缩放比例
                r_w = self.input_width / original_w
                r_h = self.input_height / original_h
                r = min(r_w, r_h) 
                
                new_unpad_w = int(round(original_w * r))
                new_unpad_h = int(round(original_h * r))
                
                # 计算总填充量
                dw = self.input_width - new_unpad_w
                dh = self.input_height - new_unpad_h
                
                # 确定对称填充的左右和上下边距 (必须是整数)
                pad_left = int(dw / 2) # 左侧填充
                pad_top = int(dh / 2)  # 顶部填充
                pad_right = dw - pad_left # 右侧填充
                pad_bottom = dh - pad_top # 底部填充

                # 调整大小：缩放到 new_unpad_w x new_unpad_h
                img_resized = cv2.resize(frame, (new_unpad_w, new_unpad_h), interpolation=cv2.INTER_LINEAR)

                # Letterbox 填充：填充到 320x320
                img_padded = cv2.copyMakeBorder(img_resized, pad_top, pad_bottom, pad_left, pad_right, cv2.BORDER_CONSTANT, value=(114, 114, 114))

                # 转换为 Tensor，并移动到 CPU
                img_tensor = torch.from_numpy(img_padded).to('cpu').float()
                
                # 归一化 (0-255 -> 0.0-1.0) 和 维度调整 (HWC -> CHW -> BCHW)
                input_tensor = img_tensor.permute(2, 0, 1).unsqueeze(0) / 255.0

                # 2. 推理
                results_tensor = self.model(input_tensor)
                
                # 3. 后处理
                if isinstance(results_tensor, tuple):
                    results_tensor = results_tensor[0]
                    
                if results_tensor.ndim > 1:
                    detections = results_tensor.squeeze(0).cpu().numpy() 
                else:
                    detections = np.empty((0, 6))

                # 4. 遍历检测结果并绘制
                for detection in detections:
                    confidence = detection[4]
                    if confidence > self.CONFIDENCE_THRESHOLD:
                        
                        # 提取边界框和类别 (相对于 320x320 Letterbox 图像)
                        x1, y1, x2, y2 = detection[:4].astype(int)
                        class_id = int(detection[5])
                        
                        # --- 5. 边界框坐标校正 (Letterbox 反向操作) ---
                        
                        # 移除填充 (减去左侧和顶部的填充量)
                        x1 = x1 - pad_left
                        y1 = y1 - pad_top
                        x2 = x2 - pad_left
                        y2 = y2 - pad_top
                        
                        # 反向缩放回原始尺寸 (480x320)
                        x1_scaled = int(np.clip(x1 / r, 0, original_w))
                        y1_scaled = int(np.clip(y1 / r, 0, original_h))
                        x2_scaled = int(np.clip(x2 / r, 0, original_w))
                        y2_scaled = int(np.clip(y2 / r, 0, original_h))
                        
                        # --- 6. 绘制 (多色) ---
                        
                        if class_id < len(self.CLASSES):
                            label = f"{self.CLASSES[class_id]}: {confidence:.2f}"
                            # 根据类别 ID 获取不同的颜色 (多色实现)
                            color_bgr = self.COLORS[class_id % len(self.COLORS)].tolist() 

                            # 绘制边界框
                            cv2.rectangle(annotated_frame, (x1_scaled, y1_scaled), (x2_scaled, y2_scaled), color_bgr, 2)
                            
                            # 绘制标签背景和文字
                            y_pos = y1_scaled - 15 if y1_scaled - 15 > 15 else y1_scaled + 15
                            cv2.putText(annotated_frame, label, (x1_scaled, y_pos),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_bgr, 2)
                        
            # --- 颜色深度适配 (针对 16 位屏幕 R5G6B5) ---
            # 适配 16 位显示器，通过比例缩放和四舍五入实现更自然的 16 位颜色量化。
            
            # B 通道 (5 位, 31 级): V_new = round(V_8bit * 31 / 255) * 255 / 31
            B_quantized = np.round(annotated_frame[:, :, 0] * 31.0 / 255.0)
            annotated_frame[:, :, 0] = np.round(B_quantized * 255.0 / 31.0).astype(np.uint8)
            
            # G 通道 (6 位, 63 级): V_new = round(V_8bit * 63 / 255) * 255 / 63
            G_quantized = np.round(annotated_frame[:, :, 1] * 63.0 / 255.0)
            annotated_frame[:, :, 1] = np.round(G_quantized * 255.0 / 63.0).astype(np.uint8)
            
            # R 通道 (5 位, 31 级): V_new = round(V_8bit * 31 / 255) * 255 / 31
            R_quantized = np.round(annotated_frame[:, :, 2] * 31.0 / 255.0)
            annotated_frame[:, :, 2] = np.round(R_quantized * 255.0 / 31.0).astype(np.uint8)
            
            # --- UI 绘制 (FPS 和 X 按钮) ---
            
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
            # 现在可以通过 'q' 键或点击自定义 X 按钮退出
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
