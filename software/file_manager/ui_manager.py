import sys
import tkinter as tk
from tkinter import ttk
from system.button.about import show_system_about, show_developer_about

class UIManager:
    def __init__(self, master, icon_references):
        self.master = master
        self.icon_references = icon_references
        self.path_var = tk.StringVar()
        self.tree = None
        self._create_menu()
        self._create_widgets()

    def _create_menu(self):
        """根据操作系统动态创建菜单栏。"""
        if sys.platform in ['darwin', 'win32']:
            self._create_default_menu()
        else:
            self._create_custom_menu()

    def _create_default_menu(self):
        """创建默认风格的 Tkinter 菜单栏。"""
        self.menubar = tk.Menu(self.master)
        self.master.config(menu=self.menubar)
        
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="文件", menu=self.file_menu)
        
        self.sort_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="排序", menu=self.sort_menu)
        
        self.navigate_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="导航", menu=self.navigate_menu)

        about_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="关于", menu=about_menu)
        about_menu.add_command(label="系统信息", command=lambda: show_system_about(self.master))
        about_menu.add_command(label="关于开发者", command=lambda: show_developer_about(self.master))
        about_menu.add_separator()
        about_menu.add_command(label="退出", command=self.master.quit)

    def _create_custom_menu(self):
        """创建自定义顶部栏（非 macOS/Windows 风格）。"""
        top_bar_frame = tk.Frame(self.master, bg="lightgray", height=30)
        top_bar_frame.pack(side=tk.TOP, fill=tk.X)
        self.file_mb = tk.Menubutton(top_bar_frame, text="文件", activebackground="gray", bg="lightgray")
        self.file_mb.pack(side=tk.LEFT, padx=5)
        self.file_menu = tk.Menu(self.file_mb, tearoff=0)
        self.file_mb.config(menu=self.file_menu)

        self.sort_mb = tk.Menubutton(top_bar_frame, text="排序", activebackground="gray", bg="lightgray")
        self.sort_mb.pack(side=tk.LEFT, padx=5)
        self.sort_menu = tk.Menu(self.sort_mb, tearoff=0)
        self.sort_mb.config(menu=self.sort_menu)
        
        self.back_btn = tk.Button(top_bar_frame, text="向后", relief=tk.FLAT, bg="lightgray")
        self.back_btn.pack(side=tk.LEFT, padx=5)
        self.forward_btn = tk.Button(top_bar_frame, text="向前", relief=tk.FLAT, bg="lightgray")
        self.forward_btn.pack(side=tk.LEFT, padx=5)
        self.refresh_btn = tk.Button(top_bar_frame, text="刷新", relief=tk.FLAT, bg="lightgray")
        self.refresh_btn.pack(side=tk.LEFT, padx=5)

        self.quit_btn = tk.Button(top_bar_frame, text="X", command=self.master.quit, relief=tk.FLAT, bg="#f0f0f0", fg="red", activebackground="#e1e1e1")
        self.quit_btn.pack(side=tk.RIGHT, padx=5, pady=2)

    def _create_widgets(self):
        """创建文件列表视图。"""
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

        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
    
    def bind_commands(self, commands):
        """绑定命令到 UI 元素。"""
        if self.master.cget('menu'):
            # 默认菜单 (macOS/Windows)
            self.file_menu.add_command(label="打开", command=commands['on_double_click'])
            self.file_menu.add_separator()
            self.file_menu.add_command(label="复制", command=commands['copy'])
            self.file_menu.add_command(label="粘贴", command=commands['paste'])
            self.file_menu.add_command(label="查看属性", command=commands['properties'])
            self.file_menu.add_command(label="删除", command=commands['delete'])
            self.file_menu.add_separator()
            self.file_menu.add_command(label="新建文件夹", command=commands['new_folder'])
            
            self.sort_menu.add_command(label="按名称排序", command=commands['sort_name'])
            self.sort_menu.add_command(label="按种类排序", command=commands['sort_category'])
            self.sort_menu.add_command(label="按修改日期排序", command=commands['sort_date'])
            self.sort_menu.add_command(label="按文件大小排序", command=commands['sort_size'])

            self.navigate_menu.add_command(label="向后", command=commands['go_back'])
            self.navigate_menu.add_command(label="向前", command=commands['go_forward'])
            self.navigate_menu.add_command(label="刷新", command=commands['refresh'])

        else:
            # 自定义菜单 (树莓派)
            self.file_menu.add_command(label="打开", command=commands['on_double_click'])
            self.file_menu.add_separator()
            self.file_menu.add_command(label="复制", command=commands['copy'])
            self.file_menu.add_command(label="粘贴", command=commands['paste'])
            self.file_menu.add_command(label="查看属性", command=commands['properties'])
            self.file_menu.add_command(label="删除", command=commands['delete'])
            self.file_menu.add_separator()
            self.file_menu.add_command(label="新建文件夹", command=commands['new_folder'])
            self.file_menu.add_separator()
            self.file_menu.add_command(label="系统信息", command=lambda: show_system_about(self.master))
            self.file_menu.add_command(label="关于开发者", command=lambda: show_developer_about(self.master))
            
            # --- 修复点：为自定义排序菜单添加命令 ---
            self.sort_menu.add_command(label="按名称排序", command=commands['sort_name'])
            self.sort_menu.add_command(label="按种类排序", command=commands['sort_category'])
            self.sort_menu.add_command(label="按修改日期排序", command=commands['sort_date'])
            self.sort_menu.add_command(label="按文件大小排序", command=commands['sort_size'])
            # --- 修复点结束 ---
            
            self.back_btn.config(command=commands['go_back'])
            self.forward_btn.config(command=commands['go_forward'])
            self.refresh_btn.config(command=commands['refresh'])

        self.tree.bind("<Double-1>", commands['on_double_click'])
        self._bind_hotkeys(commands)

    def _bind_hotkeys(self, commands):
        """绑定快捷键。"""
        if sys.platform == 'darwin':
            self.master.bind_all('<Command-c>', lambda e: commands['copy']())
            self.master.bind_all('<Command-v>', lambda e: commands['paste']())
            self.master.bind_all('<Command-d>', lambda e: commands['delete']())
            self.master.bind_all('<Command-r>', lambda e: commands['refresh']())
            self.master.bind_all('<Command-Left>', lambda e: commands['go_back']())
            self.master.bind_all('<Command-Right>', lambda e: commands['go_forward']())
            self.master.bind_all('<Command-o>', lambda e: commands['on_double_click']())
        else:
            self.master.bind_all('<Control-c>', lambda e: commands['copy']())
            self.master.bind_all('<Control-v>', lambda e: commands['paste']())
            self.master.bind_all('<Delete>', lambda e: commands['delete']())
            self.master.bind_all('<F5>', lambda e: commands['refresh']())
            self.master.bind_all('<Alt-Left>', lambda e: commands['go_back']())
            self.master.bind_all('<Alt-Right>', lambda e: commands['go_forward']())
            self.master.bind_all('<Control-o>', lambda e: commands['on_double_click']())
