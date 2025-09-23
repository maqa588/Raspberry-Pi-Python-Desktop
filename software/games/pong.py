import pygame
import sys
import os

# 初始化 Pygame
pygame.init()

# 窗口设置
WIDTH, HEIGHT = 480, 320
WINDOW = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pong Game")

# 颜色
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# 游戏对象属性
PADDLE_WIDTH, PADDLE_HEIGHT = 10, 60
BALL_RADIUS = 7

# 获取当前脚本的绝对路径
script_dir = os.path.dirname(__file__)

# 构建字体文件的绝对路径
font_path = os.path.join(script_dir, "fonts", "ChillBitmap_16px.ttf")

# 字体设置
try:
    font = pygame.font.Font(font_path, 36)
    pause_font = pygame.font.Font(font_path, 60)
except pygame.error:
    font = pygame.font.Font(None, 36)
    pause_font = pygame.font.Font(None, 60)
    print("警告: 字体文件未找到，中文可能显示为方块。")

# 游戏对象类
class Paddle:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, PADDLE_WIDTH, PADDLE_HEIGHT)
        self.speed = 200 # 单位：像素/秒

    def draw(self, surface):
        pygame.draw.rect(surface, WHITE, self.rect)

    def move(self, dy, dt):
        self.rect.y += dy * self.speed * dt
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.bottom > HEIGHT:
            self.rect.bottom = HEIGHT

class Ball:
    def __init__(self):
        self.rect = pygame.Rect(WIDTH // 2 - BALL_RADIUS, HEIGHT // 2 - BALL_RADIUS, BALL_RADIUS * 2, BALL_RADIUS * 2)
        self.speed_x = 150 # 单位：像素/秒
        self.speed_y = 150 # 单位：像素/秒

    def draw(self, surface):
        pygame.draw.ellipse(surface, WHITE, self.rect)

    def move(self, dt):
        self.rect.x += self.speed_x * dt
        self.rect.y += self.speed_y * dt
        
    def reset(self):
        self.rect.center = (WIDTH // 2, HEIGHT // 2)
        self.speed_x *= -1

# 游戏状态
game_paused = False

def draw_pause_menu():
    """绘制暂停菜单"""
    pause_text = pause_font.render("暂停", True, WHITE)
    resume_text = font.render("继续游戏 (Enter)", True, WHITE)
    quit_text = font.render("退出游戏 (Q)", True, WHITE)
    
    WINDOW.blit(pause_text, (WIDTH // 2 - pause_text.get_width() // 2, HEIGHT // 2 - 100))
    WINDOW.blit(resume_text, (WIDTH // 2 - resume_text.get_width() // 2, HEIGHT // 2))
    WINDOW.blit(quit_text, (WIDTH // 2 - quit_text.get_width() // 2, HEIGHT // 2 + 50))
    pygame.display.flip()

def main():
    global game_paused
    
    left_paddle = Paddle(10, HEIGHT // 2 - PADDLE_HEIGHT // 2)
    right_paddle = Paddle(WIDTH - 10 - PADDLE_WIDTH, HEIGHT // 2 - PADDLE_HEIGHT // 2)
    ball = Ball()
    
    joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
    for j in joysticks:
        j.init()
    
    print("手柄信息：")
    for j in joysticks:
        print(f"  名称: {j.get_name()}")
        print(f"  按钮数量: {j.get_numbuttons()}")
        print(f"  摇杆数量: {j.get_numaxes()}")
    
    clock = pygame.time.Clock()

    running = True
    while running:
        # 获取自上一帧以来的时间，以秒为单位
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_paused = not game_paused
                elif game_paused:
                    if event.key == pygame.K_RETURN:
                        game_paused = False
                    elif event.key == pygame.K_q:
                        running = False
            
            if event.type == pygame.JOYBUTTONDOWN:
                print(f"手柄按钮按下：{event.button}")
                if event.button == 8: # 假设你的 Select 键是按钮 8
                    game_paused = not game_paused
                
                if game_paused:
                    if event.button == 0:
                        game_paused = False
                    elif event.button == 1:
                        running = False

        if game_paused:
            draw_pause_menu()
            continue

        # 键盘控制
        keys = pygame.key.get_pressed()
        
        # 控制左侧球拍 (W/S 键)
        if keys[pygame.K_w]:
            left_paddle.move(-1, dt)
        if keys[pygame.K_s]:
            left_paddle.move(1, dt)
            
        # 控制右侧球拍 (上/下箭头键)
        if keys[pygame.K_UP]:
            right_paddle.move(-1, dt)
        if keys[pygame.K_DOWN]:
            right_paddle.move(1, dt)

        # 游戏手柄控制
        for j in joysticks:
            if j.get_init():
                left_axis_y = j.get_axis(1)
                left_paddle.move(left_axis_y, dt)
                
                right_axis_y = j.get_axis(3)
                right_paddle.move(right_axis_y, dt)

        # 移动球
        ball.move(dt)

        # 碰撞检测 - 墙壁
        if ball.rect.top <= 0 or ball.rect.bottom >= HEIGHT:
            ball.speed_y *= -1

        # 碰撞检测 - 球拍
        if ball.rect.colliderect(left_paddle.rect) or ball.rect.colliderect(right_paddle.rect):
            ball.speed_x *= -1

        # 碰撞检测 - 得分
        if ball.rect.left <= 0 or ball.rect.right >= WIDTH:
            ball.reset()
        
        # 绘制
        WINDOW.fill(BLACK)
        left_paddle.draw(WINDOW)
        right_paddle.draw(WINDOW)
        ball.draw(WINDOW)
        
        pygame.draw.aaline(WINDOW, WHITE, (WIDTH // 2, 0), (WIDTH // 2, HEIGHT)) # 中线
        
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()