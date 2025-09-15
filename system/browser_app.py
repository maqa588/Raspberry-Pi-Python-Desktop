# system/browser_app.py
import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QSizePolicy, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QSize
from PyQt5.QtGui import QFont

# 在导入 PyQt5 模块之前，设置环境变量来禁用 GPU 硬件加速
# 强制使用软件（CPU）渲染，并优化触屏和屏幕
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
os.environ["QT_QPA_PLATFORM"] = "eglfs"
os.environ["QT_QPA_EGLFS_PHYSICAL_WIDTH"] = "480"
os.environ["QT_QPA_EGLFS_PHYSICAL_HEIGHT"] = "320"
os.environ["QT_QPA_EGLFS_INTEGRATION"] = "eglfs_brcm"
# 开启触屏支持
os.environ["QT_QPA_GENERIC_TOUCH_INPUT"] = "/dev/input/event0" # 检查你的触屏设备文件路径

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# 确保配置与物理屏幕匹配
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 320

# 定义一个退出信号，便于上级进程识别
EXIT_SIGNAL = "BROWSER_CLOSED_SUCCESSFULLY"

class BrowserWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("桌面浏览器")
        # 直接使用物理屏幕尺寸
        self.resize(QSize(WINDOW_WIDTH, WINDOW_HEIGHT))
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        self.browser = QWebEngineView()
        self.browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.browser.setUrl(QUrl("https://www.winddine.top"))
        
        # 优化触屏交互，增加缩放和拖拽
        self.browser.setZoomFactor(0.8) # 适当缩小页面以适应小屏幕

        self.quit_button = QPushButton("退出")
        # --- 优化退出按钮 ---
        # 1. 调整字体大小，使文字更清晰
        font = QFont()
        font.setPointSize(16) # 设置字体大小为16
        self.quit_button.setFont(font)

        # 2. 设置按钮的最小尺寸，使其更容易触摸
        self.quit_button.setMinimumHeight(50) # 设置最小高度为50像素
        
        # 3. 添加简单的样式，使其更醒目
        self.quit_button.setStyleSheet("background-color: #ff4d4d; color: white; border: none; border-radius: 5px;")
        
        # --- 优化结束 ---
        self.quit_button.clicked.connect(self.on_quit)
        
        layout.addWidget(self.browser)
        layout.addWidget(self.quit_button)
    
    def on_quit(self):
        print(EXIT_SIGNAL)
        self.close()
        QApplication.instance().quit()

def create_browser_window():
    """创建一个 PyQt5 浏览器窗口"""
    app = QApplication(sys.argv)
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    create_browser_window()