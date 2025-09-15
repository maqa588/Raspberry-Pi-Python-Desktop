# system/config.py
import sys
import os

def get_resource_path(relative_path):
    """
    获取资源的绝对路径，兼容打包和未打包环境。
    """
    if getattr(sys, 'frozen', False):
        # 如果是 PyInstaller 打包后的环境
        base_path = sys._MEIPASS
    else:
        # 如果是开发环境
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- 配置 ---
CONFIG_FILE = 'system/desktop_layout.json'
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 290
# 画布的虚拟大小，大于窗口尺寸以实现滚动效果
CANVAS_WIDTH = 800
CANVAS_HEIGHT = 600