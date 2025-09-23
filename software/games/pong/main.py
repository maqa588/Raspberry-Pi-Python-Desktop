import pygame
import sys
import time
import settings
import ui_elements
import single_player_mode
import online_mode

def main_menu():
    """
    显示主菜单并处理用户选择。
    """
    pygame.init()
    joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
    
    clock = pygame.time.Clock()
    selection_index = 0
    last_axis_move = 0
    
    while True:
        # --- 事件处理 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if selection_index == 0:
                        single_player_mode.run_single_player()
                    elif selection_index == 1:
                        online_mode.run_online_mode()
                    elif selection_index == 2:
                        pygame.quit()
                        sys.exit()
            if event.type == pygame.JOYBUTTONDOWN:
                 if event.button == 0: # A button
                    if selection_index == 0:
                        single_player_mode.run_single_player()
                    elif selection_index == 1:
                        online_mode.run_online_mode()
                    elif selection_index == 2:
                        pygame.quit()
                        sys.exit()
                 elif event.button == 1: # B button to quit
                    pygame.quit()
                    sys.exit()


        # --- 菜单导航 ---
        axis_y = 0
        if joysticks:
            axis_y = joysticks[0].get_axis(1)
            if joysticks[0].get_numhats() > 0:
                axis_y += -joysticks[0].get_hat(0)[1]

        keys = pygame.key.get_pressed()
        key_up = keys[pygame.K_UP] or keys[pygame.K_w]
        key_down = keys[pygame.K_DOWN] or keys[pygame.K_s]

        if time.time() - last_axis_move > 0.2:
            moved = False
            if axis_y < -0.5 or key_up:
                selection_index -= 1
                moved = True
            elif axis_y > 0.5 or key_down:
                selection_index += 1
                moved = True
            if moved:
                last_axis_move = time.time()
        
        selection_index %= 3 # 3个选项

        # --- 绘制 ---
        settings.WINDOW.fill(settings.BLACK)
        ui_elements.draw_text("Pong Game", settings.FONT_L, settings.WHITE, settings.WINDOW, settings.WIDTH/2, settings.HEIGHT/4)
        
        ui_elements.draw_button("单人游戏", settings.FONT_M, settings.WINDOW, pygame.Rect(settings.WIDTH/2-100, 150, 200, 40), selection_index, 0)
        ui_elements.draw_button("在线游戏", settings.FONT_M, settings.WINDOW, pygame.Rect(settings.WIDTH/2-100, 200, 200, 40), selection_index, 1)
        ui_elements.draw_button("退出", settings.FONT_M, settings.WINDOW, pygame.Rect(settings.WIDTH/2-100, 250, 200, 40), selection_index, 2)
        
        pygame.display.flip()
        clock.tick(settings.FPS)

def create_pong_game():
    """初始化并运行乒乓球游戏的主菜单。"""
    main_menu()

if __name__ == "__main__":
    create_pong_game()

