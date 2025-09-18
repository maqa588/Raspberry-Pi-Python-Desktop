import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, font, colorchooser
import os
import sys
import chardet

# 动态添加项目根目录到 sys.path
# 这使得脚本无论从哪里运行都能找到 system 模块
try:
    current_file_path = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(current_file_path))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from system.config import WINDOW_WIDTH, WINDOW_HEIGHT
    from system.button.about import show_system_about, show_developer_about
except ImportError:
    # 如果作为独立脚本运行，提供默认值
    WINDOW_WIDTH, WINDOW_HEIGHT = 480, 320
    def show_system_about(master): messagebox.showinfo("系统信息", "这是一个独立的应用程序。")
    def show_developer_about(master): messagebox.showinfo("开发者", "代码由AI和您共同完成。")


class FileEditorApp:
    def __init__(self, master):
        self.master = master
        self.master.title("文件编辑器")
        self.master.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        # --- 状态变量初始化 ---
        self.current_filepath = None
        self.current_encoding = 'utf-8'
        self.text_modified = False
        
        # --- 将变量初始化移到这里 ---
        # 提前初始化 Tkinter 变量，确保它们在创建UI时已存在
        self.is_bold = tk.BooleanVar()
        self.is_underline = tk.BooleanVar()

        # --- 正确的UI创建顺序 ---
        # 1. 先创建顶部菜单栏
        self.create_menu()
        # 2. 再创建文本编辑区等主要部件
        self.create_widgets()

        # --- 绑定事件 ---
        self.text_widget.bind("<<Modified>>", self.on_text_modified)
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 处理命令行参数
        self.process_command_line_args()

    def process_command_line_args(self):
        """处理启动时传入的命令行参数"""
        if len(sys.argv) > 1:
            file_to_open = sys.argv[1]
            if os.path.isfile(file_to_open):
                self._load_file(file_to_open)
            elif os.path.isdir(os.path.dirname(os.path.abspath(file_to_open))):
                self.current_filepath = file_to_open
                self.master.title(f"文件编辑器 - {os.path.basename(file_to_open)} (新文件)")
                self.text_modified = False
                self.text_widget.edit_modified(False)
            else:
                 messagebox.showerror("错误", f"无效的文件路径: {file_to_open}")

    def create_menu(self):
        """用自定义顶部栏替换 Tkinter 菜单栏"""
        top_bar_frame = tk.Frame(self.master, bg="#f0f0f0", height=30, bd=1, relief=tk.RAISED)
        top_bar_frame.pack(side=tk.TOP, fill=tk.X)

        # --- 关于菜单按钮 ---
        about_mb = tk.Menubutton(top_bar_frame, text="关于", activebackground="#e1e1e1", bg="#f0f0f0", relief=tk.FLAT)
        about_mb.pack(side=tk.LEFT, padx=5, pady=2)
        about_menu = tk.Menu(about_mb, tearoff=0)
        about_menu.add_command(label="系统信息", command=lambda: show_system_about(self.master))
        about_menu.add_command(label="关于开发者", command=lambda: show_developer_about(self.master))
        about_menu.add_separator()
        about_menu.add_command(label="退出", command=self.on_closing)
        about_mb.config(menu=about_menu)

        # --- 文件菜单按钮 ---
        file_mb = tk.Menubutton(top_bar_frame, text="文件", activebackground="#e1e1e1", bg="#f0f0f0", relief=tk.FLAT)
        file_mb.pack(side=tk.LEFT, padx=5, pady=2)
        file_menu = tk.Menu(file_mb, tearoff=0)
        file_menu.add_command(label="打开...", command=self.open_file)
        file_menu.add_command(label="保存", command=self.save_file)
        file_menu.add_command(label="另存为...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="复制", command=self.copy_text)
        file_menu.add_command(label="粘贴", command=self.paste_text)
        file_menu.add_separator()
        file_menu.add_command(label="查看字数", command=self.show_word_count)
        file_menu.add_command(label="查看编码格式", command=self.show_encoding)
        file_mb.config(menu=file_menu)
        
        # --- 格式菜单按钮 ---
        format_mb = tk.Menubutton(top_bar_frame, text="格式", activebackground="#e1e1e1", bg="#f0f0f0", relief=tk.FLAT)
        format_mb.pack(side=tk.LEFT, padx=5, pady=2)
        format_menu = tk.Menu(format_mb, tearoff=0)
        format_menu.add_command(label="字体大小", command=self.change_font_size)
        format_menu.add_command(label="字体颜色", command=self.change_font_color)
        style_menu = tk.Menu(format_menu, tearoff=0)
        format_menu.add_cascade(label="字体样式", menu=style_menu)
        # 现在这里使用 self.is_bold 不会报错，因为它已在 __init__ 中创建
        style_menu.add_checkbutton(label="加粗", onvalue=True, offvalue=False, variable=self.is_bold, command=self.toggle_bold)
        style_menu.add_checkbutton(label="下划线", onvalue=True, offvalue=False, variable=self.is_underline, command=self.toggle_underline)
        format_mb.config(menu=format_menu)

        # --- 普通命令按钮 ---
        undo_btn = tk.Button(top_bar_frame, text="撤销", command=self.undo_text, relief=tk.FLAT, bg="#f0f0f0", activebackground="#e1e1e1")
        undo_btn.pack(side=tk.LEFT, padx=5, pady=2)
        
        refresh_btn = tk.Button(top_bar_frame, text="刷新", command=self.refresh_file, relief=tk.FLAT, bg="#f0f0f0", activebackground="#e1e1e1")
        refresh_btn.pack(side=tk.LEFT, padx=5, pady=2)

        save_btn = tk.Button(top_bar_frame, text="保存", command=self.save_file, relief=tk.FLAT, bg="#f0f0f0", activebackground="#e1e1e1")
        save_btn.pack(side=tk.LEFT, padx=5, pady=2)

        # --- 退出按钮 ---
        quit_btn = tk.Button(top_bar_frame, text="X", command=self.master.quit, relief=tk.FLAT, bg="lightgray", fg="red")
        quit_btn.pack(side=tk.RIGHT, padx=5)
        
    def create_widgets(self):
        """创建文本框和滚动条"""
        # 这个 Frame 现在会被 pack 到菜单栏下方
        main_frame = tk.Frame(self.master, padx=5, pady=5)
        main_frame.pack(expand=True, fill=tk.BOTH)

        self.scrollbar = tk.Scrollbar(main_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_widget = tk.Text(
            main_frame,
            wrap=tk.WORD,
            undo=True,
            yscrollcommand=self.scrollbar.set
        )
        self.text_widget.pack(expand=True, fill=tk.BOTH)
        self.scrollbar.config(command=self.text_widget.yview)
        
        self.default_font = font.Font(font=self.text_widget['font'])
        self.current_font = self.default_font

    def _load_file(self, filepath):
        """从指定的路径加载文件内容到文本框"""
        try:
            with open(filepath, 'rb') as f:
                raw_data = f.read()
            
            result = chardet.detect(raw_data)
            self.current_encoding = result['encoding'] if result['encoding'] else 'utf-8'
            
            content = raw_data.decode(self.current_encoding, errors='replace')
            
            self.text_widget.delete('1.0', tk.END)
            self.text_widget.insert('1.0', content)
            self.current_filepath = filepath
            self.master.title(f"文件编辑器 - {os.path.basename(filepath)}")
            self.text_modified = False
            self.text_widget.edit_modified(False)
            self.text_widget.edit_reset()

        except Exception as e:
            messagebox.showerror("打开失败", f"无法打开文件：\n{e}")
            self.current_filepath = None
            self.master.title("文件编辑器")

    def open_file(self):
        if self.text_modified:
            if not messagebox.askyesno("警告", "文件已修改，确认要打开新文件并放弃更改吗？"):
                return
        filepath = filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if filepath:
            self._load_file(filepath)

    def _save_to_path(self, filepath):
        try:
            content = self.text_widget.get("1.0", "end-1c") # 使用 end-1c 避免保存末尾多余的换行符
            with open(filepath, 'w', encoding=self.current_encoding, errors='replace') as f:
                f.write(content)
            self.current_filepath = filepath
            self.master.title(f"文件编辑器 - {os.path.basename(filepath)}")
            self.text_modified = False
            self.text_widget.edit_modified(False)
            messagebox.showinfo("成功", f"文件已保存到：\n{filepath}")
            return True
        except Exception as e:
            messagebox.showerror("保存失败", f"无法保存文件：\n{e}")
            return False

    def save_file(self):
        if self.current_filepath:
            self._save_to_path(self.current_filepath)
        else:
            self.save_file_as()

    def save_file_as(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if filepath:
            self._save_to_path(filepath)

    def copy_text(self): self.text_widget.event_generate("<<Copy>>")
    def paste_text(self): self.text_widget.event_generate("<<Paste>>")

    def show_word_count(self):
        content = self.text_widget.get("1.0", tk.END)
        word_count = len(content.split())
        char_count = len(content.strip())
        messagebox.showinfo("字数统计", f"单词数: {word_count}\n字符数 (不含首尾空白): {char_count}")

    def show_encoding(self):
        encoding_info = self.current_encoding or "未知 (新文件默认为 UTF-8)"
        messagebox.showinfo("文件编码", f"当前文件的检测编码为：{encoding_info}")

    def change_font_size(self):
        new_size = simpledialog.askinteger("字体大小", "请输入新的字体大小:", initialvalue=self.current_font.cget("size"))
        if new_size and new_size > 0:
            self.current_font.config(size=new_size)
            self.text_widget.config(font=self.current_font)

    def change_font_color(self):
        color_code = colorchooser.askcolor(title="选择字体颜色")
        if color_code:
            self.text_widget.config(fg=color_code[1])

    def toggle_bold(self):
        new_weight = "bold" if self.is_bold.get() else "normal"
        self.current_font.config(weight=new_weight)
        self.text_widget.config(font=self.current_font)

    def toggle_underline(self):
        self.current_font.config(underline=self.is_underline.get())
        self.text_widget.config(font=self.current_font)
        
    def undo_text(self):
        try:
            self.text_widget.edit_undo()
        except tk.TclError:
            pass

    def refresh_file(self):
        if not self.current_filepath:
            messagebox.showinfo("提示", "这是一个新文件，无法刷新。")
            return
        if self.text_modified:
            if not messagebox.askyesno("警告", "文件已修改，确认要刷新并放弃更改吗？"):
                return
        self._load_file(self.current_filepath)
        messagebox.showinfo("成功", "文件已刷新。")

    def on_text_modified(self, event=None):
        self.text_modified = self.text_widget.edit_modified()

    def on_closing(self):
        if self.text_modified:
            response = messagebox.askyesnocancel("退出", "文件已修改，您想保存吗？")
            if response is True:
                if self.save_file():
                    self.master.destroy()
            elif response is False:
                self.master.destroy()
        else:
            self.master.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = FileEditorApp(root)
    root.mainloop()
