import pygame
import time
import sys
from pathlib import Path

# --- 确保开发阶段也能用绝对导入 ---
if not getattr(sys, 'frozen', False):
    # 定位到项目根目录
    current_file = Path(__file__).resolve()
    project_root = current_file.parents[3]  # 回到 project_root
    sys.path.insert(0, str(project_root))

from software.games.pong import settings
from software.games.pong import ui_elements
from software.games.pong import single_player_mode
from software.games.pong import online_mode

class MainMenu:
    """
    Pong 游戏的主菜单类，负责初始化、事件循环、导航和渲染。
    """
    def __init__(self):
        # 1. 初始化 Pygame 和设置
        pygame.init()
        
        # 屏幕/窗口引用
        self.window = settings.WINDOW
        self.width = settings.WIDTH
        self.height = settings.HEIGHT
        self.clock = pygame.time.Clock()
        self.fps = settings.FPS
        
        # 2. 手柄/摇杆初始化
        # 注意: 摇杆初始化如果再次引起问题，可以暂时注释掉测试
        pygame.joystick.init()
        self.joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        for joystick in self.joysticks:
            if joystick.get_init():
                joystick.init()
        
        # 3. 菜单状态
        self.menu_options = [
            "单人游戏", 
            "在线游戏", 
            "退出"
        ]
        self.num_options = len(self.menu_options)
        self.selection_index = 0
        self.last_axis_move = 0.0 # 用于控制摇杆/键盘连发速度
        self.axis_cooldown = 0.2

    def _handle_navigation(self):
        """处理键盘和摇杆的菜单导航输入。"""
        current_time = time.time()
        
        # 键盘输入
        keys = pygame.key.get_pressed()
        key_up = keys[pygame.K_UP] or keys[pygame.K_w]
        key_down = keys[pygame.K_DOWN] or keys[pygame.K_s]
        
        # 摇杆输入
        axis_y = 0
        if self.joysticks:
            # 获取第一个摇杆的 Y 轴和方向键 (Hat) 输入
            if self.joysticks[0].get_numaxes() > 1: # 确保有第二个轴
                axis_y = self.joysticks[0].get_axis(1)
            if self.joysticks[0].get_numhats() > 0:
                axis_y += -self.joysticks[0].get_hat(0)[1]

        if current_time - self.last_axis_move > self.axis_cooldown:
            moved = False
            # 向上移动
            if axis_y < -0.5 or key_up:
                self.selection_index = (self.selection_index - 1) % self.num_options
                moved = True
            # 向下移动
            elif axis_y > 0.5 or key_down:
                self.selection_index = (self.selection_index + 1) % self.num_options
                moved = True
            
            if moved:
                self.last_axis_move = current_time


    def _execute_selection(self):
        """根据当前选择的索引执行对应的操作。"""
        if self.selection_index == 0:
            print("INFO: 启动单人模式...")
            single_player_mode.run_single_player()
        elif self.selection_index == 1:
            print("INFO: 启动在线模式...")
            online_mode.run_online_mode()
        elif self.selection_index == 2:
            self._quit_game()

    def _quit_game(self):
        """退出 Pygame 窗口和 Python 进程。"""
        print("INFO: 退出游戏。")
        pygame.quit()
        sys.exit()

    def run(self):
        """主菜单的事件循环。"""
        while True:
            # --- 1. 事件处理 ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._quit_game()
                
                # 键盘确认
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self._execute_selection()

                # 摇杆按钮确认 (A/按钮0)
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 0: 
                        self._execute_selection()
                    elif event.button == 1: # B 键退出
                        self._quit_game()
            
            # --- 2. 菜单导航 (在事件循环外处理，以便于摇杆/按键长按) ---
            self._handle_navigation()
            
            # --- 3. 绘制 ---
            self.window.fill(settings.BLACK)
            
            # 标题
            ui_elements.draw_text(
                "Pong Game", 
                settings.FONT_L, 
                settings.WHITE, 
                self.window, 
                self.width / 2, 
                self.height / 4
            )
            
            # 选项按钮
            button_positions = [self.height / 2 - 50, self.height / 2 + 0, self.height / 2 + 50]
            for i, option_text in enumerate(self.menu_options):
                rect = pygame.Rect(self.width/2 - 100, button_positions[i], 200, 40)
                ui_elements.draw_button(
                    option_text, 
                    settings.FONT_M, 
                    self.window, 
                    rect, 
                    self.selection_index, 
                    i
                )
            
            pygame.display.flip()
            self.clock.tick(self.fps)

def run_game_menu():
    """
    子进程调用的入口函数。
    实例化 MainMenu 并启动其主循环。
    """
    game_menu = MainMenu()
    game_menu.run()

if __name__ == "__main__":
    run_game_menu() 
