import pygame
import sys
import socket
import json
import threading
import time
from collections import deque
from software.games.pong import settings
from software.games.pong import game_objects
from software.games.pong import ui_elements

# =============================================================================
# 网络通信模块
# =============================================================================
class NetworkManager:
    """处理所有网络发现和游戏数据交换"""
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('', settings.PORT))
        self.sock.setblocking(False)
        self.message_queue = deque()
        self.running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()

    def _listen(self):
        """在独立线程中持续监听传入的数据包"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                if addr[0] != settings.MY_IP:
                    try:
                        message = json.loads(data.decode())
                        self.message_queue.append({'addr': addr, 'data': message})
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass
            except BlockingIOError:
                pass
            except OSError: # Socket was closed
                break
            time.sleep(0.001)

    def send(self, data, addr):
        """发送数据到指定地址"""
        try:
            if self.running:
                self.sock.sendto(json.dumps(data).encode(), addr)
        except OSError as e:
            print(f"发送数据时出错: {e}")

    def broadcast(self, data):
        """广播数据到局域网"""
        self.send(data, (settings.BROADCAST_ADDR, settings.PORT))

    def get_message(self):
        """从队列中获取一条消息（非阻塞）"""
        if self.message_queue:
            return self.message_queue.popleft()
        return None

    def close(self):
        """关闭socket并停止监听线程"""
        self.running = False
        self.sock.close()
        self.thread.join(timeout=0.2)
        print("Network socket closed.")

# =============================================================================
# 在线游戏主类
# =============================================================================
class OnlineGame:
    """管理在线游戏状态、循环和渲染"""
    def __init__(self):
        self.clock = pygame.time.Clock()
        self.network = NetworkManager()
        self.joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        self.reset_game_state()

    def reset_game_state(self):
        """重置所有游戏变量到初始状态"""
        self.game_mode = 'LOBBY' # LOBBY, WAITING, PLAYING, PAUSED, GAME_OVER
        self.is_host = False
        self.opponent_addr = None
        
        self.left_paddle = game_objects.Paddle(20, settings.HEIGHT // 2 - settings.PADDLE_HEIGHT // 2)
        self.right_paddle = game_objects.Paddle(settings.WIDTH - 20 - settings.PADDLE_WIDTH, settings.HEIGHT // 2 - settings.PADDLE_HEIGHT // 2)
        self.ball = game_objects.Ball()
        self.score = {'p1': 0, 'p2': 0}
        
        self.found_players = {}
        self.last_broadcast_time = 0
        self.invitation = None
        self.popup_message = None
        self.popup_timer = 0
        
        self.selection_index = 0
        self.last_axis_move = 0

        # 游戏结束后的选择状态
        self.my_choice = None
        self.opponent_choice = None
        self.winner = None


    def run(self):
        """游戏主循环"""
        running = True
        while running:
            dt = self.clock.tick(settings.FPS) / 1000.0
            
            if self.game_mode == 'MENU': # 如果返回菜单，则退出循环
                running = False
                continue

            events = pygame.event.get()
            self.handle_input(events)
            self.handle_network()
            self.update(dt)
            self.draw()
            pygame.display.flip()
        
        self.network.close() # 在退出循环后关闭网络连接

    # --- 输入处理 ---
    def handle_input(self, events):
        """统一处理键盘和手柄输入"""
        for event in events:
            if event.type == pygame.QUIT:
                if self.opponent_addr:
                    self.network.send({'type': 'quit'}, self.opponent_addr)
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if self.invitation: self.handle_popup_input('kb_down', event.key)
                elif self.game_mode == 'LOBBY': self.handle_lobby_input('kb_down', event.key)
                elif self.game_mode == 'PAUSED': self.handle_pause_input('kb_down', event.key)
                elif self.game_mode == 'GAME_OVER': self.handle_game_over_input('kb_down', event.key)

            if event.type == pygame.JOYBUTTONDOWN:
                if self.invitation: self.handle_popup_input('joy_down', event.button)
                elif self.game_mode == 'LOBBY': self.handle_lobby_input('joy_down', event.button)
                # Select键 (通常是 button 6) 暂停
                elif event.button == 6 and self.game_mode == 'PLAYING' and self.is_host: 
                    self.game_mode = 'PAUSED'
                elif self.game_mode == 'PAUSED': self.handle_pause_input('joy_down', event.button)
                elif self.game_mode == 'GAME_OVER': self.handle_game_over_input('joy_down', event.button)

        # --- 摇杆/十字键连续输入 (用于菜单导航) ---
        axis_y, axis_x = 0, 0
        if self.joysticks:
            axis_y = self.joysticks[0].get_axis(1) # 左摇杆 Y
            axis_x = self.joysticks[0].get_axis(0) # 左摇杆 X
            if self.joysticks[0].get_numhats() > 0:
                hat_x, hat_y = self.joysticks[0].get_hat(0)
                axis_y -= hat_y # 十字键 Y
                axis_x += hat_x  # 十字键 X

        keys = pygame.key.get_pressed()
        
        if time.time() - self.last_axis_move > 0.2:
            moved = False
            # 垂直导航
            key_up = keys[pygame.K_UP] or keys[pygame.K_w]
            key_down = keys[pygame.K_DOWN] or keys[pygame.K_s]
            if axis_y < -0.5 or key_up:
                self.selection_index -= 1; moved = True
            elif axis_y > 0.5 or key_down:
                self.selection_index += 1; moved = True
            
            # 水平导航 (仅用于邀请弹窗)
            if self.invitation:
                key_left = keys[pygame.K_LEFT] or keys[pygame.K_a]
                key_right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
                if axis_x < -0.5 or key_left:
                    self.selection_index = 0; moved = True # 同意
                elif axis_x > 0.5 or key_right:
                    self.selection_index = 1; moved = True # 拒绝

            if moved:
                self.last_axis_move = time.time()

    def handle_lobby_input(self, type, value):
        # A键 或 Enter
        if (type == 'kb_down' and value == pygame.K_RETURN) or (type == 'joy_down' and value == 0):
            player_list = list(self.found_players.items())
            if self.selection_index < len(player_list):
                ip, name = player_list[self.selection_index]
                self.opponent_addr = (ip, settings.PORT)
                self.network.send({'type': 'invite', 'name': settings.MY_USERNAME}, self.opponent_addr)
                self.game_mode = 'WAITING'
                self.popup_message = f"邀请 {name} 中..."
            else: # 返回主菜单
                self.game_mode = 'MENU'
        # B键 或 Escape
        elif (type == 'kb_down' and value == pygame.K_ESCAPE) or (type == 'joy_down' and value == 1):
            self.game_mode = 'MENU'

    def handle_pause_input(self, type, value):
        if not self.is_host: return
        # A键 或 Enter
        if (type == 'kb_down' and value == pygame.K_RETURN) or (type == 'joy_down' and value == 0):
            if self.selection_index == 0: # 继续
                self.game_mode = 'PLAYING'
                self.network.send({'type': 'resume'}, self.opponent_addr)
        # B键 或 Q
        elif (type == 'kb_down' and value == pygame.K_q) or (type == 'joy_down' and value == 1):
             if self.selection_index == 1: # 退出
                self.network.send({'type': 'quit'}, self.opponent_addr)
                self.reset_game_state()

    def handle_popup_input(self, type, value):
        # 导航在 handle_input 中处理
        # A键 或 Enter 确认选择
        if (type == 'kb_down' and value == pygame.K_RETURN) or (type == 'joy_down' and value == 0):
            if self.selection_index == 0: # 同意
                self.is_host = False
                self.opponent_addr = self.invitation['addr']
                self.network.send({'type': 'accept'}, self.opponent_addr)
                self.game_mode = 'PLAYING'
            else: # 拒绝
                self.network.send({'type': 'decline'}, self.invitation['addr'])
            self.invitation = None
        # B键 或 Escape 拒绝
        elif (type == 'kb_down' and value == pygame.K_ESCAPE) or (type == 'joy_down' and value == 1):
            self.network.send({'type': 'decline'}, self.invitation['addr'])
            self.invitation = None
    
    def handle_game_over_input(self, type, value):
        if self.my_choice: return

        # A键 或 Enter
        if (type == 'kb_down' and value == pygame.K_RETURN) or (type == 'joy_down' and value == 0):
            choice = 'rematch' if self.selection_index == 0 else 'quit'
            self.my_choice = choice
            self.network.send({'type': 'post_game_choice', 'choice': self.my_choice}, self.opponent_addr)
        # B键 或 Escape
        elif (type == 'kb_down' and value == pygame.K_ESCAPE) or (type == 'joy_down' and value == 1):
             self.my_choice = 'quit'
             self.network.send({'type': 'post_game_choice', 'choice': self.my_choice}, self.opponent_addr)

    # --- 网络消息处理 ---
    def handle_network(self):
        message = self.network.get_message()
        if not message: return
        
        msg_type = message['data'].get('type')
        addr = message['addr']
        
        if msg_type == 'discover':
            self.network.send({'type': 'discover_response', 'name': settings.MY_USERNAME}, addr)
        elif msg_type == 'discover_response':
            if addr[0] not in self.found_players and addr[0] != settings.MY_IP:
                self.found_players[addr[0]] = message['data'].get('name', 'Unknown')
        elif msg_type == 'invite' and not self.opponent_addr:
            self.invitation = {'addr': addr, 'name': message['data'].get('name', 'Unknown')}
            self.selection_index = 0
        elif msg_type == 'accept' and self.game_mode == 'WAITING':
            self.is_host = True
            self.game_mode = 'PLAYING'
            self.popup_message = None
        elif msg_type == 'decline' and self.game_mode == 'WAITING':
            self.reset_game_state()
            self.popup_message = "对方拒绝了你的邀请"
            self.popup_timer = time.time() + 3
        elif msg_type == 'game_state' and not self.is_host:
            state = message['data']['state']
            self.ball.set_pos(state['ball_x'], state['ball_y'])
            self.left_paddle.set_pos(state['p1_y'])
            self.score = state['score']
        elif msg_type == 'paddle_pos' and self.is_host:
            self.right_paddle.set_pos(message['data']['y'])
        elif msg_type == 'pause':
            if not self.is_host: self.game_mode = 'PAUSED'
        elif msg_type == 'resume':
            if not self.is_host: self.game_mode = 'PLAYING'
        elif msg_type == 'quit':
            self.reset_game_state()
            self.popup_message = "对方已断开连接"
            self.popup_timer = time.time() + 3
        elif msg_type == 'game_over' and not self.is_host:
            self.game_mode = 'GAME_OVER'
            self.winner = message['data'].get('winner')
            self.selection_index = 0
        elif msg_type == 'post_game_choice':
            self.opponent_choice = message['data'].get('choice')
        elif msg_type == 'rematch_accepted' and not self.is_host:
            self.score = {'p1': 0, 'p2': 0}
            self.ball.reset(1)
            self.my_choice = None
            self.opponent_choice = None
            self.game_mode = 'PLAYING'
        elif msg_type == 'back_to_lobby':
            self.reset_game_state()

            
    # --- 游戏逻辑更新 ---
    def update(self, dt):
        if self.game_mode == 'LOBBY':
            if time.time() - self.last_broadcast_time > 2:
                self.network.broadcast({'type': 'discover', 'name': settings.MY_USERNAME})
                self.last_broadcast_time = time.time()
        elif self.game_mode == 'PLAYING':
            keys = pygame.key.get_pressed()
            # P1 (Host) 控制
            if self.is_host:
                p1_dy = 0
                if keys[pygame.K_w]: p1_dy = -1
                if keys[pygame.K_s]: p1_dy = 1
                if self.joysticks: p1_dy += self.joysticks[0].get_axis(1)
                self.left_paddle.move(p1_dy, dt)
            # P2 (Client) 控制
            else:
                p2_dy = 0
                if keys[pygame.K_UP]: p2_dy = -1
                if keys[pygame.K_DOWN]: p2_dy = 1
                if self.joysticks:
                    if self.joysticks[0].get_numaxes() > 3:
                        p2_dy += self.joysticks[0].get_axis(3) # 右摇杆Y
                self.right_paddle.move(p2_dy, dt)
                self.network.send({'type': 'paddle_pos', 'y': self.right_paddle.rect.y}, self.opponent_addr)
            
            # 主机端物理计算
            if self.is_host:
                self.ball.move(dt)
                if self.ball.rect.top <= 0 or self.ball.rect.bottom >= settings.HEIGHT: self.ball.speed_y *= -1
                if self.ball.rect.colliderect(self.left_paddle.rect) and self.ball.speed_x < 0: self.ball.speed_x *= -1.05
                if self.ball.rect.colliderect(self.right_paddle.rect) and self.ball.speed_x > 0: self.ball.speed_x *= -1.05
                if self.ball.rect.left <= 0: self.score['p2'] += 1; self.ball.reset(1)
                if self.ball.rect.right >= settings.WIDTH: self.score['p1'] += 1; self.ball.reset(-1)
                
                if self.score['p1'] >= settings.WINNING_SCORE or self.score['p2'] >= settings.WINNING_SCORE:
                    self.game_mode = 'GAME_OVER'
                    self.selection_index = 0
                    self.winner = "P1" if self.score['p1'] > self.score['p2'] else "P2"
                    self.network.send({'type': 'game_over', 'winner': self.winner}, self.opponent_addr)
                else:
                    game_state_data = {
                        'ball_x': self.ball.rect.centerx, 'ball_y': self.ball.rect.centery,
                        'p1_y': self.left_paddle.rect.y, 'score': self.score,
                    }
                    self.network.send({'type': 'game_state', 'state': game_state_data}, self.opponent_addr)

        elif self.game_mode == 'PAUSED' and self.is_host:
            self.network.send({'type': 'pause'}, self.opponent_addr)
        
        elif self.game_mode == 'GAME_OVER':
            # 只有主机负责处理双方选择后的逻辑
            if self.is_host and self.my_choice and self.opponent_choice:
                if self.my_choice == 'rematch' and self.opponent_choice == 'rematch':
                    # 主机重置状态
                    self.score = {'p1': 0, 'p2': 0}
                    self.ball.reset()
                    self.my_choice = None
                    self.opponent_choice = None
                    self.game_mode = 'PLAYING'
                    # 通知客户端也重置
                    self.network.send({'type': 'rematch_accepted'}, self.opponent_addr)
                else: # 任意一方选择退出
                    self.network.send({'type': 'back_to_lobby'}, self.opponent_addr)
                    self.reset_game_state()


    # --- 渲染 ---
    def draw(self):
        settings.WINDOW.fill(settings.BLACK)
        
        if self.game_mode == 'LOBBY': self.draw_lobby()
        elif self.game_mode in ['PLAYING', 'PAUSED', 'GAME_OVER']: self.draw_game_scene()
        elif self.game_mode == 'WAITING': ui_elements.draw_text(self.popup_message, settings.FONT_M, settings.WHITE, settings.WINDOW, settings.WIDTH/2, settings.HEIGHT/2)

        if self.game_mode == 'PAUSED': self.draw_pause_menu()
        if self.game_mode == 'GAME_OVER': self.draw_game_over()
        if self.invitation: self.draw_invitation_popup()
        if self.popup_message and time.time() < self.popup_timer:
            ui_elements.draw_text(self.popup_message, settings.FONT_M, settings.WHITE, settings.WINDOW, settings.WIDTH/2, settings.HEIGHT - 40)
    
    def draw_lobby(self):
        ui_elements.draw_text("局域网大厅", settings.FONT_L, settings.WHITE, settings.WINDOW, settings.WIDTH/2, 50)
        player_list = list(self.found_players.items())
        if not player_list:
            ui_elements.draw_text("正在扫描局域网内的玩家...", settings.FONT_S, settings.GRAY, settings.WINDOW, settings.WIDTH/2, settings.HEIGHT/2 - 20)
        
        num_options = len(player_list) + 1
        self.selection_index %= num_options
        for i, (ip, name) in enumerate(player_list):
            ui_elements.draw_button(f"{name}", settings.FONT_S, settings.WINDOW, pygame.Rect(settings.WIDTH/2 - 125, 120 + i*40, 250, 35), self.selection_index, i)
        ui_elements.draw_button("返回", settings.FONT_M, settings.WINDOW, pygame.Rect(settings.WIDTH/2-100, settings.HEIGHT - 60, 200, 40), self.selection_index, len(player_list))

    def draw_game_scene(self):
        pygame.draw.aaline(settings.WINDOW, settings.GRAY, (settings.WIDTH // 2, 0), (settings.WIDTH // 2, settings.HEIGHT))
        self.left_paddle.draw(settings.WINDOW)
        self.right_paddle.draw(settings.WINDOW)
        self.ball.draw(settings.WINDOW)
        ui_elements.draw_text(f"P1", settings.FONT_M, settings.WHITE, settings.WINDOW, settings.WIDTH / 4, 20)
        ui_elements.draw_text(f"{self.score['p1']}", settings.FONT_L, settings.WHITE, settings.WINDOW, settings.WIDTH / 4, 60)
        ui_elements.draw_text(f"P2", settings.FONT_M, settings.WHITE, settings.WINDOW, settings.WIDTH * 3 / 4, 20)
        ui_elements.draw_text(f"{self.score['p2']}", settings.FONT_L, settings.WHITE, settings.WINDOW, settings.WIDTH * 3 / 4, 60)

    def draw_pause_menu(self):
        overlay = pygame.Surface((settings.WIDTH, settings.HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 180)); settings.WINDOW.blit(overlay, (0,0))
        ui_elements.draw_text("游戏暂停", settings.FONT_L, settings.WHITE, settings.WINDOW, settings.WIDTH/2, settings.HEIGHT/4)
        if self.is_host:
            self.selection_index %= 2
            ui_elements.draw_button("继续游戏 (A键/Enter)", settings.FONT_M, settings.WINDOW, pygame.Rect(settings.WIDTH/2-125, 150, 250, 40), self.selection_index, 0)
            ui_elements.draw_button("退出到大厅 (B键/Q)", settings.FONT_M, settings.WINDOW, pygame.Rect(settings.WIDTH/2-125, 200, 250, 40), self.selection_index, 1)
        else:
            ui_elements.draw_text("等待主机继续游戏...", settings.FONT_M, settings.GRAY, settings.WINDOW, settings.WIDTH/2, settings.HEIGHT/2)

    def draw_invitation_popup(self):
        overlay = pygame.Surface((settings.WIDTH, settings.HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 200)); settings.WINDOW.blit(overlay, (0, 0))
        box_rect = pygame.Rect(settings.WIDTH/4, settings.HEIGHT/4, settings.WIDTH/2, settings.HEIGHT/2)
        pygame.draw.rect(settings.WINDOW, settings.DARK_GRAY, box_rect, border_radius=15)
        pygame.draw.rect(settings.WINDOW, settings.WHITE, box_rect, 2, border_radius=15)
        ui_elements.draw_text("收到游戏邀请", settings.FONT_M, settings.WHITE, settings.WINDOW, settings.WIDTH/2, box_rect.y + 25)
        ui_elements.draw_text(f"来自: {self.invitation['name']}", settings.FONT_S, settings.GRAY, settings.WINDOW, settings.WIDTH/2, box_rect.y + 60)
        self.selection_index %= 2
        button_width = (box_rect.width / 2) - 20
        ui_elements.draw_button("同意 (A键)", settings.FONT_S, settings.WINDOW, pygame.Rect(box_rect.x + 15, box_rect.y + 100, button_width, 40), self.selection_index, 0)
        ui_elements.draw_button("拒绝 (B键)", settings.FONT_S, settings.WINDOW, pygame.Rect(box_rect.right - button_width - 15, box_rect.y + 100, button_width, 40), self.selection_index, 1)

    def draw_game_over(self):
        overlay = pygame.Surface((settings.WIDTH, settings.HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 180)); settings.WINDOW.blit(overlay, (0,0))
        winner_text = self.winner or ("P1" if self.score['p1'] > self.score['p2'] else "P2")
        ui_elements.draw_text("游戏结束", settings.FONT_L, settings.WHITE, settings.WINDOW, settings.WIDTH/2, 60)
        ui_elements.draw_text(f"玩家 {winner_text} 胜利!", settings.FONT_M, settings.GREEN, settings.WINDOW, settings.WIDTH/2, 110)
        
        if self.my_choice:
            my_choice_map = {'rematch': '再玩一局', 'quit': '返回大厅'}
            opp_choice_map = {'rematch': '对方选择再玩一局', 'quit': '对方选择返回大厅', None: '等待对方选择...'}
            
            ui_elements.draw_text(f"你选择了: {my_choice_map[self.my_choice]}", settings.FONT_S, settings.WHITE, settings.WINDOW, settings.WIDTH/2, 160)
            ui_elements.draw_text(opp_choice_map[self.opponent_choice], settings.FONT_S, settings.GRAY, settings.WINDOW, settings.WIDTH/2, 190)
        else:
            self.selection_index %= 2
            ui_elements.draw_button("再玩一局 (A键)", settings.FONT_M, settings.WINDOW, pygame.Rect(settings.WIDTH/2 - 125, 160, 250, 40), self.selection_index, 0)
            ui_elements.draw_button("返回大厅 (B键)", settings.FONT_M, settings.WINDOW, pygame.Rect(settings.WIDTH/2 - 125, 210, 250, 40), self.selection_index, 1)


def run_online_mode():
    """初始化并运行在线游戏模式。"""
    game = OnlineGame()
    game.run()

