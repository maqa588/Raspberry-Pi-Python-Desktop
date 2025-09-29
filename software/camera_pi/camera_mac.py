import cv2
import time
from ultralytics import YOLO

class CameraApp:
    def __init__(self):
        model_path = "software/camera_pi/models/yolo11n_ncnn_model"

        try:
            print("尝试使用 Metal (MPS) 加速...")
            self.model = YOLO(model_path)
            self.device = "mps"
            # 先跑一个空推理，确保 MPS 可用
            self.model.predict(source=cv2.imread("software/camera_pi/models/test.jpg"), device="mps", verbose=False)
            print("✅ 使用 Metal (MPS) 加速")
        except Exception as e:
            print(f"WARN: Metal 初始化失败 ({e})，回退到 CPU")
            self.model = YOLO(model_path)
            self.device = "cpu"

    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ 无法打开摄像头")
            return

        fps_counter = 0
        start_time = time.time()

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 目标检测
            results = self.model.predict(source=frame, device=self.device, conf=0.4, verbose=False)
            annotated_frame = results[0].plot()

            # 计算 FPS
            fps_counter += 1
            elapsed = time.time() - start_time
            fps = fps_counter / elapsed if elapsed > 0 else 0

            # 显示 FPS
            cv2.putText(annotated_frame, f"FPS: {fps:.2f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # 绘制右上角红色 X 按钮
            h, w, _ = annotated_frame.shape
            btn_size = 30
            x1, y1 = w - btn_size - 10, 10
            x2, y2 = w - 10, 10 + btn_size
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), -1)
            cv2.putText(annotated_frame, "X", (x1 + 7, y1 + 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            cv2.imshow("CameraApp - macOS (Metal/CPU)", annotated_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

            # 检查鼠标点击 X 按钮
            def on_mouse(event, mx, my, flags, param):
                if event == cv2.EVENT_LBUTTONDOWN:
                    if x1 <= mx <= x2 and y1 <= my <= y2:
                        cap.release()
                        cv2.destroyAllWindows()
                        exit(0)

            cv2.setMouseCallback("CameraApp - macOS (Metal/CPU)", on_mouse)

        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    app = CameraApp()
    app.run()
