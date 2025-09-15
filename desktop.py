import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw
import subprocess
import platform
import json
import os
import time

from system.terminal import open_terminal_system
from system.terminal import create_placeholder_icon

# --- 配置 ---
CONFIG_FILE = 'desktop_layout.json'
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 320
# 画布的虚拟大小，大于窗口尺寸以实现滚动效果
CANVAS_WIDTH = 800
CANVAS_HEIGHT = 600

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
        # 这是一个占位函数，您需要在这里定义双击图标时执行的操作
        self.double_click_command = self.app.get_command_for_icon(self.id)

        # 确保图标存在
        create_placeholder_icon(self.image_path, text=self.id[:3].upper())

        # 加载并保持对PhotoImage的引用，防止被垃圾回收
        self.pil_image = Image.open(self.image_path).resize((48, 48), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.pil_image)

        # 在Canvas上创建图像和文字
        self.image_item = self.canvas.create_image(self.x, self.y, image=self.tk_image, anchor=tk.CENTER)
        self.text_item = self.canvas.create_text(self.x, self.y + 35, text=self.label_text, fill="white", font=("Arial", 9))
        
        # 使用标签将图像和文本组合在一起，方便一起移动
        self.tag = f"icon_{self.id}"
        self.canvas.addtag_withtag(self.tag, self.image_item)
        self.canvas.addtag_withtag(self.tag, self.text_item)
        
        # 绑定事件
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
        # 获取图标中心的新坐标
        coords = self.canvas.coords(self.image_item)
        self.x = coords[0]
        self.y = coords[1]
        self.app.update_icon_position(self.id, self.x, self.y)


class DesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Raspberry Pi Desktop")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        
        self.icons = {} # 存储所有DesktopIcon实例

        status_frame = tk.Frame(self.root, bd=1, relief="sunken")
        status_frame.pack(side="bottom", fill="x")

        self.status_text = tk.Label(status_frame, text="已准备", anchor="w")
        self.status_text.pack(side="left", padx=(5,0))
        self._status_reset_after_id = None

        self.time_label = tk.Label(status_frame, text="", anchor="e")
        self.time_label.pack(side="right", padx=(0,5))

        self.create_menu()
        self.create_desktop_canvas()
        self.load_and_create_icons()
        self.update_clock()
        
    def update_clock(self):
        now = time.strftime("%H:%M:%S")
        self.time_label.config(text=now)
        # 调用自身，每 1000 毫秒一次
        self.time_label.after(1000, self.update_clock)

    def create_menu(self):
        """创建顶部菜单栏"""
        menubar = tk.Menu(self.root)
        
        # --- 文件菜单 ---
        file_menu = tk.Menu(menubar, tearoff=0)
        # 在这里为您留出接口，您可以替换为您自己的函数
        file_menu.add_command(label="新文件", command=self.menu_placeholder_function)
        file_menu.add_command(label="打开", command=self.menu_placeholder_function)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)

        # --- 编辑菜单 ---
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="设置", command=self.menu_placeholder_function)
        menubar.add_cascade(label="编辑", menu=edit_menu)

        self.root.config(menu=menubar)

    def create_desktop_canvas(self):
        """创建作为桌面的画布"""
        self.canvas = tk.Canvas(self.root, bg="#3498db", scrollregion=(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT))
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 绑定背景拖动事件
        self.canvas.bind("<ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.pan_view)

    def start_pan(self, event):
        """开始平移桌面前的准备"""
        # 检查是否点击在图标上，如果是，则不进行平移
        if not self.canvas.find_withtag(tk.CURRENT):
             self.canvas.scan_mark(event.x, event.y)

    def pan_view(self, event):
        """平移画布视图"""
        if not self.canvas.find_withtag(tk.CURRENT):
            self.canvas.scan_dragto(event.x, event.y, gain=1)
            
    def load_layout(self):
        """从JSON文件加载图标布局，如果文件不存在则返回默认布局"""
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
        """定义默认的图标布局"""
        return [
            {"id": "terminal", "text": "终端", "icon": "icons/terminal.png", "x": 80, "y": 80},
            {"id": "browser", "text": "浏览器", "icon": "icons/browser.png", "x": 180, "y": 80},
            {"id": "files", "text": "文件管理器", "icon": "icons/folder.png", "x": 80, "y": 180},
            {"id": "editor", "text": "文本编辑器", "icon": "icons/editor.png", "x": 180, "y": 180},
        ]
        
    def save_layout(self):
        """将当前所有图标的位置保存到JSON文件"""
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
        self.status_text.config(text="布局已保存")
        
    def load_and_create_icons(self):
        """加载布局并在桌面上创建所有图标"""
        icon_layout = self.load_layout()
        for icon_data in icon_layout:
            icon_instance = DesktopIcon(self, self.canvas, icon_data)
            self.icons[icon_data['id']] = icon_instance
            
    def update_icon_position(self, icon_id, x, y):
        """当图标移动后，更新其位置并触发保存"""
        if icon_id in self.icons:
            self.icons[icon_id].x = x
            self.icons[icon_id].y = y
            self.save_layout()

    # --- 留给您实现的接口 ---
    
    def menu_placeholder_function(self):
        """菜单项的占位符函数"""
        messagebox.showinfo("提示", "此菜单功能待实现！")

    def get_command_for_icon(self, icon_id):
        """
        根据图标ID返回对应的双击执行函数。
        这是您需要重点编写的逻辑接口。
        """
        if icon_id == "terminal":
            return self.open_terminal
        elif icon_id == "browser":
            return self.open_browser
        elif icon_id == "files":
            return self.open_file_manager
        elif icon_id == "editor":
            return self.open_editor
        # ...可以为其他图标添加更多逻辑
        else:
            # 默认的占位操作
            return lambda: messagebox.showinfo("操作", f"双击了图标: {icon_id}\n请在此处实现您的功能！")

    # --- 您可以实现的具体操作 ---

    def open_reset(self):
        # 如果之前有安排重置状态的任务，就取消
        if hasattr(self, "_status_reset_after_id") and self._status_reset_after_id is not None:
            self.root.after_cancel(self._status_reset_after_id)
        # 安排 3 秒后重置状态为 "已准备"
        self._status_reset_after_id = self.root.after(3000, lambda: self.status_text.config(text="就绪"))

    def open_terminal(self):
        """打开终端的操作逻辑（委托给 system/terminal.py）"""
        print("执行打开终端的操作...")
        success = open_terminal_system()
        if success:
            self.status_text.config(text="终端已启动")
            self.open_reset()
        else:
            self.status_text.config(text="打开终端失败")
            self.open_reset()

    def open_browser(self):
        """打开浏览器的操作逻辑"""
        print("执行打开浏览器的操作...")
        messagebox.showinfo("操作", "正在打开浏览器...")
        # os.system('chromium-browser &')

    def open_file_manager(self):
        """打开文件管理器的操作逻辑"""
        print("执行打开文件管理器的操作...")
        messagebox.showinfo("操作", "正在打开文件管理器...")
        # os.system('pcmanfm &')

    def open_editor(self):
        """打开文件管理器的操作逻辑"""
        print("执行打开文件编辑器的操作...")
        messagebox.showinfo("操作", "正在打开文件管理器...")
        # os.system('pcmanfm &')


if __name__ == "__main__":
    root = tk.Tk()
    app = DesktopApp(root)
    root.mainloop()