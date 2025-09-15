# system/browser_app.py
import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QSizePolicy, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QLineEdit
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QSize, Qt
from PyQt5.QtGui import QFont, QIcon

# 启用高 DPI 缩放，使其在不同分辨率屏幕上显示正常
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

# --- 优化平台判断逻辑 ---
# 在明确是 Linux 系统时，才设置特定的嵌入式环境变量
if sys.platform.startswith('linux'):
    print("在Linux系统上运行，启用嵌入式模式...")
    # 检查是否为树莓派，并设置特定的环境变量
    # 这里的设备路径需要根据你的实际设备进行调整
    # 例如：/dev/input/event0 或其他
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
    os.environ["QT_QPA_PLATFORM"] = "eglfs"
    os.environ["QT_QPA_EGLFS_PHYSICAL_WIDTH"] = "480"
    os.environ["QT_QPA_EGLFS_PHYSICAL_HEIGHT"] = "320"
    os.environ["QT_QPA_EGLFS_INTEGRATION"] = "eglfs_brcm"
    os.environ["QT_QPA_GENERIC_TOUCH_INPUT"] = "/dev/input/event0"
    WINDOW_WIDTH = 480
    WINDOW_HEIGHT = 320

# 在 macOS 上运行时，使用默认配置
elif sys.platform == 'darwin':
    print("在macOS上运行，使用默认配置...")
    # 确保没有设置任何影响macOS本地渲染的环境变量
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600
    
# 其他平台使用通用默认配置
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
        self.url_bar.setFont(QFont("Arial", 10))
        self.url_bar.setStyleSheet("""
            QLineEdit { 
                background-color: #f0f0f0; 
                padding: 5px; 
                border-radius: 5px; 
                border: 1px solid #ccc; 
                color: black;
            }
        """)
        self.url_bar.setAlignment(Qt.AlignCenter)

        self.browser = QWebEngineView()
        self.browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.browser.setUrl(QUrl("https://www.winddine.top"))
        self.browser.setZoomFactor(0.8)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)

        # 返回按钮
        self.back_button = QPushButton()
        self.back_button.setIcon(QIcon.fromTheme("go-previous"))
        self.back_button.setText("上一页")
        self.back_button.setStyleSheet("background-color: #4CAF50; color: white; border: none; border-radius: 5px; padding: 10px;")
        self.back_button.clicked.connect(self.browser.back)
        button_layout.addWidget(self.back_button)

        # 前进按钮
        self.next_button = QPushButton()
        self.next_button.setIcon(QIcon.fromTheme("go-next"))
        self.next_button.setText("下一页")
        self.next_button.setStyleSheet("background-color: #4CAF50; color: white; border: none; border-radius: 5px; padding: 10px;")
        self.next_button.clicked.connect(self.browser.forward)
        button_layout.addWidget(self.next_button)

        # 刷新按钮
        self.refresh_button = QPushButton()
        self.refresh_button.setIcon(QIcon.fromTheme("view-refresh"))
        self.refresh_button.setText("刷新")
        self.refresh_button.setStyleSheet("background-color: #4CAF50; color: white; border: none; border-radius: 5px; padding: 10px;")
        self.refresh_button.clicked.connect(self.browser.reload)
        button_layout.addWidget(self.refresh_button)
        
        # 主页按钮
        self.home_button = QPushButton()
        self.home_button.setIcon(QIcon.fromTheme("go-home"))
        self.home_button.setText("主页")
        self.home_button.setStyleSheet("background-color: #2196F3; color: white; border: none; border-radius: 5px; padding: 10px;")
        self.home_button.clicked.connect(self.go_home)
        button_layout.addWidget(self.home_button)
        
        # 退出按钮
        self.quit_button = QPushButton("退出")
        self.quit_button.setIcon(QIcon.fromTheme("application-exit"))
        font = QFont()
        font.setPointSize(14)
        self.quit_button.setFont(font)
        self.quit_button.setStyleSheet("background-color: #ff4d4d; color: white; border: none; border-radius: 5px; padding: 10px;")
        self.quit_button.clicked.connect(self.on_quit)
        button_layout.addWidget(self.quit_button)

        # 关联 URL 变化和 URL 地址栏
        self.browser.urlChanged.connect(self.update_url_bar)
        
        # 将所有控件添加到主布局中
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