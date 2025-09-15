# system/browser_app.py
import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QSizePolicy, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QSize
from PyQt5.QtGui import QFont

# 根据操作系统类型来设置环境变量
# 这可以防止在 macOS 或 Windows 上运行时因环境变量不兼容而崩溃
if sys.platform.startswith('linux') and os.path.exists('/dev/input/event0'):
    print("在Linux（树莓派）上运行，启用嵌入式模式...")
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
    os.environ["QT_QPA_PLATFORM"] = "eglfs"
    os.environ["QT_QPA_EGLFS_PHYSICAL_WIDTH"] = "480"
    os.environ["QT_QPA_EGLFS_PHYSICAL_HEIGHT"] = "320"
    os.environ["QT_QPA_EGLFS_INTEGRATION"] = "eglfs_brcm"
    os.environ["QT_QPA_GENERIC_TOUCH_INPUT"] = "/dev/input/event0"
    WINDOW_WIDTH = 480
    WINDOW_HEIGHT = 320
else:
    print("在非Linux系统上运行，使用默认配置...")
    # 在macOS/Windows上运行时，PyQt5会自动选择合适的平台插件，无需手动设置。
    # 如果系统是macOS，Qt会自动选择cocoa平台插件。
    # 窗口尺寸使用默认值或你希望在桌面上显示的尺寸
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# 定义一个退出信号，便于上级进程识别
EXIT_SIGNAL = "BROWSER_CLOSED_SUCCESSFULLY"

class BrowserWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("桌面浏览器")
        self.resize(QSize(WINDOW_WIDTH, WINDOW_HEIGHT))
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        self.browser = QWebEngineView()
        self.browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.browser.setUrl(QUrl("https://www.winddine.top"))
        
        self.browser.setZoomFactor(0.8)

        self.quit_button = QPushButton("退出")
        # 优化退出按钮：调整字体大小和按钮高度，使其更易于触摸
        font = QFont()
        font.setPointSize(24)  # 增大字体大小到24
        self.quit_button.setFont(font)
        
        # 调整按钮尺寸策略，确保按钮可以填充布局并保持合理的最小高度
        self.quit_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.quit_button.setMinimumHeight(60) # 增大最小高度

        self.quit_button.setStyleSheet("background-color: #ff4d4d; color: white; border: none; border-radius: 5px;")
        
        self.quit_button.clicked.connect(self.on_quit)
        
        # 使用 QSizePolicy 来控制布局的伸缩比例
        # 浏览器占据大部分空间
        layout.addWidget(self.browser, 1)
        # 退出按钮占据较小空间
        layout.addWidget(self.quit_button, 0)
    
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