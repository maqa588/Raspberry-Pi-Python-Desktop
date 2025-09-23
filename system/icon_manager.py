# system/icon_manager.py
import json
import os
# 从新的模块导入加载和保存函数
from system.platformdirs_pack import load_user_config, save_user_config
from system.desktop_icon import DesktopIcon

class IconManager:
    def __init__(self, app):
        self.app = app
        self.icons = {}
        self.background_color = "#66ccff"
        self.label_color = "black" # 新增: 图标文字颜色
        self.load_and_create_icons()
        
    def load_and_create_icons(self):
        """从用户或默认配置文件加载图标布局、背景颜色和文字颜色"""
        layout_data = load_user_config("desktop_layout.json")

        # 加载背景颜色
        self.background_color = layout_data.get('background_color', "#3498db")
        self.app.ui.canvas.config(bg=self.background_color)
        
        # 新增: 加载图标文字颜色
        self.label_color = layout_data.get('label_color', "black")
        
        # 加载图标布局，如果配置文件中没有则使用默认布局
        icon_layout = layout_data.get('icons', self._get_default_layout())
        for icon_data in icon_layout:
            icon_instance = DesktopIcon(self.app, self.app.ui.canvas, icon_data)
            self.icons[icon_data['id']] = icon_instance
            # 新增: 在创建图标后，立即更新其文字颜色
            icon_instance.set_label_color(self.label_color)

    @staticmethod
    def _get_default_layout():
        """定义默认的图标布局"""
        # 注意：因为是静态方法，所以方法签名里没有 self
        return [
            {"id": "terminal", "text": "终端", "icon": "icons/terminal.png", "x": 60, "y": 60},
            {"id": "browser", "text": "浏览器", "icon": "icons/browser.png", "x": 140, "y": 60},
            {"id": "files", "text": "文件管理器", "icon": "icons/folder.png", "x": 60, "y": 140},
            {"id": "editor", "text": "文本编辑器", "icon": "icons/editor.png", "x": 140, "y": 140},
            {"id": "camera", "text": "相机", "icon": "icons/camera.png", "x": 220, "y": 60},
            {"id": "deepseek", "text": "Deepseek", "icon": "icons/deepseek.png", "x": 220, "y": 140},
            {"id": "games", "text": "游戏", "icon": "icons/game.png", "x": 300, "y": 60},
        ]

    def save_layout(self):
        """将当前所有图标的位置、背景颜色和文字颜色保存到用户配置文件"""
        layout_data = {
            "background_color": self.background_color,
            "label_color": self.label_color,
            "icons": []
        }
        for icon_id, icon_instance in self.icons.items():
            layout_data["icons"].append({
                "id": icon_instance.id,
                "text": icon_instance.label_text,
                "icon": icon_instance.image_path,
                "x": icon_instance.x,
                "y": icon_instance.y
            })
        
        save_user_config(layout_data, "desktop_layout.json")
    
        self.app.ui.set_status_text("布局已保存")
        self.app.root.after(1000, self.set_status_ready)

    def set_status_ready(self):
        """设置状态文本为“就绪”的辅助方法"""
        self.app.ui.set_status_text("就绪")
        
    def update_icon_position(self, icon_id, x, y):
        """当图标移动后，更新其位置并触发保存"""
        if icon_id in self.icons:
            self.icons[icon_id].x = x
            self.icons[icon_id].y = y
            self.save_layout()

    def save_background_color(self, color):
        """单独保存背景颜色，并触发布局保存"""
        self.background_color = color
        self.save_layout()

    # 新增: 保存文字颜色，并更新所有图标
    def save_label_color(self, color):
        """单独保存文字颜色，并更新所有图标的颜色"""
        self.label_color = color
        for icon_id, icon_instance in self.icons.items():
            icon_instance.set_label_color(color)
        self.save_layout()