# system/icon_manager.py
import json
import os
from system.config import CONFIG_FILE
from system.desktop_icon import DesktopIcon

class IconManager:
    def __init__(self, app):
        self.app = app
        self.icons = {}
        self.load_and_create_icons()
        
    def load_layout(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("配置文件格式错误，将使用默认布局。")
                return self.get_default_layout()
        else:
            return self.get_default_layout()
            
    def get_default_layout(self):
        return [
            {"id": "terminal", "text": "终端", "icon": "icons/terminal.png", "x": 80, "y": 80},
            {"id": "browser", "text": "浏览器", "icon": "icons/browser.png", "x": 180, "y": 80},
            {"id": "files", "text": "文件管理器", "icon": "icons/folder.png", "x": 80, "y": 180},
            {"id": "editor", "text": "文本编辑器", "icon": "icons/editor.png", "x": 180, "y": 180},
        ]
        
    def save_layout(self):
        layout_data = []
        for icon_id, icon_instance in self.icons.items():
            layout_data.append({
                "id": icon_instance.id,
                "text": icon_instance.label_text,
                "icon": icon_instance.image_path,
                "x": icon_instance.x,
                "y": icon_instance.y
            })
        with open(CONFIG_FILE, 'w') as f:
            json.dump(layout_data, f, indent=4)
        self.app.ui.set_status_text("布局已保存")
        
    def load_and_create_icons(self):
        icon_layout = self.load_layout()
        for icon_data in icon_layout:
            icon_instance = DesktopIcon(self.app, self.app.ui.canvas, icon_data)
            self.icons[icon_data['id']] = icon_instance
            
    def update_icon_position(self, icon_id, x, y):
        if icon_id in self.icons:
            self.icons[icon_id].x = x
            self.icons[icon_id].y = y
            self.save_layout()