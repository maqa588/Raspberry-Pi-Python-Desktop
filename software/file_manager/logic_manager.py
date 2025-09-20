import os
import sys
import shutil
import subprocess
import datetime
from pathlib import Path
from tkinter import messagebox, simpledialog
import tkinter as tk
import tkinter as ttk

class LogicManager:
    def __init__(self, app_instance, tree_widget, path_var):
        self.app = app_instance
        self.master = app_instance.master
        self.tree = tree_widget
        self.path_var = path_var

        self.current_path = Path.home()
        self.history = [self.current_path]
        self.history_index = 0
        self.sort_criteria = ('name', False) 
        self.clipboard_path = None
        self.clipboard_action = None

    def get_file_category(self, filename: str) -> str:
        """根据文件扩展名返回分类名称。"""
        # ... (同原文件)
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        if ext in ['mp3', 'wav', 'flac', 'aac']: return "音乐"
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'svg']: return "图片"
        if ext in ['mp4', 'mov', 'avi', 'mkv', 'wmv']: return "视频"
        if ext in ['txt', 'md', 'py', 'json', 'xml', 'log', 'ini', 'cfg', 'pdf', 'doc', 'docx', 'xls', 'xlsx']: return "文档"
        if ext in ['html', 'htm', 'css', 'js']: return "网页"
        if ext in ['zip', 'rar', 'gz', '7z']: return "压缩包"
        return "其他"

    def _format_size(self, size_bytes):
        """将字节转换为可读的格式。"""
        # ... (同原文件)
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes/1024**2:.1f} MB"
        else:
            return f"{size_bytes/1024**3:.1f} GB"

    def get_icon_key_for_file(self, filename: str) -> str:
        """根据文件名返回图标键。"""
        # ... (同原文件)
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        if ext in ['mp3', 'wav', 'flac', 'aac']: return "music"
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']: return "photo"
        if ext in ['mp4', 'mov', 'avi', 'mkv', 'wmv']: return "video"
        if ext in ['txt', 'md', 'py', 'json', 'xml', 'log', 'ini', 'cfg', 'pdf', 'doc', 'docx']: return "editor"
        if ext in ['html', 'htm', 'css', 'js', 'svg']: return "browser"
        return "file"
        
    def populate_file_list(self, path: Path):
        """填充文件列表，并按类型分组和排序。"""
        # ... (同原文件，但需要更新对 icon_references 和 photo_image_references 的引用)
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.app.photo_image_references.clear()

        self.current_path = path
        self.path_var.set(str(self.current_path))
        self.master.title(f"文件管理器 - {self.current_path.name}")
        
        # ... (与原文件管理器中的 `populate_file_list` 逻辑相同)
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
            self.tree.insert("", "end", text="..", values=("上一级", "", ""), image=self.app.icon_references.get("folder"), tags=('real_dir', 'parent_dir'))
        
        for category_name, items in categories.items():
            if not items:
                continue
            
            sort_key, reverse = self.sort_criteria
            try:
                if sort_key == 'name':
                    items.sort(key=lambda e: e.name.lower(), reverse=reverse)
                elif sort_key == 'date':
                    items.sort(key=lambda e: e.stat().st_mtime, reverse=reverse)
                elif sort_key == 'size':
                    items.sort(key=lambda e: e.stat().st_size, reverse=reverse)
                elif sort_key == 'category':
                    items.sort(key=lambda e: self.get_file_category(e.name), reverse=reverse)
            except OSError as e:
                print(f"排序时无法访问文件属性: {e}")

            category_node = self.tree.insert("", "end", text=category_name, values=("分类", "", ""), image=self.app.icon_references.get("folder"), open=False, tags=('category_header',))

            for item in items:
                try:
                    stat = item.stat()
                    modified_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                    size = self._format_size(stat.st_size) if not item.is_dir() else ""
                    
                    is_dir = item.is_dir()
                    icon_key = "folder" if is_dir else self.get_icon_key_for_file(item.name)
                    photo_image = self.app.icon_references.get(icon_key, self.app.icon_references.get("file"))
                    self.app.photo_image_references.append(photo_image)

                    item_tags = ('real_dir',) if is_dir else ('file',)
                    self.tree.insert(category_node, "end", text=item.name, values=(modified_time, size), image=photo_image, tags=item_tags)
                except OSError:
                    continue

    def on_double_click(self, event=None):
        """处理双击或菜单“打开”事件。"""
        # ... (同原文件，需要更新对 self.open_document_in_editor 和 self.navigate_to 的引用)
        item_id = self.tree.focus() 
        if not item_id:
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
                    try:
                        if sys.platform == "win32":
                            os.startfile(full_path)
                        elif sys.platform == "darwin":
                            subprocess.Popen(["open", full_path])
                        else:
                            subprocess.Popen(["xdg-open", full_path])
                    except Exception as e:
                        messagebox.showerror("打开失败", f"无法使用系统默认程序打开文件：\n{e}")

    def open_document_in_editor(self, file_path: Path):
        """为指定的文件路径启动外部文本编辑器子进程。"""
        try:
            main_executable = sys.executable
            file_path_str = str(file_path)
            if getattr(sys, 'frozen', False):
                command = [main_executable, "file_editor_only", file_path_str]
            else:
                editor_script_path = self.app.project_root / 'software' / 'file_editor_app.py'
                command = [main_executable, str(editor_script_path), file_path_str]
            subprocess.Popen(command)
            return True
        except Exception as e:
            messagebox.showerror("启动失败", f"启动文件编辑器时发生未知错误：{e}")
            return False

    def navigate_to(self, path: Path):
        """导航到新路径。"""
        self.populate_file_list(path)
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        if self.history[-1] != path:
            self.history.append(path)
        self.history_index = len(self.history) - 1

    def go_back(self, is_error=False):
        """回到上一级目录。"""
        if is_error and self.history_index > 0:
            self.history.pop()
            self.history_index -= 1
            self.populate_file_list(self.history[self.history_index])
            return
        if self.history_index > 0:
            self.history_index -= 1
            self.populate_file_list(self.history[self.history_index])

    def go_forward(self):
        """前进到下一级目录。"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.populate_file_list(self.history[self.history_index])

    def refresh(self):
        """刷新当前目录。"""
        self.populate_file_list(self.current_path)

    def create_new_folder(self):
        """创建新文件夹。"""
        folder_name = simpledialog.askstring("新建文件夹", "请输入文件夹名称:", parent=self.master)
        if folder_name:
            try:
                os.makedirs(self.current_path / folder_name)
                self.refresh()
            except FileExistsError:
                messagebox.showerror("错误", f"文件夹 '{folder_name}' 已存在。")
            except Exception as e:
                messagebox.showerror("错误", f"创建文件夹失败: {e}")

    def _get_selected_path(self):
        """辅助函数：获取当前选中的有效文件/文件夹的完整路径。"""
        selected_ids = self.tree.selection()
        if not selected_ids:
            messagebox.showinfo("提示", "请先选择一个文件或文件夹。")
            return None
        
        item_id = selected_ids[0]
        item = self.tree.item(item_id)
        tags = item.get('tags', [])
        
        if 'parent_dir' in tags or 'category_header' in tags:
            messagebox.showinfo("提示", "此项目无法进行操作。")
            return None
            
        name = item.get('text', '')
        return self.current_path / name

    def copy_item(self):
        """复制选定的项目到剪贴板。"""
        path = self._get_selected_path()
        if path:
            self.clipboard_path = path
            self.clipboard_action = 'copy'
            messagebox.showinfo("成功", f"'{path.name}' 已复制。")

    def paste_item(self):
        """将剪贴板中的项目粘贴到当前目录。"""
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
        except Exception as e:
            messagebox.showerror("粘贴失败", f"发生错误：{e}")

    def delete_item(self):
        """删除选定的项目。"""
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
        """显示选定项目的属性。"""
        path = self._get_selected_path()
        if not path:
            return
        try:
            stat = path.stat()
            is_dir = path.is_dir()
            prop_win = tk.Toplevel(self.master)
            prop_win.title(f"'{path.name}' 的属性")
            # ... (显示属性窗口的UI逻辑，需要引用 app.property_window_icon)
            prop_win.geometry("350x250")
            prop_win.resizable(False, False)
            frame = ttk.Frame(prop_win, padding="10")
            frame.pack(expand=True, fill=tk.BOTH)
            icon_key = "folder" if is_dir else self.get_icon_key_for_file(path.name)
            self.app.property_window_icon = self.app.icon_references.get(icon_key)
            icon_label = ttk.Label(frame, image=self.app.property_window_icon, text=path.name, compound=tk.LEFT, font=("", 12, "bold"))
            icon_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=5)
            # ... (其他属性标签)
            ttk.Separator(frame, orient='horizontal').grid(row=1, column=0, columnspan=2, sticky='ew', pady=5)
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

    def sort_by_name(self):
        self.sort_criteria = ('name', False)
        self.refresh()
    def sort_by_date(self):
        self.sort_criteria = ('date', True)
        self.refresh()
    def sort_by_size(self):
        self.sort_criteria = ('size', True)
        self.refresh()
    def sort_by_category(self):
        self.sort_criteria = ('category', False)
        self.refresh()