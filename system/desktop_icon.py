# desktop_icon.py
import tkinter as tk
from PIL import Image, ImageTk
import os
from system.CreatePlaceholderIcon import create_placeholder_icon
from system.config import get_resource_path # 导入新函数

class DesktopIcon:
    """管理单个桌面图标的类"""
    def __init__(self, app, canvas, icon_data):
        self.app = app
        self.canvas = canvas
        self.id = icon_data['id']
        self.label_text = icon_data['text']
        self.image_path = icon_data['icon']
        self.x = icon_data['x']
        self.y = icon_data['y']
        self.double_click_command = self.app.get_command_for_icon(self.id)

        create_placeholder_icon(self.image_path, text=self.id[:3].upper())

        full_image_path = get_resource_path(self.image_path)
        self.pil_image = Image.open(full_image_path).resize((48, 48), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.pil_image)

        self.image_item = self.canvas.create_image(self.x, self.y, image=self.tk_image, anchor=tk.CENTER)
        self.text_item = self.canvas.create_text(self.x, self.y + 35, text=self.label_text, fill="white", font=("Arial", 9))
        
        self.tag = f"icon_{self.id}"
        self.canvas.addtag_withtag(self.tag, self.image_item)
        self.canvas.addtag_withtag(self.tag, self.text_item)
        
        self.canvas.tag_bind(self.tag, "<Double-1>", self.on_double_click)
        self.canvas.tag_bind(self.tag, "<ButtonPress-1>", self.on_press)
        self.canvas.tag_bind(self.tag, "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind(self.tag, "<ButtonRelease-1>", self.on_release)
        
        self._drag_data = {"x": 0, "y": 0}

    def on_double_click(self, event):
        """处理双击事件"""
        if self.double_click_command:
            self.double_click_command()

    def on_press(self, event):
        """记录点击的起始位置"""
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def on_drag(self, event):
        """计算位移并移动图标"""
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        self.canvas.move(self.tag, dx, dy)
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def on_release(self, event):
        """释放鼠标后，更新图标最终坐标并保存"""
        coords = self.canvas.coords(self.image_item)
        self.x = coords[0]
        self.y = coords[1]
        self.app.update_icon_position(self.id, self.x, self.y)