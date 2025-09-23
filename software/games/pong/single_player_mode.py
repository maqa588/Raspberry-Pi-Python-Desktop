import pygame
import sys
import time
import settings
import game_objects
import ui_elements

def run_single_player():
    """运行单人（本地双人）游戏模式。"""
    clock = pygame.time.Clock()
    joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]

    # --- 游戏对象 ---
    left_paddle = game_objects.Paddle(20, settings.HEIGHT // 2 - settings.PADDLE_HEIGHT // 2)
    right_paddle = game_objects.Paddle(settings.WIDTH - 20 - settings.PADDLE_WIDTH, settings.HEIGHT // 2 - settings.PADDLE_HEIGHT // 2)
    ball = game_objects.Ball()
    score = {'p1': 0, 'p2': 0}
    
    game_state = 'PLAYING' # PLAYING, PAUSED, GAME_OVER
    
    running = True
    while running:
        dt = clock.tick(settings.FPS) / 1000.0
        
        # --- 事件处理 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # --- 键盘事件 ---
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state = 'PAUSED' if game_state == 'PLAYING' else 'PLAYING'
                
                if game_state == 'PAUSED':
                    if event.key == pygame.K_RETURN: # 继续
                        game_state = 'PLAYING'
                    if event.key == pygame.K_q: # 退出
                        running = False
                
                if game_state == 'GAME_OVER':
                    if event.key == pygame.K_RETURN: # 返回菜单
                        running = False
            
            # --- 手柄按钮事件 ---
            if event.type == pygame.JOYBUTTONDOWN:
                # Select键 (通常是 button 6) 暂停
                if event.button == 6 and game_state in ['PLAYING', 'PAUSED']:
                    game_state = 'PAUSED' if game_state == 'PLAYING' else 'PLAYING'
                
                if game_state == 'PAUSED':
                    if event.button == 0: # A键 继续
                        game_state = 'PLAYING'
                    if event.button == 1: # B键 退出
                        running = False
                
                if game_state == 'GAME_OVER':
                    if event.button == 0: # A键 返回菜单
                        running = False
        
        # --- 游戏逻辑更新 ---
        if game_state == 'PLAYING':
            keys = pygame.key.get_pressed()
            
            # P1 控制 (W/S 或 左摇杆)
            p1_dy = 0
            if keys[pygame.K_w]: p1_dy = -1
            if keys[pygame.K_s]: p1_dy = 1
            if joysticks: p1_dy += joysticks[0].get_axis(1)
            left_paddle.move(p1_dy, dt)
            
            # P2 控制 (方向键 或 右摇杆)
            p2_dy = 0
            if keys[pygame.K_UP]: p2_dy = -1
            if keys[pygame.K_DOWN]: p2_dy = 1
            if joysticks:
                # 使用右摇杆Y轴 (axis 3)
                if joysticks[0].get_numaxes() > 3:
                    p2_dy += joysticks[0].get_axis(3)
            right_paddle.move(p2_dy, dt)
            
            # 球的移动与碰撞
            ball.move(dt)
            if ball.rect.top <= 0 or ball.rect.bottom >= settings.HEIGHT:
                ball.speed_y *= -1
            if ball.rect.colliderect(left_paddle.rect) and ball.speed_x < 0:
                ball.speed_x *= -1.05
            if ball.rect.colliderect(right_paddle.rect) and ball.speed_x > 0:
                ball.speed_x *= -1.05

            # 得分
            if ball.rect.left <= 0:
                score['p2'] += 1
                ball.reset(1)
            if ball.rect.right >= settings.WIDTH:
                score['p1'] += 1
                ball.reset(-1)

            # 游戏结束
            if score['p1'] >= settings.WINNING_SCORE or score['p2'] >= settings.WINNING_SCORE:
                game_state = 'GAME_OVER'

        # --- 绘制 ---
        settings.WINDOW.fill(settings.BLACK)
        pygame.draw.aaline(settings.WINDOW, settings.GRAY, (settings.WIDTH // 2, 0), (settings.WIDTH // 2, settings.HEIGHT))
        left_paddle.draw(settings.WINDOW)
        right_paddle.draw(settings.WINDOW)
        ball.draw(settings.WINDOW)
        
        ui_elements.draw_text(f"P1", settings.FONT_M, settings.WHITE, settings.WINDOW, settings.WIDTH / 4, 20)
        ui_elements.draw_text(f"{score['p1']}", settings.FONT_L, settings.WHITE, settings.WINDOW, settings.WIDTH / 4, 60)
        ui_elements.draw_text(f"P2", settings.FONT_M, settings.WHITE, settings.WINDOW, settings.WIDTH * 3 / 4, 20)
        ui_elements.draw_text(f"{score['p2']}", settings.FONT_L, settings.WHITE, settings.WINDOW, settings.WIDTH * 3 / 4, 60)

        if game_state == 'PAUSED':
            overlay = pygame.Surface((settings.WIDTH, settings.HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            settings.WINDOW.blit(overlay, (0,0))
            ui_elements.draw_text("游戏暂停", settings.FONT_L, settings.WHITE, settings.WINDOW, settings.WIDTH/2, settings.HEIGHT/4)
            ui_elements.draw_text("按 A键/Enter 继续", settings.FONT_M, settings.WHITE, settings.WINDOW, settings.WIDTH/2, 150)
            ui_elements.draw_text("按 B键/Q 返回主菜单", settings.FONT_M, settings.WHITE, settings.WINDOW, settings.WIDTH/2, 200)

        if game_state == 'GAME_OVER':
            overlay = pygame.Surface((settings.WIDTH, settings.HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            settings.WINDOW.blit(overlay, (0,0))
            winner = "P1" if score['p1'] > score['p2'] else "P2"
            ui_elements.draw_text("游戏结束", settings.FONT_L, settings.WHITE, settings.WINDOW, settings.WIDTH/2, settings.HEIGHT/4)
            ui_elements.draw_text(f"玩家 {winner} 胜利!", settings.FONT_M, settings.GREEN, settings.WINDOW, settings.WIDTH/2, settings.HEIGHT/2 - 20)
            ui_elements.draw_button("返回菜单 (A键/Enter)", settings.FONT_M, settings.WINDOW, pygame.Rect(settings.WIDTH/2 - 125, settings.HEIGHT - 100, 250, 50), 0, 0)

        pygame.display.flip()

