# software/camera_pc/camera_pc.py
import time
import cv2
from ultralytics import YOLO

class CameraAppPC:
    def __init__(self, mode=None):
        self.mode = mode
        model_path = "software/camera_pi/models/yolo11n_ncnn_model"

        # 尝试使用 GPU
        try:
            print("⚙️ 尝试使用 GPU 加速...")
            self.device = "cuda"  # ultralytics 支持 "cuda" 或 "cpu"
            self.model = YOLO(model_path)
            # 测试一次推理，确认 GPU 可用
            _ = self.model.predict(source=cv2.imread("test.jpg"), device=self.device, verbose=False)
            print("✅ GPU 可用，使用 GPU 加速推理")
        except Exception:
            print("⚠️ GPU 不可用，回退到 CPU")
            self.device = "cpu"
            self.model = YOLO(model_path)

        # 打开默认摄像头
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise RuntimeError("无法打开摄像头")

        # X按钮参数
        self.button_size = 40
        self.button_margin = 10
        self.window_name = "CameraApp - Windows"
        self.should_exit = False

        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            h, w = param.shape[:2]
            x0 = w - self.button_size - self.button_margin
            y0 = self.button_margin
            x1 = w - self.button_margin
            y1 = self.button_margin + self.button_size
            if x0 <= x <= x1 and y0 <= y <= y1:
                print("❌ X按钮被点击，退出程序...")
                self.should_exit = True

    def run(self):
        fps_counter = 0
        start_time = time.time()

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("⚠️ 读取摄像头失败")
                break

            # YOLO 推理
            results = self.model.predict(source=frame, device=self.device, conf=0.4, verbose=False)
            annotated_frame = results[0].plot()

            # 添加 FPS
            fps_counter += 1
            elapsed = time.time() - start_time
            fps = fps_counter / elapsed if elapsed > 0 else 0
            cv2.putText(annotated_frame, f"FPS: {fps:.2f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # 绘制右上角 X 按钮
            h, w = annotated_frame.shape[:2]
            x0 = w - self.button_size - self.button_margin
            y0 = self.button_margin
            x1 = w - self.button_margin
            y1 = self.button_margin + self.button_size
            cv2.rectangle(annotated_frame, (x0, y0), (x1, y1), (0, 0, 255), -1)
            cv2.putText(annotated_frame, "X", (x0 + 10, y0 + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            cv2.imshow(self.window_name, annotated_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or self.should_exit:
                break

        self.cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    app = CameraAppPC()
    app.run()
