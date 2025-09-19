import os
import sys
import shutil
import subprocess
from PIL import Image, ImageTk
import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file_path))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from system.config import WINDOW_WIDTH, WINDOW_HEIGHT
from system.button.about import show_system_about, show_developer_about

class FileManagerApp:
    def __init__(self, master):
        self.master = master
        self.master.title("文件管理器")
        self.project_root = Path(__file__).resolve().parent.parent
        self.master.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        self.current_path = Path.home()
        self.history = [self.current_path]
        self.history_index = 0
        self.icon_references = {}
        self.photo_image_references = [] # 防止图片被垃圾回收
        self.property_window_icon = None # 确保属性窗口的图标不被回收

        # 用于复制/粘贴功能
        self.clipboard_path = None
        self.clipboard_action = None  # 'copy' or 'cut'

        # 用于排序功能, 元组(排序依据, 是否反向)
        self.sort_criteria = ('name', False) 

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
        # 适应脚本在不同位置运行的情况
        try:
            icon_path = Path(__file__).parent.parent / "icons"
            if not icon_path.exists():
                 icon_path = Path("icons") # Fallback for running in root
        except NameError:
            # __file__ is not defined when running in some environments
            icon_path = Path("icons")

        for name, filename in icon_names.items():
            try:
                img_path = icon_path / filename
                if img_path.exists():
                    img = Image.open(img_path).resize((16, 16), Image.Resampling.LANCZOS)
                    self.icon_references[name] = ImageTk.PhotoImage(img)
                else:
                    raise FileNotFoundError
            except Exception as e:
                print(f"警告: 加载图标 {filename} 失败: {e}. 将使用一个空白图片。")
                # 创建一个空白图片作为备用
                img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
                self.icon_references[name] = ImageTk.PhotoImage(img)

    def create_menu(self):
        """根据操作系统动态创建菜单栏"""
        if sys.platform in ['darwin', 'win32']:
            self.create_default_menu()
        else:
            self.create_custom_menu()

    def create_default_menu(self):
        """创建默认风格的 Tkinter 菜单栏"""
        self.menubar = tk.Menu(self.master)
        self.master.config(menu=self.menubar)

        # --- 根据操作系统设置不同的修饰键 ---
        if sys.platform == 'darwin':  # macOS
            copy_key = "Command-c"
            paste_key = "Command-v"
            delete_key = "Command-d"
            refresh_key = "Command-r"
            back_key = "Command-Left"
            forward_key = "Command-Right"
            open_key = "Command-o"
        else:  # Windows 或 Linux
            copy_key = "Ctrl-c"
            paste_key = "Ctrl-v"
            delete_key = "Del"  # 或 "Delete"
            refresh_key = "F5"
            back_key = "Alt-Left"
            forward_key = "Alt-Right"
            open_key = "Ctrl-o"
        
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
        file_menu.add_command(label="打开", command=self.on_double_click, accelerator=open_key)
        file_menu.add_separator()
        file_menu.add_command(label="复制", command=self.copy_item, accelerator=copy_key)
        file_menu.add_command(label="粘贴", command=self.paste_item, accelerator=paste_key)
        file_menu.add_command(label="查看属性", command=self.show_properties)
        file_menu.add_command(label="删除", command=self.delete_item, accelerator=delete_key)
        file_menu.add_separator()
        file_menu.add_command(label="新建文件夹", command=self.create_new_folder)
        
        # --- 排序菜单 ---
        sort_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="排序", menu=sort_menu)
        sort_menu.add_command(label="按名称排序", command=self.sort_by_name)
        sort_menu.add_command(label="按种类排序", command=self.sort_by_category)
        sort_menu.add_command(label="按修改日期排序", command=self.sort_by_date)
        sort_menu.add_command(label="按文件大小排序", command=self.sort_by_size)
        
        # --- 导航按钮 ---
        navigate_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="导航", menu=navigate_menu)
        navigate_menu.add_command(label="向后", command=self.go_back, accelerator=back_key)
        navigate_menu.add_command(label="向前", command=self.go_forward, accelerator=forward_key)
        navigate_menu.add_command(label="刷新", command=self.refresh, accelerator=refresh_key)

        # --- 绑定快捷键 ---
        # Windows/Linux 绑定
        self.master.bind_all('<Control-c>', lambda event: self.copy_item())
        self.master.bind_all('<Control-v>', lambda event: self.paste_item())
        self.master.bind_all('<Delete>', lambda event: self.delete_item())
        self.master.bind_all('<F5>', lambda event: self.refresh())
        self.master.bind_all('<Alt-Left>', lambda event: self.go_back())
        self.master.bind_all('<Alt-Right>', lambda event: self.go_forward())
        self.master.bind_all('<Control-o>', lambda event: self.on_double_click())

        # macOS 绑定
        if sys.platform == 'darwin':
            self.master.bind_all('<Command-c>', lambda event: self.copy_item())
            self.master.bind_all('<Command-v>', lambda event: self.paste_item())
            self.master.bind_all('<Command-d>', lambda event: self.delete_item())
            self.master.bind_all('<Command-r>', lambda event: self.refresh())
            self.master.bind_all('<Command-Left>', lambda event: self.go_back())
            self.master.bind_all('<Command-Right>', lambda event: self.go_forward())
            self.master.bind_all('<Command-o>', lambda event: self.on_double_click())

    def create_custom_menu(self):
        """创建自定义顶部栏（非 macOS/Windows 风格）"""
        top_bar_frame = tk.Frame(self.master, bg="lightgray", height=30)
        top_bar_frame.pack(side=tk.TOP, fill=tk.X)

        # --- 关于菜单按钮 ---
        about_mb = tk.Menubutton(top_bar_frame, text="关于", activebackground="gray", bg="lightgray")
        about_mb.pack(side=tk.LEFT, padx=5)
        about_menu = tk.Menu(about_mb, tearoff=0)
        about_menu.add_command(label="系统信息", command=lambda: show_system_about(self.master))
        about_menu.add_command(label="关于开发者", command=lambda: show_developer_about(self.master))
        about_menu.add_separator()
        about_menu.add_command(label="退出", command=self.master.quit)
        about_mb.config(menu=about_menu)

        # --- 文件菜单按钮 ---
        file_mb = tk.Menubutton(top_bar_frame, text="文件", activebackground="gray", bg="lightgray")
        file_mb.pack(side=tk.LEFT, padx=5)
        file_menu = tk.Menu(file_mb, tearoff=0)
        file_menu.add_command(label="打开", command=self.on_double_click)
        file_menu.add_separator()
        file_menu.add_command(label="复制", command=self.copy_item)
        file_menu.add_command(label="粘贴", command=self.paste_item)
        file_menu.add_command(label="查看属性", command=self.show_properties)
        file_menu.add_command(label="删除", command=self.delete_item)
        file_menu.add_separator()
        file_menu.add_command(label="新建文件夹", command=self.create_new_folder)
        file_mb.config(menu=file_menu)

        # --- 排序菜单按钮 ---
        sort_mb = tk.Menubutton(top_bar_frame, text="排序", activebackground="gray", bg="lightgray")
        sort_mb.pack(side=tk.LEFT, padx=5)
        sort_menu = tk.Menu(sort_mb, tearoff=0)
        sort_menu.add_command(label="按名称排序", command=self.sort_by_name)
        sort_menu.add_command(label="按种类排序", command=self.sort_by_category)
        sort_menu.add_command(label="按修改日期排序", command=self.sort_by_date)
        sort_menu.add_command(label="按文件大小排序", command=self.sort_by_size)
        sort_mb.config(menu=sort_menu)

        # --- 导航按钮 ---
        tk.Button(top_bar_frame, text="向后", command=self.go_back, relief=tk.FLAT, bg="lightgray").pack(side=tk.LEFT, padx=5)
        tk.Button(top_bar_frame, text="向前", command=self.go_forward, relief=tk.FLAT, bg="lightgray").pack(side=tk.LEFT, padx=5)
        tk.Button(top_bar_frame, text="刷新", command=self.refresh, relief=tk.FLAT, bg="lightgray").pack(side=tk.LEFT, padx=5)
        tk.Button(top_bar_frame, text="X", command=self.master.quit, relief=tk.FLAT, bg="lightgray", fg="red").pack(side=tk.RIGHT, padx=5)

    def create_widgets(self):
        """创建文件列表视图"""
        self.path_var = tk.StringVar(value=str(self.current_path))
        path_entry = ttk.Entry(self.master, textvariable=self.path_var, state='readonly')
        path_entry.pack(fill=tk.X, padx=5, pady=5)
        
        tree_frame = tk.Frame(self.master)
        tree_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        
        self.tree = ttk.Treeview(tree_frame, columns=("modified", "size"), show="tree headings")
        self.tree.heading("#0", text="名称")
        self.tree.heading("modified", text="修改时间")
        self.tree.heading("size", text="大小")

        self.tree.column("#0", width=240, stretch=tk.NO)
        self.tree.column("modified", width=140, anchor="w")
        self.tree.column("size", width=80, anchor="e")

        self.v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.v_scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        
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
    
    def _format_size(self, size_bytes):
        """将字节转换为可读的格式"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes/1024**2:.1f} MB"
        else:
            return f"{size_bytes/1024**3:.1f} GB"

    def populate_file_list(self, path: Path):
        """填充文件列表，并按类型分组和排序"""
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.photo_image_references.clear()

        self.current_path = path
        self.path_var.set(str(self.current_path))
        self.master.title(f"文件管理器 - {self.current_path.name}")

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

        if path.parent != path:
            self.tree.insert("", "end", text="..", values=("上一级", "", ""), image=self.icon_references.get("folder"), tags=('real_dir', 'parent_dir'))

        for category_name, items in categories.items():
            if not items:
                continue
            
            # --- 排序逻辑 ---
            sort_key, reverse = self.sort_criteria
            try:
                if sort_key == 'name':
                    items.sort(key=lambda e: e.name.lower(), reverse=reverse)
                elif sort_key == 'date':
                    items.sort(key=lambda e: e.stat().st_mtime, reverse=reverse)
                elif sort_key == 'size':
                    items.sort(key=lambda e: e.stat().st_size, reverse=reverse)
                elif sort_key == 'category': # 实际上是按名称排序，因为它们已经在类别中了
                    items.sort(key=lambda e: self.get_file_category(e.name), reverse=reverse)
            except OSError as e:
                print(f"排序时无法访问文件属性: {e}")

            category_node = self.tree.insert("", "end", text=category_name, values=("分类", "", ""), image=self.icon_references.get("folder"), open=False, tags=('category_header',))

            for item in items:
                try:
                    stat = item.stat()
                    modified_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                    size = self._format_size(stat.st_size) if not item.is_dir() else ""
                    
                    is_dir = item.is_dir()
                    icon_key = "folder" if is_dir else self.get_icon_key_for_file(item.name)
                    photo_image = self.icon_references.get(icon_key, self.icon_references.get("file"))
                    self.photo_image_references.append(photo_image)

                    item_tags = ('real_dir',) if is_dir else ('file',)
                    self.tree.insert(category_node, "end", text=item.name, values=(modified_time, size), image=photo_image, tags=item_tags)
                except OSError:
                    continue

    def get_icon_key_for_file(self, filename: str) -> str:
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
                # --- 这是修改的核心部分 ---
                # 使用 self.project_root 构建绝对路径，避免相对路径问题
                editor_script_path = self.project_root / 'software' / 'file_editor_app.py'
                command = [main_executable, str(editor_script_path), file_path_str]
            
            # 启动子进程，不阻塞主程序
            subprocess.Popen(command)
            return True

        except Exception as e:
            messagebox.showerror("启动失败", f"启动文件编辑器时发生未知错误：{e}")
            return False
        
    def on_double_click(self, event=None):
        """
        处理双击或菜单“打开”事件。
        使用 self.tree.focus() 来获取当前选中的项目，使其不依赖于 event 对象。
        """
        # --- 修改部分：不再使用 event.y，而是获取当前焦点项 ---
        item_id = self.tree.focus() 
        if not item_id:
            # 如果没有任何项目被选中，则不执行任何操作
            return

        item = self.tree.item(item_id)
        name_text = item.get('text', '')
        tags = item.get('tags', [])

        if 'parent_dir' in tags:
            new_path = self.current_path.parent
            if new_path != self.current_path:
                self.navigate_to(new_path)
            return

        if 'category_header' in tags:
            # 展开/折叠分类
            self.tree.item(item_id, open=not self.tree.item(item_id, 'open'))
            return

        full_path = self.current_path / name_text

        if 'real_dir' in tags:
            if full_path.is_dir():
                self.navigate_to(full_path)
            else:
                messagebox.showwarning("导航失败", f"目录 '{name_text}' 不存在。")
        elif 'file' in tags:
            if full_path.is_file():
                icon_key = self.get_icon_key_for_file(name_text)
                if icon_key == "editor":
                    self.open_document_in_editor(full_path)
                else:
                    # 对于其他文件，尝试用系统默认程序打开
                    try:
                        if sys.platform == "win32":
                            os.startfile(full_path)
                        elif sys.platform == "darwin":
                            subprocess.Popen(["open", full_path])
                        else:
                            subprocess.Popen(["xdg-open", full_path])
                    except Exception as e:
                        messagebox.showerror("打开失败", f"无法使用系统默认程序打开文件：\n{e}")

    def navigate_to(self, path: Path):
        self.populate_file_list(path)
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        if self.history[-1] != path:
            self.history.append(path)
        self.history_index = len(self.history) - 1

    def go_back(self, is_error=False):
        if is_error and self.history_index > 0:
            self.history.pop()
            self.history_index -= 1
            self.populate_file_list(self.history[self.history_index])
            return
        if self.history_index > 0:
            self.history_index -= 1
            self.populate_file_list(self.history[self.history_index])

    def go_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.populate_file_list(self.history[self.history_index])

    def refresh(self):
        self.populate_file_list(self.current_path)

    def create_new_folder(self):
        folder_name = simpledialog.askstring("新建文件夹", "请输入文件夹名称:", parent=self.master)
        if folder_name:
            try:
                os.makedirs(self.current_path / folder_name)
                self.refresh()
            except FileExistsError:
                messagebox.showerror("错误", f"文件夹 '{folder_name}' 已存在。")
            except Exception as e:
                messagebox.showerror("错误", f"创建文件夹失败: {e}")

    # --- 新增和修改的功能 ---

    def _get_selected_path(self):
        """辅助函数：获取当前选中的有效文件/文件夹的完整路径"""
        selected_ids = self.tree.selection()
        if not selected_ids:
            messagebox.showinfo("提示", "请先选择一个文件或文件夹。")
            return None
        
        item_id = selected_ids[0]
        item = self.tree.item(item_id)
        tags = item.get('tags', [])
        
        # 过滤掉无效选择，如 ".." 或分类标题
        if 'parent_dir' in tags or 'category_header' in tags:
            messagebox.showinfo("提示", "此项目无法进行操作。")
            return None
            
        name = item.get('text', '')
        return self.current_path / name

    def copy_item(self):
        """复制选定的项目到剪贴板"""
        path = self._get_selected_path()
        if path:
            self.clipboard_path = path
            self.clipboard_action = 'copy'
            messagebox.showinfo("成功", f"'{path.name}' 已复制。")

    def paste_item(self):
        """将剪贴板中的项目粘贴到当前目录"""
        if not self.clipboard_path or not self.clipboard_path.exists():
            messagebox.showwarning("提示", "剪贴板为空或源文件/夹已被移动或删除。")
            return

        dest_path = self.current_path / self.clipboard_path.name
        if dest_path.exists():
            if not messagebox.askyesno("确认", f"'{dest_path.name}' 已存在，要覆盖它吗？"):
                return

        try:
            if self.clipboard_action == 'copy':
                if self.clipboard_path.is_dir():
                    shutil.copytree(self.clipboard_path, dest_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(self.clipboard_path, dest_path)
                self.refresh()
            # 可以为 'cut' 添加逻辑
            # elif self.clipboard_action == 'cut':
            #     shutil.move(str(self.clipboard_path), str(dest_path))
            #     self.clipboard_path = None # 清空剪贴板
            #     self.refresh()
        except Exception as e:
            messagebox.showerror("粘贴失败", f"发生错误：{e}")

    def delete_item(self):
        """删除选定的项目"""
        path = self._get_selected_path()
        if path:
            if messagebox.askyesno("确认删除", f"您确定要删除 '{path.name}' 吗？\n此操作无法撤销。"):
                try:
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    self.refresh()
                except Exception as e:
                    messagebox.showerror("删除失败", f"发生错误：{e}")

    def show_properties(self):
        """显示选定项目的属性"""
        path = self._get_selected_path()
        if not path:
            return

        try:
            stat = path.stat()
            is_dir = path.is_dir()
            
            prop_win = tk.Toplevel(self.master)
            prop_win.title(f"'{path.name}' 的属性")
            prop_win.geometry("350x250")
            prop_win.resizable(False, False)

            frame = ttk.Frame(prop_win, padding="10")
            frame.pack(expand=True, fill=tk.BOTH)

            # 图标和名称
            icon_key = "folder" if is_dir else self.get_icon_key_for_file(path.name)
            self.property_window_icon = self.icon_references.get(icon_key) # 防止被回收
            
            icon_label = ttk.Label(frame, image=self.property_window_icon, text=path.name, compound=tk.LEFT, font=("", 12, "bold"))
            icon_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=5)
            ttk.Separator(frame, orient='horizontal').grid(row=1, column=0, columnspan=2, sticky='ew', pady=5)

            # 属性
            ttk.Label(frame, text="类型:").grid(row=2, column=0, sticky="w")
            category = "文件夹" if is_dir else self.get_file_category(path.name)
            ttk.Label(frame, text=category).grid(row=2, column=1, sticky="w")
            
            ttk.Label(frame, text="位置:").grid(row=3, column=0, sticky="w")
            ttk.Label(frame, text=str(path.parent), wraplength=250).grid(row=3, column=1, sticky="w")

            ttk.Label(frame, text="大小:").grid(row=4, column=0, sticky="w")
            size_str = self._format_size(stat.st_size) if not is_dir else "N/A"
            ttk.Label(frame, text=size_str).grid(row=4, column=1, sticky="w")

            ttk.Label(frame, text="修改日期:").grid(row=5, column=0, sticky="w")
            mod_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            ttk.Label(frame, text=mod_time).grid(row=5, column=1, sticky="w")
            
            ttk.Button(frame, text="确定", command=prop_win.destroy).grid(row=6, column=0, columnspan=2, pady=15)

            prop_win.transient(self.master)
            prop_win.grab_set()
            self.master.wait_window(prop_win)

        except Exception as e:
            messagebox.showerror("错误", f"无法获取属性：{e}")

    # --- 排序方法 ---
    def sort_by_name(self):
        self.sort_criteria = ('name', False)
        self.refresh()

    def sort_by_date(self):
        self.sort_criteria = ('date', True) # True 表示降序，最新的在前面
        self.refresh()

    def sort_by_size(self):
        self.sort_criteria = ('size', True) # True 表示降序，最大的在前面
        self.refresh()
        
    def sort_by_category(self):
        self.sort_criteria = ('category', False)
        self.refresh()


if __name__ == '__main__':
    root = tk.Tk()
    app = FileManagerApp(root)
    root.mainloop()