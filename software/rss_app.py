import tkinter as tk
from tkinter import ttk
import sys
import os
import subprocess
from tkinter import messagebox
from pathlib import Path
import re 
from urllib.parse import urlparse # 用于 URL 解析
import webbrowser # 用于打开 URL

current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file_path))
sys.path.insert(0, project_root)
# 假设这些导入在项目中可用，用于菜单
try:
    from system.button.about import show_system_about, show_developer_about
except ImportError:
    # 定义占位函数以防导入失败，确保代码能运行
    def show_system_about(root): messagebox.showinfo("系统信息", "此为系统信息占位符。")
    def show_developer_about(root): messagebox.showinfo("开发者信息", "此为开发者信息占位符。")
    print("警告: 未能导入 system.button.about，使用占位函数。")

# 假设 system.config 位于项目的某个父目录或可导入路径中
try:
    # 尝试从预期路径导入配置
    from system.config import WINDOW_WIDTH, WINDOW_HEIGHT
    # 如果配置存在，使用配置，否则使用默认值
    APP_WIDTH = WINDOW_WIDTH
    APP_HEIGHT = WINDOW_HEIGHT
except ImportError:
    # 适配 480x320 紧凑布局
    APP_WIDTH = 480
    APP_HEIGHT = 320
    print("警告: 未能导入 system.config 中的窗口尺寸，使用默认值 (480x320)。")

# --- 网络和多线程依赖 ---
import requests
import feedparser
import threading
# ----------------------------

# ==============================================================================
# RSS 阅读器主应用
# ==============================================================================

class RSSReaderApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Tkinter RSS 阅读器")
        self.master.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        
        # 居中窗口
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        x = (screen_width // 2) - (APP_WIDTH // 2)
        y = (screen_height // 2) - (APP_HEIGHT // 2)
        self.master.geometry(f'+{x}+{y}')
        
        # 用于管理后台线程
        self.fetch_thread = None
        self.rss_url = tk.StringVar(value="https://winddine.top/rss.xml") # 默认 URL
        
        # -------------------
        # 整合菜单功能
        # -------------------
        self.create_menu()
        
        self._setup_ui()
        
        # 立即加载默认 URL
        self.load_feed()

    # ==========================================================================
    # 菜单功能 (根据用户要求植入)
    # ==========================================================================

    def create_menu(self):
        """根据操作系统动态创建菜单栏"""
        # 检查操作系统是否为 macOS 或 Windows
        if sys.platform == 'darwin' or sys.platform == 'win32':
            print(f"Detected {sys.platform}, creating default Tkinter menu.")
            self.create_default_menu()
        else:
            print(f"Detected {sys.platform}, creating custom top bar menu.")
            self.create_custom_menu()

    def create_default_menu(self):
        """创建默认风格的 Tkinter 菜单栏"""
        self.menubar = tk.Menu(self.master)
        self.master.config(menu=self.menubar)

        # 文件菜单 (刷新, 打开URL, 关闭)
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="刷新", command=self.load_feed)
        file_menu.add_command(label="打开URL", command=self._open_current_feed_link)
        file_menu.add_separator()
        file_menu.add_command(label="关闭", command=self.master.quit)

        # 关于菜单 (系统信息, 开发者信息)
        about_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="关于", menu=about_menu)
        about_menu.add_command(label="系统信息", command=lambda:show_system_about(self.master))
        about_menu.add_command(label="开发者信息", command=lambda:show_developer_about(self.master))

    def create_custom_menu(self):
        """创建自定义顶部栏（非 macOS 或 Windows 风格）"""
        # 注意: 这里的菜单实现使用了 pack，可能与主应用的 pack 布局冲突，但为了遵循用户提供的结构，暂时使用 frame+pack
        top_bar_frame = tk.Frame(self.master, bg="#f0f0f0", height=30, bd=1, relief=tk.RAISED)
        # 使用 pack 来确保它在顶部，因为主内容也使用 pack
        top_bar_frame.pack(fill='x', side='top')
        
        # 文件菜单按钮
        file_mb = tk.Menubutton(top_bar_frame, text="文件", activebackground="#e1e1e1", bg="#f0f0f0", relief=tk.FLAT)
        file_mb.pack(side=tk.LEFT, padx=5, pady=2)
        file_menu = tk.Menu(file_mb, tearoff=0)
        file_menu.add_command(label="刷新", command=self.load_feed)
        file_menu.add_command(label="打开URL", command=self._open_current_feed_link)
        file_menu.add_separator()
        file_menu.add_command(label="关闭", command=self.master.quit)
        file_mb.config(menu=file_menu)
        
        # 关于菜单按钮
        about_mb = tk.Menubutton(top_bar_frame, text="关于", activebackground="#e1e1e1", bg="#f0f0f0", relief=tk.FLAT)
        about_mb.pack(side=tk.LEFT, padx=5, pady=2)
        about_menu = tk.Menu(about_mb, tearoff=0)
        about_menu.add_command(label="系统信息", command=lambda:show_system_about(self.master))
        about_menu.add_command(label="开发者信息", command=lambda:show_developer_about(self.master))
        about_mb.config(menu=about_menu)

        quit_btn = tk.Button(top_bar_frame, text="X", command=self.master.quit, relief=tk.FLAT, bg="#f0f0f0", fg="red", activebackground="#e1e1e1")
        quit_btn.pack(side=tk.RIGHT, padx=5, pady=2)
        
    def _sanitize_url(self, url):
        """
        去除 URL 末尾的 RSS 文件名，如 /rss.xml, /rss, /index.xml 等，并确保有协议头。
        例如：https://winddine.top/rss.xml -> https://winddine.top
        """
        if not url:
            return ""
        
        # 移除常见的 RSS 文件后缀 (确保只在末尾匹配)
        url = re.sub(r'/(rss(\.xml)?|index\.xml|feed\.xml|atom)$', '', url, flags=re.IGNORECASE)
        
        # 确保 URL 有协议头
        parsed = urlparse(url)
        if not parsed.scheme:
            url = 'http://' + url
            
        return url

    def _open_current_feed_link(self):
        """
        使用外部浏览器应用 (browser_app.py) 打开当前 RSS 订阅源的根 URL。
        """
        raw_url = self.rss_url.get()
        if not raw_url:
             messagebox.showinfo("提示", "URL 栏为空，无法打开。")
             return
             
        target_url = self._sanitize_url(raw_url)

        try:
            # 浏览器应用路径：在项目根目录下的 software 文件夹中
            browser_path = os.path.join(project_root, 'software', 'browser_app.py')
            
            # 检查浏览器文件是否存在
            if not os.path.exists(browser_path):
                messagebox.showerror("错误", f"找不到浏览器应用: {browser_path}")
                return

            # 使用 Python 解释器执行 browser_app.py 并传入目标 URL
            # sys.executable 是当前运行的 Python 解释器的路径
            subprocess.Popen([sys.executable, browser_path, target_url])
            
        except Exception as e:
            messagebox.showerror("错误", f"无法启动浏览器应用或打开 URL: {target_url}\n错误信息: {e}")

    # ==========================================================================
    # UI/逻辑功能 (移除图片相关内容)
    # ==========================================================================

    def _extract_text_and_images(self, text):
        """
        [精简] 仅用于清理 HTML 标签并提取纯文本。
        """
        # 1. 替换 <br> 或 <br /> 为换行符
        text_with_newlines = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)

        # 2. 移除所有 HTML 标签
        cleaned_text = re.sub(r'<[^>]+>', '', text_with_newlines)
        
        # 3. 清理结果：移除多余的空白行和首尾空格
        # 返回一个空的 list 作为图片 URL，以匹配原来的方法签名（尽管现在不再使用）
        return cleaned_text.strip(), []

    def _setup_ui(self):
        """配置应用程序界面，现在只有 URL 栏和文章文本区。"""
        # -------------------
        # 1. URL 输入框架 (顶部)
        # -------------------
        url_frame = ttk.Frame(self.master, padding="5 5 5 2")
        url_frame.pack(fill='x')
        
        ttk.Label(url_frame, text="URL:").pack(side='left', padx=(0, 5))
        
        self.url_entry = ttk.Entry(url_frame, textvariable=self.rss_url)
        self.url_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        ttk.Button(url_frame, text="刷新", command=self.load_feed).pack(side='left')

        # -------------------
        # 2. 标题和描述 (中间)
        # -------------------
        header_frame = ttk.Frame(self.master, padding="5 2 5 2")
        header_frame.pack(fill='x')
        header_frame.grid_columnconfigure(0, weight=1) # 标题占位
        header_frame.grid_columnconfigure(1, weight=1) # 描述占位

        # 博客标题 (左侧)
        self.title_label = ttk.Label(header_frame, text="博客标题: 正在加载...", 
                                     font=('Arial', 10, 'bold'), wraplength=(APP_WIDTH // 2) - 10)
        self.title_label.grid(row=0, column=0, sticky='w')

        # 描述 (右侧)
        self.feed_desc_var = tk.StringVar(value="描述: -")
        self.desc_label = ttk.Label(header_frame, textvariable=self.feed_desc_var, 
                                     font=('Arial', 8), wraplength=(APP_WIDTH // 2) - 10, 
                                     anchor='e', justify='right')
        self.desc_label.grid(row=0, column=1, sticky='e')
        
        # 插入一个分隔符
        ttk.Separator(self.master, orient='horizontal').pack(fill='x', padx=5, pady=2)

        # -------------------
        # 3. 内容文本区 (Text widget) - 占据剩余所有空间
        # -------------------
        
        main_frame = ttk.Frame(self.master, padding="5 0 5 5")
        main_frame.pack(fill='both', expand=True) # 占据所有剩余空间
        
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(side='left', fill='both', expand=True)
        
        self.content_text = tk.Text(text_frame, wrap='word', padx=3, pady=3, font=('Arial', 9))
        self.content_text.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame, command=self.content_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.content_text.config(yscrollcommand=scrollbar.set)
        
        # 配置标签 tag 来模拟链接
        self.content_text.tag_config('title', font=('Arial', 11, 'bold')) 
        self.content_text.tag_config('link', foreground='#0066cc', underline=1)
        self.content_text.tag_bind('link', '<Button-1>', self._open_link)
        
        # 初始化内容
        self.content_text.insert('1.0', "最新文章将显示在此处。请点击刷新按钮。")
        self.content_text.config(state='disabled') # 只读

    # 移除了所有图片加载和同步方法：
    # _sync_image_on_scroll
    # _display_placeholder_image
    # _process_and_display_sidebar_image
    # _load_and_display_sidebar_image


    def load_feed(self):
        """
        加载并解析 RSS 订阅源，在后台线程中执行网络操作，以避免阻塞 UI。
        """
        if self.fetch_thread and self.fetch_thread.is_alive():
            messagebox.showinfo("提示", "正在加载中，请稍候...")
            return

        url = self.rss_url.get()
        self.title_label.config(text=f"博客标题: 正在加载 '{url}'...")
        self._clear_content(initial=True) # 显示加载信息

        # 启动后台线程进行网络请求和解析
        self.fetch_thread = threading.Thread(target=self._fetch_and_parse_feed, args=(url,))
        self.fetch_thread.daemon = True
        self.fetch_thread.start()

    def _fetch_and_parse_feed(self, url):
        """
        在后台线程中执行网络请求和 RSS 解析。
        """
        result = {'success': False, 'error': None, 'feed': None}
        
        try:
            # 1. 网络请求
            headers = {'User-Agent': 'Tkinter_RSS_Reader/1.0'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 2. RSS 解析
            feed = feedparser.parse(response.content)
            
            if feed.bozo and not feed.entries:
                if feed.bozo_exception:
                    result['error'] = f"RSS 解析警告/错误: {feed.bozo_exception}"
                if feed.entries:
                    result['success'] = True
                    result['feed'] = feed
                else:
                    result['error'] = "RSS 解析失败且未获取到任何文章。"
            else:
                result['success'] = True
                result['feed'] = feed
                
        except requests.exceptions.Timeout as e:
            result['error'] = f"网络请求超时 (10秒): {e}"
        except requests.exceptions.ConnectionError as e:
            result['error'] = f"无法连接到该 URL，请检查网络和 URL: {e}"
        except requests.exceptions.RequestException as e:
            result['error'] = f"网络请求失败: {e}"
        except Exception as e:
            result['error'] = f"未知错误: {e}"
            
        # 线程安全地调度 UI 更新
        self.master.after(0, lambda: self._update_ui_with_data(result))

    def _update_ui_with_data(self, result):
        """
        在主线程中接收解析结果并更新 UI。(已移除图片处理逻辑)
        """
        
        self._clear_content(initial=False) 
        
        if not result['success']:
            # 处理错误情况
            error_message = result.get('error', '加载失败，无详细错误信息。')
            self.title_label.config(text="博客标题: 错误")
            self.feed_desc_var.set(f"描述: 加载失败\n{error_message}")
            return
            
        feed = result['feed']
        
        # 1. 更新标题和描述
        feed_title = feed.feed.get('title', '未知标题')
        feed_description = feed.feed.get('subtitle', feed.feed.get('description', '无描述信息'))
        
        self.title_label.config(text=f"博客标题: {feed_title}")
        self.feed_desc_var.set(f"描述: {feed_description}") 

        # 2. 插入文章内容
        self.content_text.config(state='normal')
        
        if not feed.entries:
            self.content_text.insert('1.0', "此订阅源加载成功，但目前没有文章内容。")
        
        for entry_index, entry in enumerate(feed.entries):
            # --- 1. 获取文章信息和摘要 ---
            title = entry.get('title', '无标题')
            published = entry.get('published', entry.get('updated', '无日期'))
            link = entry.get('link', '#')
            author = entry.get('author', '未知作者') 
            category_list = entry.get('tags', [])
            category = category_list[0]['term'] if category_list else entry.get('category', '无分类')
            
            if entry.get('content') and isinstance(entry['content'], list) and entry['content'][0].get('value'):
                summary = entry['content'][0]['value']
            else:
                summary = entry.get('summary', entry.get('description', '无摘要'))
                
            # 从 HTML 摘要中提取纯文本 (图片 URL 自动被忽略)
            summary_cleaned, _ = self._extract_text_and_images(summary)
            
            # --- 2. 插入内容，创建新排版 ---
            
            # 插入标题 (包含链接 tag)
            start_index = self.content_text.index(tk.END)
            self.content_text.insert(tk.END, title, 'title') 
            end_index_of_title = self.content_text.index(tk.END)
            self.content_text.tag_add('link', start_index, end_index_of_title)
            # 注意：这里仍然使用 webbrowser 打开文章的链接
            self.content_text.tag_bind('link', '<Button-1>', lambda e, url=link: self._open_link(e, url))
            self.content_text.insert(tk.END, "\n")

            # 插入元数据
            metadata_line = f"作者: {author} | 分类: {category} | 发布时间: {published}\n"
            self.content_text.insert(tk.END, metadata_line)
            
            # 插入摘要 (只插入纯文本)
            self.content_text.insert(tk.END, f"\n摘要:\n{summary_cleaned}\n")

            # 插入分隔符
            self.content_text.insert(tk.END, "\n— — — — — — — — — — — — — — — — —\n\n")

        self.content_text.config(state='disabled')
        
    def _clear_content(self, initial=False):
        """清空内容区域以便加载新数据。"""
        # 清空描述
        self.feed_desc_var.set("描述: -")
        
        # 清空文章内容
        self.content_text.config(state='normal')
        self.content_text.delete('1.0', tk.END)
        
        # 清理所有标记
        for mark_name in self.content_text.mark_names():
            if mark_name.startswith('article_'):
                self.content_text.mark_unset(mark_name)
        
        if initial:
             self.content_text.insert('1.0', "正在从互联网加载 RSS 订阅源...")
        
        self.content_text.config(state='disabled')
        
    def _open_link(self, event, url=None):
        """处理链接点击事件，在外部浏览器中打开 URL。（文章内部链接）"""
        if url and url != '#':
            try:
                # 保持使用系统默认浏览器打开文章链接
                webbrowser.open_new_tab(url)
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文章链接: {url}\n错误信息: {e}")
        # else: pass

# ==============================================================================
# 启动块 (被 rss_init.py 或 app.py 作为子进程启动时执行)
# ==============================================================================

if __name__ == '__main__':
    # 检查当前脚本是否作为独立应用被调用 (开发环境)
    current_script_name = os.path.basename(__file__)
    
    # 允许直接执行 (调试模式)，或作为子进程启动
    is_direct_start = len(sys.argv) == 1
    is_dev_start = len(sys.argv) > 1 and sys.argv[1].endswith(current_script_name)
    is_frozen_start = len(sys.argv) > 1 and sys.argv[1] == "rss_only"
    
    if is_direct_start or is_dev_start or is_frozen_start:
         try:
             root = tk.Tk()
             RSSReaderApp(root)
             root.mainloop()
         except Exception as e:
             # 在子进程中，如果发生错误，直接打印到 stderr
             print(f"RSS Reader 独立应用启动失败: {e}", file=sys.stderr)
