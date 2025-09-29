import cv2
import time
from ultralytics import YOLO
import os

class CameraApp:
    def __init__(self, mode=None):
        self.mode = mode
        self.should_exit = False  # 循环退出标志
        self.btn_size = 30
        self.btn_margin = 10
        self.window_name = "CameraApp - macOS (PyTorch MPS)"

        # 模型路径：PyTorch .pt 模型
        model_path = "software/camera_pi/models/yolo11n.pt"
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"PyTorch 模型未找到: {model_path}")

        # 尝试 MPS 加速
        try:
            print("⚙️ 尝试使用 PyTorch MPS 加速...")
            self.device = "mps"
            self.model = YOLO(model_path)
            print("✅ 使用 MPS 加速")
        except Exception as e:
            print(f"⚠️ MPS 初始化失败 ({e})，回退 CPU")
            self.device = "cpu"
            self.model = YOLO(model_path)

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            h, w, _ = param.shape
            x1 = w - self.btn_size - self.btn_margin
            y1 = self.btn_margin
            x2 = w - self.btn_margin
            y2 = self.btn_margin + self.btn_size
            if x1 <= x <= x2 and y1 <= y <= y2:
                print("❌ X按钮点击，退出程序")
                self.should_exit = True

    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ 无法打开摄像头")
            return

        cv2.namedWindow(self.window_name)
        fps_counter = 0
        start_time = time.time()

        while True:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ 摄像头读取失败")
                break

            # YOLO 推理
            results = self.model.predict(source=frame, device=self.device, conf=0.4, verbose=False)
            annotated_frame = results[0].plot()

            # FPS 显示
            fps_counter += 1
            elapsed = time.time() - start_time
            fps = fps_counter / elapsed if elapsed > 0 else 0
            cv2.putText(annotated_frame, f"FPS: {fps:.2f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # 绘制右上角 X 按钮
            h, w, _ = annotated_frame.shape
            x1 = w - self.btn_size - self.btn_margin
            y1 = self.btn_margin
            x2 = w - self.btn_margin
            y2 = self.btn_margin + self.btn_size
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), -1)
            cv2.putText(annotated_frame, "X", (x1 + 7, y1 + 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            # 鼠标回调
            cv2.setMouseCallback(self.window_name, self.mouse_callback, annotated_frame)
            cv2.imshow(self.window_name, annotated_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or self.should_exit:
                break

        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    app = CameraApp()
    app.run()
