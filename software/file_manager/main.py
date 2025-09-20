import sys
import tkinter as tk
from pathlib import Path

# 导入配置文件，注意路径需要适应新的结构
current_file_path = Path(__file__).resolve()
project_root = current_file_path.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from system.config import WINDOW_WIDTH, WINDOW_HEIGHT

# 使用相对导入解决 Pylance 报错
from .ui_manager import UIManager
from .logic_manager import LogicManager
from .icon_loader import IconLoader

class FileManagerApp:
    def __init__(self, master):
        self.master = master
        self.master.title("文件管理器")
        self.master.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        
        # 实例化图标加载器
        self.icon_loader = IconLoader()
        self.icon_references = self.icon_loader.load_icons()
        self.property_window_icon = None # 确保属性窗口的图标不被回收
        self.photo_image_references = [] # 防止图片被垃圾回收

        # 实例化UI和逻辑管理器，并传入必要的参数
        self.ui_manager = UIManager(self.master, self.icon_references)
        self.logic_manager = LogicManager(self, self.ui_manager.tree, self.ui_manager.path_var)
        
        # 将逻辑方法绑定到UI事件
        self.ui_manager.bind_commands({
            'refresh': self.logic_manager.refresh,
            'go_back': self.logic_manager.go_back,
            'go_forward': self.logic_manager.go_forward,
            'copy': self.logic_manager.copy_item,
            'paste': self.logic_manager.paste_item,
            'delete': self.logic_manager.delete_item,
            'properties': self.logic_manager.show_properties,
            'new_folder': self.logic_manager.create_new_folder,
            'sort_name': self.logic_manager.sort_by_name,
            'sort_category': self.logic_manager.sort_by_category,
            'sort_date': self.logic_manager.sort_by_date,
            'sort_size': self.logic_manager.sort_by_size,
            'on_double_click': self.logic_manager.on_double_click,
        })
        
        # 初始填充列表
        self.logic_manager.populate_file_list(Path.home())

if __name__ == '__main__':
    root = tk.Tk()
    app = FileManagerApp(root)
    root.mainloop()