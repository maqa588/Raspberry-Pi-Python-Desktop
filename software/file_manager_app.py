import os
import sys

# --- 自动添加项目根目录到搜索路径 (解决方法二) ---
current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file_path))
sys.path.insert(0, project_root)
# --- 添加结束 ---

from PIL import Image, ImageTk
import platform
import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from system.config import WINDOW_WIDTH, WINDOW_HEIGHT
from system.button.about import show_system_about, show_developer_about

class FileManagerApp:
    def __init__(self, master):
        self.master = master
        self.master.title("文件管理器")
        # 您可以根据需要在这里覆盖导入的配置
        # self.master.geometry(f"480x{WINDOW_HEIGHT}")
        self.master.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        self.current_path = Path.home()
        self.history = [self.current_path]
        self.history_index = 0
        self.icon_references = {}
        self.photo_image_references = []

        self.load_icons()
        self.create_menu()
        self.create_widgets()
        self.populate_file_list(self.current_path)

    def load_icons(self):
        """加载所有需要的图标并存储"""
        icon_names = {
            "folder": "folder.png", "music": "music.png", "photo": "photo.png",
            "video": "video.png", "file": "file.png", "editor": "editor.png",
            "browser": "browser.png"
        }
        icon_path = Path(__file__).parent.parent / "icons"
        for name, filename in icon_names.items():
            try:
                img = Image.open(icon_path / filename).resize((16, 16), Image.Resampling.LANCZOS)
                self.icon_references[name] = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"警告: 加载图标 {filename} 失败: {e}")
                self.icon_references[name] = None

    def create_menu(self):
        """创建顶部菜单栏"""
        self.menubar = tk.Menu(self.master)
        self.master.config(menu=self.menubar)
        # --- 关于菜单 ---
        about_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="关于", menu=about_menu)
        about_menu.add_command(label="系统信息", command=lambda: show_system_about(self.master))
        about_menu.add_command(label="关于开发者", command=lambda: show_developer_about(self.master))
        about_menu.add_separator()
        about_menu.add_command(label="退出", command=self.master.quit)
        # --- 文件菜单 ---
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="复制", command=self.show_not_implemented)
        file_menu.add_command(label="粘贴", command=self.show_not_implemented)
        file_menu.add_command(label="查看属性", command=self.show_not_implemented)
        file_menu.add_command(label="删除", command=self.show_not_implemented)
        file_menu.add_separator()
        file_menu.add_command(label="新建文件夹", command=self.create_new_folder)
        # --- 格式菜单 ---
        format_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="格式", menu=format_menu)
        format_menu.add_command(label="修改排列格式", command=self.show_not_implemented)
        # --- 导航按钮 ---
        self.menubar.add_command(label="向后", command=self.go_back)
        self.menubar.add_command(label="向前", command=self.go_forward)
        self.menubar.add_command(label="刷新", command=self.refresh)

    def create_widgets(self):
        """创建文件列表视图，并调整列宽以适应窄屏幕"""
        self.path_var = tk.StringVar(value=str(self.current_path))
        path_entry = ttk.Entry(self.master, textvariable=self.path_var, state='readonly')
        path_entry.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建框架来包含Treeview和滚动条
        tree_frame = tk.Frame(self.master)
        tree_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        
        self.tree = ttk.Treeview(tree_frame, columns=("name", "modified"), show="headings")
        self.tree.heading("name", text="名称")
        self.tree.heading("modified", text="修改时间")

        # --- 关键修改：调整列宽以适应 480px 屏幕 ---
        # 假设总宽度480，减去边距和滚动条约30，剩余450
        # 图标列宽度为30
        # 名称列和修改时间列分配剩余的420
        self.tree.column("#0", width=30, stretch=tk.NO) # 图标列
        self.tree.column("name", width=280)             # 名称列
        self.tree.column("modified", width=140)         # 修改时间列

        # 创建垂直滚动条
        self.v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.v_scrollbar.set)
        
        # 使用grid布局来放置Treeview和滚动条
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # 配置grid权重，使Treeview可以扩展
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        self.tree.bind("<Double-1>", self.on_double_click)

    def get_file_category(self, filename: str) -> str:
        """根据文件扩展名返回分类名称"""
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        if ext in ['mp3', 'wav', 'flac', 'aac']: return "音乐"
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'svg']: return "图片"
        if ext in ['mp4', 'mov', 'avi', 'mkv', 'wmv']: return "视频"
        if ext in ['txt', 'md', 'py', 'json', 'xml', 'log', 'ini', 'cfg', 'pdf', 'doc', 'docx', 'xls', 'xlsx']: return "文档"
        if ext in ['html', 'htm', 'css', 'js']: return "网页"
        if ext in ['zip', 'rar', 'gz', '7z']: return "压缩包"
        return "其他"

    def populate_file_list(self, path: Path):
        """填充文件列表，并按类型分组"""
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.photo_image_references.clear()

        self.current_path = path
        self.path_var.set(str(self.current_path))
        self.master.title(f"文件管理器 - {self.current_path.name}")

        # --- 关键修改：文件分类逻辑 ---
        categories = {
            "文件夹": [], "图片": [], "音乐": [], "视频": [],
            "文档": [], "网页": [], "压缩包": [], "其他": []
        }

        try:
            for entry in os.scandir(path):
                if entry.is_dir():
                    categories["文件夹"].append(entry)
                else:
                    category_name = self.get_file_category(entry.name)
                    categories[category_name].append(entry)
        except PermissionError:
            messagebox.showwarning("权限错误", f"无法访问目录：\n{path}")
            self.go_back(is_error=True)
            return
        except Exception as e:
            messagebox.showerror("错误", f"无法读取目录内容: {e}")
            return

        # 插入 ".." 以返回上一级目录
        if path.parent != path:
            self.tree.insert("", "end", text="", values=("..", "上一级", ""), image=self.icon_references.get("folder"), tags=('real_dir',))

        # 按分类顺序插入到 Treeview
        for category_name, items in categories.items():
            if not items:
                continue

            # 插入分类的父节点
            category_node = self.tree.insert("", "end", text="", values=(category_name, "分类", ""), image=self.icon_references.get("folder"), open=False)

            # 排序后插入子节点
            items.sort(key=lambda e: e.name.lower())
            for item in items:
                try:
                    stat = item.stat()
                    modified_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                    
                    is_dir = item.is_dir()
                    # 如果是真实文件夹，使用folder图标，否则根据文件类型获取图标
                    icon_key = "folder" if is_dir else self.get_icon_key_for_file(item.name)
                    photo_image = self.icon_references.get(icon_key, self.icon_references.get("file"))
                    self.photo_image_references.append(photo_image)
                    
                    # 使用 tag 来区分真实文件夹和虚拟分类
                    item_tags = ('real_dir',) if is_dir else ()
                    self.tree.insert(category_node, "end", text="", values=(item.name, modified_time), image=photo_image, tags=item_tags)
                except OSError:
                    continue

    def get_icon_key_for_file(self, filename: str) -> str:
        """根据文件名返回图标对应的key (与load_icons中的key一致)"""
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        if ext in ['mp3', 'wav', 'flac', 'aac']: return "music"
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']: return "photo"
        if ext in ['mp4', 'mov', 'avi', 'mkv', 'wmv']: return "video"
        if ext in ['txt', 'md', 'py', 'json', 'xml', 'log', 'ini', 'cfg', 'pdf', 'doc', 'docx']: return "editor"
        if ext in ['html', 'htm', 'css', 'js', 'svg']: return "browser"
        return "file"
        
    def on_double_click(self, event):
        """处理双击事件，只对真实文件夹和'..'进行导航"""
        item_id = self.tree.identify_row(event.y)
        if not item_id: return

        item = self.tree.item(item_id)
        name = item['values'][0]

        # --- 关键修改：只处理真实目录的导航 ---
        # 检查是否是 '..' 或者被标记为真实文件夹的项
        is_real_folder = 'real_dir' in item['tags']
        is_parent_dir = name == ".."

        if is_parent_dir:
            new_path = self.current_path.parent
            if new_path != self.current_path:
                self.navigate_to(new_path)
            return

        if is_real_folder:
            new_path = self.current_path / name
            # 再次确认路径确实是目录，避免符号链接等问题
            if new_path.is_dir():
                self.navigate_to(new_path)

    def navigate_to(self, path: Path):
        """导航到新路径并更新历史记录"""
        self.populate_file_list(path)
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        if self.history[-1] != path:
            self.history.append(path)
        self.history_index = len(self.history) - 1

    def go_back(self, is_error=False):
        """导航到历史记录中的上一个文件夹"""
        if is_error and self.history_index > 0:
            self.history.pop()
            self.history_index -= 1
            self.populate_file_list(self.history[self.history_index])
            return
        if self.history_index > 0:
            self.history_index -= 1
            self.populate_file_list(self.history[self.history_index])

    def go_forward(self):
        """导航到历史记录中的下一个文件夹"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.populate_file_list(self.history[self.history_index])

    def refresh(self):
        """刷新当前目录视图"""
        self.populate_file_list(self.current_path)

    def create_new_folder(self):
        folder_name = simpledialog.askstring("新建文件夹", "请输入文件夹名称:")
        if folder_name:
            try:
                os.makedirs(self.current_path / folder_name)
                self.refresh()
            except FileExistsError:
                messagebox.showerror("错误", f"文件夹 '{folder_name}' 已存在。")
            except Exception as e:
                messagebox.showerror("错误", f"创建文件夹失败: {e}")

    def show_not_implemented(self):
        messagebox.showinfo("提示", "该功能尚未实现。")

if __name__ == '__main__':
    root = tk.Tk()
    app = FileManagerApp(root)
    root.mainloop()
