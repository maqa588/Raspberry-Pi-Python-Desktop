import os
import cv2
import time
from ultralytics import YOLO

class CameraApp:
    def __init__(self):
        # 模型路径
        model_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "models",
            "yolo11n_ncnn_model"
        )

        # 尝试加载 NCNN 模型，优先使用 Metal
        try:
            self.model = YOLO(model_path, task="detect", backend="ncnn")
            self.device = "metal"
            print("INFO: 使用 Metal 加速运行 NCNN YOLO 模型")
        except Exception as e:
            print(f"WARN: Metal 初始化失败 ({e})，回退到 CPU")
            self.model = YOLO(model_path, task="detect", backend="ncnn")
            self.device = "cpu"

        # OpenCV 摄像头
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise RuntimeError("无法打开摄像头")

        self.running = True

    def run(self):
        prev_time = time.time()
        frame_count = 0

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                break

            # 推理
            results = self.model.predict(frame, device=self.device, verbose=False)
            annotated_frame = results[0].plot()

            # FPS 计算
            frame_count += 1
            now = time.time()
            fps = frame_count / (now - prev_time)

            cv2.putText(
                annotated_frame,
                f"FPS: {fps:.2f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )

            cv2.imshow("Camera - macOS Metal", annotated_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.stop()

        self.cap.release()
        cv2.destroyAllWindows()

    def stop(self):
        self.running = False


if __name__ == "__main__":
    app = CameraApp()
    app.run()
