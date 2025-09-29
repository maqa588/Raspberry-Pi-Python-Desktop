# software/camera_pi/camera_rpi.py
import time
import cv2
from picamera2 import Picamera2
from ultralytics import YOLO

class CameraAppRpi:
    def __init__(self, mode=None):
        self.mode = mode
        model_path = "software/camera_pi/models/yolo11n_ncnn_model"

        print("⚙️ 初始化 YOLO 模型 (CPU)...")
        self.model = YOLO(model_path)
        self.device = "cpu"

        # 初始化摄像头，设置分辨率为 480x320
        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(main={"size": (480, 320)})
        self.picam2.configure(config)
        self.picam2.start()

        # X按钮参数
        self.button_size = 40
        self.button_margin = 10
        self.window_name = "CameraApp - Raspberry Pi (CPU)"
        self.should_exit = False

    def mouse_callback(self, event, x, y, flags, param):
        # 检测是否点击到右上角 X 区域
        if event == cv2.EVENT_LBUTTONDOWN:
            w, h = self.button_size, self.button_size
            if (x >= param.shape[1] - w - self.button_margin and
                x <= param.shape[1] - self.button_margin and
                y >= self.button_margin and
                y <= self.button_margin + h):
                print("❌ X按钮被点击，退出程序...")
                self.should_exit = True

    def run(self):
        fps_counter = 0
        start_time = time.time()
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        while True:
            # 获取一帧图像
            frame = self.picam2.capture_array()

            # YOLO 推理 (CPU)
            results = self.model.predict(source=frame, device=self.device, conf=0.4, verbose=False)
            annotated_frame = results[0].plot()

            # 添加 FPS
            fps_counter += 1
            elapsed = time.time() - start_time
            fps = fps_counter / elapsed if elapsed > 0 else 0
            cv2.putText(annotated_frame, f"FPS: {fps:.2f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # 绘制右上角 X 按钮
            x0 = annotated_frame.shape[1] - self.button_size - self.button_margin
            y0 = self.button_margin
            x1 = annotated_frame.shape[1] - self.button_margin
            y1 = self.button_margin + self.button_size
            cv2.rectangle(annotated_frame, (x0, y0), (x1, y1), (0, 0, 255), -1)
            cv2.putText(annotated_frame, "X", (x0 + 10, y0 + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            # 显示画面
            cv2.imshow(self.window_name, annotated_frame)

            # 检查退出条件
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or self.should_exit:
                break

        self.picam2.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    app = CameraAppRpi()
    app.run()
