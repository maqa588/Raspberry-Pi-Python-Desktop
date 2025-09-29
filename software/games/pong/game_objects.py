import pygame
import time
from software.games.pong import settings

class Paddle:
    """代表玩家的球拍"""
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, settings.PADDLE_WIDTH, settings.PADDLE_HEIGHT)
        self.speed = 300

    def draw(self, surface):
        pygame.draw.rect(surface, settings.WHITE, self.rect)

    def move(self, dy, dt):
        """根据输入移动球拍"""
        self.rect.y += dy * self.speed * dt
        # 限制球拍在窗口内移动
        self.rect.clamp_ip(pygame.Rect(0, 0, settings.WIDTH, settings.HEIGHT))

    def set_pos(self, y):
        """直接设置球拍位置（用于网络同步）"""
        self.rect.y = y
        self.rect.clamp_ip(pygame.Rect(0, 0, settings.WIDTH, settings.HEIGHT))

class Ball:
    """代表游戏中的球"""
    def __init__(self):
        self.rect = pygame.Rect(0, 0, settings.BALL_RADIUS * 2, settings.BALL_RADIUS * 2)
        self.speed_x = 0
        self.speed_y = 0
        self.reset()

    def draw(self, surface):
        pygame.draw.ellipse(surface, settings.WHITE, self.rect)

    def move(self, dt):
        """移动球"""
        self.rect.x += self.speed_x * dt
        self.rect.y += self.speed_y * dt

    def set_pos(self, x, y):
        """直接设置球的位置（用于客户端同步）"""
        self.rect.center = (x, y)

    def reset(self, direction=1):
        """重置球的位置和速度"""
        self.rect.center = (settings.WIDTH // 2, settings.HEIGHT // 2)
        # 随机化初始Y轴方向
        y_direction = 1 if time.time() % 2 > 1 else -1
        self.speed_x = 250 * direction
        self.speed_y = 200 * y_direction
