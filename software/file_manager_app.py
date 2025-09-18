import os
import sys

current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file_path))
sys.path.insert(0, project_root)

import subprocess
from PIL import Image, ImageTk
import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
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
        """用自定义顶部栏替换 Tkinter 菜单栏"""
        # 创建一个 Frame 作为自定义顶部栏的容器
        top_bar_frame = tk.Frame(self.master, bg="lightgray", height=30)
        top_bar_frame.pack(side=tk.TOP, fill=tk.X)

        # --- 关于菜单 ---
        about_mb = tk.Menubutton(top_bar_frame, text="关于", activebackground="gray", bg="lightgray")
        about_mb.pack(side=tk.LEFT, padx=5)
        about_menu = tk.Menu(about_mb, tearoff=0)
        about_menu.add_command(label="系统信息", command=lambda: show_system_about(self.master))
        about_menu.add_command(label="关于开发者", command=lambda: show_developer_about(self.master))
        about_menu.add_separator()
        about_menu.add_command(label="退出", command=self.master.quit)
        about_mb.config(menu=about_menu)

        # --- 文件菜单 ---
        file_mb = tk.Menubutton(top_bar_frame, text="文件", activebackground="gray", bg="lightgray")
        file_mb.pack(side=tk.LEFT, padx=5)
        file_menu = tk.Menu(file_mb, tearoff=0)
        file_menu.add_command(label="复制", command=self.show_not_implemented)
        file_menu.add_command(label="粘贴", command=self.show_not_implemented)
        file_menu.add_command(label="查看属性", command=self.show_not_implemented)
        file_menu.add_command(label="删除", command=self.show_not_implemented)
        file_menu.add_separator()
        file_menu.add_command(label="新建文件夹", command=self.create_new_folder)
        file_mb.config(menu=file_menu)

        # --- 格式菜单 ---
        format_mb = tk.Menubutton(top_bar_frame, text="格式", activebackground="gray", bg="lightgray")
        format_mb.pack(side=tk.LEFT, padx=5)
        format_menu = tk.Menu(format_mb, tearoff=0)
        format_menu.add_command(label="修改排列格式", command=self.show_not_implemented)
        format_mb.config(menu=format_menu)

        # --- 导航按钮 ---
        go_back_btn = tk.Button(top_bar_frame, text="向后", command=self.go_back, relief=tk.FLAT, bg="lightgray")
        go_back_btn.pack(side=tk.LEFT, padx=5)
        
        go_forward_btn = tk.Button(top_bar_frame, text="向前", command=self.go_forward, relief=tk.FLAT, bg="lightgray")
        go_forward_btn.pack(side=tk.LEFT, padx=5)
        
        refresh_btn = tk.Button(top_bar_frame, text="刷新", command=self.refresh, relief=tk.FLAT, bg="lightgray")
        refresh_btn.pack(side=tk.LEFT, padx=5)

        # --- 退出按钮 ---
        quit_btn = tk.Button(top_bar_frame, text="X", command=self.master.quit, relief=tk.FLAT, bg="lightgray", fg="red")
        quit_btn.pack(side=tk.RIGHT, padx=5)

    def create_widgets(self):
        """创建文件列表视图，并调整列宽以适应窄屏幕"""
        self.path_var = tk.StringVar(value=str(self.current_path))
        path_entry = ttk.Entry(self.master, textvariable=self.path_var, state='readonly')
        path_entry.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建框架来包含Treeview和滚动条
        tree_frame = tk.Frame(self.master)
        tree_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        
        # 注意：show="tree headings" 才能显示图标所在的 #0 列
        self.tree = ttk.Treeview(tree_frame, columns=("modified",), show="tree headings")
        self.tree.heading("#0", text="名称")
        self.tree.heading("modified", text="修改时间")

        # 列宽设置（适配 480px 的布局）
        self.tree.column("#0", width=280, stretch=tk.NO)   # 图标 + 文件名
        self.tree.column("modified", width=140, anchor="w")

        # 创建垂直滚动条
        self.v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.v_scrollbar.set)
        
        # 使用grid布局来放置Treeview和滚动条
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # 配置grid权重，使Treeview可以扩展
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # 绑定双击事件（会调用下面的 on_double_click）
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

        # 文件分类
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

        # 插入 ".." 以返回上一级目录（将 .. 放在 #0 的 text 中）
        if path.parent != path:
            self.tree.insert("", "end",
                text="..",
                values=("上一级",),
                image=self.icon_references.get("folder"),
                tags=('real_dir',)
            )

        # 按分类顺序插入到 Treeview
        for category_name, items in categories.items():
            if not items:
                continue

            # 插入分类的父节点（分类节点不是实际文件夹，不带 real_dir tag）
            category_node = self.tree.insert("", "end",
                text=category_name,
                values=("分类",),
                image=self.icon_references.get("folder"),
                open=False
            )

            # 排序后插入子节点
            items.sort(key=lambda e: e.name.lower())
            for item in items:
                try:
                    stat = item.stat()
                    modified_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                    
                    is_dir = item.is_dir()
                    icon_key = "folder" if is_dir else self.get_icon_key_for_file(item.name)
                    photo_image = self.icon_references.get(icon_key, self.icon_references.get("file"))
                    # 保持对 PhotoImage 的引用，防止被 GC
                    self.photo_image_references.append(photo_image)

                    item_tags = ('real_dir',) if is_dir else ()
                    # 把文件名放到 text（#0 列），把修改时间放到 values
                    self.tree.insert(category_node, "end",
                        text=item.name,
                        values=(modified_time,),
                        image=photo_image,
                        tags=item_tags
                    )
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
    
    def open_document_in_editor(self, file_path: Path):
        """为指定的文件路径启动外部文本编辑器子进程。"""
        try:
            main_executable = sys.executable
            # 必须将 Path 对象转换为字符串才能传递给子进程
            file_path_str = str(file_path)

            if getattr(sys, 'frozen', False):
                # 如果是 PyInstaller 打包后的环境
                # 我们假设主程序可以处理 "file_editor_only" 和一个文件路径参数
                command = [main_executable, "file_editor_only", file_path_str]
            else:
                # 如果是直接用 Python 运行的开发环境
                command = [main_executable, 'software/file_editor_app.py', file_path_str]
            
            # 启动子进程，不阻塞主程序
            subprocess.Popen(command)
            return True

        except Exception as e:
            messagebox.showerror("启动失败", f"启动文件编辑器时发生未知错误：{e}")
            return False
        
    def on_double_click(self, event):
        """处理双击事件：导航目录或用文本编辑器打开文件"""
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        item = self.tree.item(item_id)
        name_text = item.get('text', '')
        tags = item.get('tags', ())

        is_real_folder = 'real_dir' in tags
        is_parent_dir = name_text == ".."

        # 处理父目录导航
        if is_parent_dir:
            new_path = self.current_path.parent
            if new_path != self.current_path:
                self.navigate_to(new_path)
            return

        # 构造完整路径
        full_path = self.current_path / name_text

        # 处理真实目录导航
        if is_real_folder:
            if full_path.is_dir():
                self.navigate_to(full_path)
            else:
                messagebox.showwarning("导航失败", f"目录 '{name_text}' 不存在。")
            return
        
        # --- 新增逻辑：处理文件 ---
        # 如果不是目录，则判断是否为可编辑的文档文件
        if full_path.is_file():
            icon_key = self.get_icon_key_for_file(name_text)
            if icon_key == "editor":
                # 调用新方法打开文本编辑器
                self.open_document_in_editor(full_path)
        
        # (可选) 在这里可以为其他文件类型（如图片、视频）添加不同的打开逻辑
        # else:
        #     # 默认的系统打开方式
        #     os.startfile(full_path)

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
