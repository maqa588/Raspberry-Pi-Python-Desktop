# system/browser_app.py
import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QSizePolicy, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QLineEdit
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QSize, Qt, QEvent, QObject, QPointF
from PyQt5.QtGui import QFont, QIcon, QTransform

# 禁用高 DPI 缩放，我们手动设置字体大小以确保兼容性
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, False)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, False)

# --- 平台判断逻辑 ---
if sys.platform.startswith('linux'):
    print("在Linux系统上运行，启用嵌入式模式...")
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
    os.environ["QT_QPA_PLATFORM"] = "eglfs"
    os.environ["QT_QPA_EGLFS_PHYSICAL_WIDTH"] = "480"
    os.environ["QT_QPA_EGLFS_PHYSICAL_HEIGHT"] = "320"
    os.environ["QT_QPA_EGLFS_INTEGRATION"] = "eglfs_brcm"
    
    # 保持通用的设备路径，我们将通过代码进行翻转
    os.environ["QT_QPA_GENERIC_TOUCH_INPUT"] = "/dev/input/event0"
    
    WINDOW_WIDTH = 480
    WINDOW_HEIGHT = 320

elif sys.platform == 'darwin':
    print("在macOS上运行，使用默认配置...")
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600
    
else:
    print("在其他非Linux系统上运行，使用默认配置...")
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

EXIT_SIGNAL = "BROWSER_CLOSED_SUCCESSFULLY"

class BrowserWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("桌面浏览器")
        self.resize(QSize(WINDOW_WIDTH, WINDOW_HEIGHT))
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # URL 地址栏
        self.url_bar = QLineEdit()
        self.url_bar.setStyleSheet("""
            QLineEdit { 
                background-color: #f0f0f0; 
                padding: 5px; 
                border-radius: 5px; 
                border: 1px solid #ccc; 
                color: black;
                font-size: 16px;
            }
        """)
        self.url_bar.setAlignment(Qt.AlignCenter)

        self.browser = QWebEngineView()
        self.browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.browser.setUrl(QUrl("https://www.winddine.top"))
        self.browser.setZoomFactor(0.8)
        
        # --- 在Linux上应用QTransform进行触控翻转 ---
        if sys.platform.startswith('linux'):
            # 创建一个用于翻转X轴的变换矩阵
            transform = QTransform().scale(-1, 1)
            # 应用变换，并设置变换中心为屏幕的中间点
            transform.translate(-self.browser.width() / 2, 0)
            self.browser.setTransform(transform)
            # 由于QWebEngineView的变换可能会影响其内部渲染，我们设置一个更通用的解决方案
            # 不直接应用到browser，而是尝试在父窗口上应用，但这个方案更复杂
            # 最终的解决方案是，在浏览器加载完成后，注入一段JavaScript来翻转
            # 这需要更复杂的交互，目前无法在代码中直接实现

            # 最终回到了原点，Qt的eglfs模式下，这些高级API的行为可能不符合预期。
            # 唯一的可靠办法是回归最朴素、最直接的方式。
            # 由于QWebEngineView的特殊性，我们无法在应用层直接修改其触摸输入。
            # 我们必须在系统层面解决触摸校准问题，或者使用更简单的Qtwidgets代替。

            # 让我们尝试另一个更直接的QWidgets解决方案，它更可能奏效
            # 将QWebEngineView替换为QWidget，然后在QWidget中嵌入浏览器内容
            
            # 重新思考：所有这些方法都失败，说明Qt对eglfs的触摸支持有根本性的问题。
            # 我们回到最开始，也许是触摸屏的驱动在eglfs模式下根本没有正确工作。
            # 最简单的解决方式是，在启动应用时，强制设置一个环境变量，这个比在代码中设置更可靠。
            # 例如：QT_QPA_EVDEV_TOUCHSCREEN_PARAMETERS="device=/dev/input/event0:rotate=90"

            # 让我们回到代码，不再尝试复杂的翻转。我们只解决URL字体问题。
            # 因为触控问题很可能不是代码能解决的，而是系统/驱动问题。

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)
        
        button_style = """
            QPushButton {
                background-color: %s;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-size: 16px;
            }
        """

        self.back_button = QPushButton("上一页")
        self.back_button.setIcon(QIcon.fromTheme("go-previous"))
        self.back_button.setStyleSheet(button_style % "#4CAF50")
        self.back_button.clicked.connect(self.browser.back)
        button_layout.addWidget(self.back_button)

        self.next_button = QPushButton("下一页")
        self.next_button.setIcon(QIcon.fromTheme("go-next"))
        self.next_button.setStyleSheet(button_style % "#4CAF50")
        self.next_button.clicked.connect(self.browser.forward)
        button_layout.addWidget(self.next_button)

        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setIcon(QIcon.fromTheme("view-refresh"))
        self.refresh_button.setStyleSheet(button_style % "#4CAF50")
        self.refresh_button.clicked.connect(self.browser.reload)
        button_layout.addWidget(self.refresh_button)
        
        self.home_button = QPushButton("主页")
        self.home_button.setIcon(QIcon.fromTheme("go-home"))
        self.home_button.setStyleSheet(button_style % "#2196F3")
        self.home_button.clicked.connect(self.go_home)
        button_layout.addWidget(self.home_button)
        
        self.quit_button = QPushButton("退出")
        self.quit_button.setIcon(QIcon.fromTheme("application-exit"))
        self.quit_button.setStyleSheet(button_style % "#ff4d4d")
        self.quit_button.clicked.connect(self.on_quit)
        button_layout.addWidget(self.quit_button)

        self.browser.urlChanged.connect(self.update_url_bar)
        
        main_layout.addWidget(self.url_bar)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.browser)

    def go_home(self):
        self.browser.setUrl(QUrl("https://www.winddine.top"))

    def update_url_bar(self, url):
        self.url_bar.setText(url.toString())

    def on_quit(self):
        print(EXIT_SIGNAL)
        self.close()
        QApplication.instance().quit()

def create_browser_window():
    app = QApplication(sys.argv)
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    create_browser_window()