import pygame
import settings

def draw_text(text, font, color, surface, x, y, center=True):
    """在屏幕上绘制文本"""
    text_obj = font.render(text, True, color)
    text_rect = text_obj.get_rect()
    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    surface.blit(text_obj, text_rect)
    return text_rect

def draw_button(text, font, surface, rect, selection_index, button_index):
    """绘制一个可交互的按钮"""
    is_selected = selection_index == button_index
    color = settings.BLUE if is_selected else settings.DARK_GRAY
    pygame.draw.rect(surface, color, rect, border_radius=10)
    pygame.draw.rect(surface, settings.WHITE, rect, 2, border_radius=10) # 边框
    draw_text(text, font, settings.WHITE, surface, rect.centerx, rect.centery)
