import pygame
import os
import socket

# =============================================================================
# 1. 初始化与常量设置
# =============================================================================
pygame.init()
pygame.font.init()

# -- 窗口设置 --
WIDTH, HEIGHT = 480, 320
WINDOW = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pong Game")
FPS = 60

# -- 颜色 --
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
DARK_GRAY = (50, 50, 50)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
BLUE = (0, 150, 255)

# -- 游戏对象属性 --
PADDLE_WIDTH, PADDLE_HEIGHT = 15, 80
BALL_RADIUS = 8
WINNING_SCORE = 5

# -- 网络设置 --
PORT = 5555
BROADCAST_ADDR = "255.255.255.255" # 更通用的广播地址
MY_USERNAME = f"Player_{str(socket.gethostname())[:6]}"
try:
    MY_IP = socket.gethostbyname(socket.gethostname())
except socket.gaierror:
    MY_IP = "127.0.0.1"

# -- 字体加载 --
try:
    # 使用相对路径来定位字体文件
    script_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(script_dir, "fonts", "ChillBitmap_16px.ttf")
    FONT_S = pygame.font.Font(font_path, 18)
    FONT_M = pygame.font.Font(font_path, 28)
    FONT_L = pygame.font.Font(font_path, 42)
except pygame.error:
    print("警告: 自定义字体未找到，将使用默认字体。")
    FONT_S = pygame.font.Font(None, 24)
    FONT_M = pygame.font.Font(None, 36)
    FONT_L = pygame.font.Font(None, 60)
