# system/browser_app.py
import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QSizePolicy, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QSize

# 在导入 PyQt5 模块之前，设置环境变量来禁用 GPU 硬件加速
# 强制使用软件（CPU）渲染
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
os.environ["QT_QPA_PLATFORM"] = "eglfs"
os.environ["QT_QPA_EGLFS_PHYSICAL_WIDTH"] = "480"
os.environ["QT_QPA_EGLFS_PHYSICAL_HEIGHT"] = "320"
os.environ["QT_QPA_EGLFS_INTEGRATION"] = "eglfs_brcm" # 或者其他适用于你的树莓派型号的集成方式

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from system.config import WINDOW_WIDTH, WINDOW_HEIGHT

# 定义一个退出信号，便于上级进程识别
EXIT_SIGNAL = "BROWSER_CLOSED_SUCCESSFULLY"

class BrowserWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("桌面浏览器")
        self.resize(QSize(WINDOW_WIDTH, (WINDOW_HEIGHT + 10)))
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        self.browser = QWebEngineView()
        self.browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.browser.setUrl(QUrl("https://www.winddine.top"))
        
        self.quit_button = QPushButton("退出")
        self.quit_button.clicked.connect(self.on_quit)
        
        layout.addWidget(self.browser)
        layout.addWidget(self.quit_button)
    
    def on_quit(self):
        # 打印退出信号到标准输出，然后关闭应用程序
        print(EXIT_SIGNAL)
        self.close()
        # 强制退出，以确保信号被立即发送
        QApplication.instance().quit()

def create_browser_window():
    """创建一个 PyQt5 浏览器窗口"""
    app = QApplication(sys.argv)
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    create_browser_window()