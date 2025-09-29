import tkinter as tk
from tkinter import ttk
import sys
import os
import subprocess
from tkinter import messagebox
from pathlib import Path
import re 
import io # 用于处理网络下载的图片数据流

current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file_path))
sys.path.insert(0, project_root)

# 新增 Pillow 依赖，用于图片处理
try:
    from PIL import Image, ImageTk 
except ImportError:
    # 如果用户没有安装 Pillow，提供一个错误提示
    print("错误: 需要安装 Pillow 库 (pip install Pillow) 才能显示图片。", file=sys.stderr)
    Image = None
    ImageTk = None

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
        
        # 用于存储侧边栏图片引用，防止被垃圾回收
        self.sidebar_image_ref = None 
        # 缓存所有文章的图片URL，用于滚动同步
        self.article_image_urls = []
        # 记录当前显示的图片 URL，避免重复加载
        self.current_image_url = None
        
        self._setup_ui()
        
        # 立即加载默认 URL
        self.load_feed()

    def _extract_text_and_images(self, text):
        """
        提取纯文本和图片 URL，并用占位符标记图片位置。
        返回 (cleaned_text_with_placeholders, image_urls)
        注意：占位符文本最终会在插入到 Text 控件前被移除，这里主要目的是获取 URL。
        """
        image_urls = []
        
        # 正则表达式用于查找 <img> 标签并捕获 src 属性
        img_pattern = re.compile(r'<img\s+[^>]*src\s*=\s*["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)

        def img_replacer(match):
            url = match.group(1)
            # 过滤掉常见的 1x1 追踪像素图或透明像素
            if "telemetry.gif" in url or 'opacity:0' in match.group(0).lower():
                 return '' # 忽略追踪像素，替换为空字符串
            
            # 只记录第一个图片 URL，因为侧边栏只显示一个
            if not image_urls:
                 image_urls.append(url)
            
            # 使用一个临时占位符，以便在后续步骤中清理文本
            return f"\n[[TEMP_IMG_LOC_{len(image_urls) - 1}]]\n" 

        # 1. 替换 <img> 标签为占位符，并收集 URL
        text_with_placeholders = img_pattern.sub(img_replacer, text)
        
        # 2. 替换 <br> 或 <br /> 为换行符
        text_with_placeholders = re.sub(r'<br\s*/?>', '\n', text_with_placeholders, flags=re.IGNORECASE)

        # 3. 移除所有剩余的 HTML 标签
        cleaned_text = re.sub(r'<[^>]+>', '', text_with_placeholders)
        
        # 4. 清理结果：移除多余的空白行和首尾空格
        return cleaned_text.strip(), image_urls

    def _setup_ui(self):
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
        # 2. 标题和描述 (中间 - 紧凑布局)
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
        # 3. 内容列表和图片显示 (底部 - 2:1 布局)
        # -------------------
        
        main_split_frame = ttk.Frame(self.master, padding="5 0 5 5")
        main_split_frame.pack(fill='both', expand=True)
        
        # 配置 2:1 比例的网格
        main_split_frame.grid_columnconfigure(0, weight=2) # 文本内容 (2/3)
        main_split_frame.grid_columnconfigure(1, weight=1) # 图片显示 (1/3)
        main_split_frame.grid_rowconfigure(0, weight=1)

        # A. 文本内容区 (Text widget) - 2/3 宽度
        text_frame = ttk.Frame(main_split_frame)
        text_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        self.content_text = tk.Text(text_frame, wrap='word', padx=3, pady=3, font=('Arial', 9))
        self.content_text.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame, command=self.content_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.content_text.config(yscrollcommand=scrollbar.set)
        
        # 绑定滚动事件：鼠标拖动滚动条时触发，用于图片同步
        self.content_text.bind("<B1-Motion>", self._sync_image_on_scroll)
        # 绑定鼠标滚轮事件 (可能因平台而异，但尝试绑定)
        self.content_text.bind("<MouseWheel>", self._sync_image_on_scroll)
        self.content_text.bind("<Button-4>", self._sync_image_on_scroll) # Linux/X11 up
        self.content_text.bind("<Button-5>", self._sync_image_on_scroll) # Linux/X11 down
        
        # 配置标签 tag 来模拟链接
        self.content_text.tag_config('title', font=('Arial', 11, 'bold')) 
        self.content_text.tag_config('link', foreground='#0066cc', underline=1)
        self.content_text.tag_bind('link', '<Button-1>', self._open_link)
        
        # B. 图片显示区 (Label widget) - 1/3 宽度
        image_frame = ttk.Frame(main_split_frame, relief='raised', borderwidth=1, padding=3)
        image_frame.grid(row=0, column=1, sticky='nsew')
        
        self.image_display_label = ttk.Label(image_frame, 
                                            text="无图片或正在加载...", 
                                            anchor='center', 
                                            justify='center',
                                            font=('Arial', 8, 'italic'),
                                            background='#333333', 
                                            foreground='#AAAAAA')
        self.image_display_label.pack(fill='both', expand=True)
        
        # 初始化内容
        self.content_text.insert('1.0', "最新文章将显示在此处。请点击刷新按钮。")
        self.content_text.config(state='disabled') # 只读

    def _sync_image_on_scroll(self, event=None):
        """
        根据 Text 控件的滚动位置，同步右侧图片。
        查找当前最顶部的标记 (mark) 来确定当前可见的是哪篇文章。
        """
        # 确保有文章数据
        if not self.article_image_urls:
            return

        # 获取当前 Text 控件可见区域的起始索引 (例如: "1.0")
        visible_start_index = self.content_text.index("@0,0")
        
        # 遍历所有文章标记，找到第一个位于或低于可见起始索引的标记
        target_article_index = 0 # 默认为第一篇
        
        for i in range(len(self.article_image_urls)):
            mark_name = f"article_{i}"
            try:
                # 获取文章标记的位置
                mark_index = self.content_text.index(mark_name)
                
                # 如果当前文章标记的位置在可见区域之上或与可见区域顶部重合，则更新目标索引
                if self.content_text.compare(mark_index, "<=", visible_start_index):
                    target_article_index = i
                elif self.content_text.compare(mark_index, ">", visible_start_index):
                    # 如果标记已经滚出可见区域顶部，则跳出循环，使用最后一个匹配的 target_article_index
                    break
            except tk.TclError:
                # 标记不存在，跳过
                continue

        # 获取目标文章的图片 URL
        new_image_url = self.article_image_urls[target_article_index]
        
        # 如果图片 URL 发生变化，则重新加载
        if new_image_url != self.current_image_url:
            self.current_image_url = new_image_url
            if new_image_url and new_image_url != '#':
                self._load_and_display_sidebar_image(new_image_url)
            else:
                self._display_placeholder_image("无图片")

        # 返回 "break" 停止 Tkinter 对滚动事件的默认处理，但我们希望保持默认滚动，所以不返回。
        # return 'break' 
        
    def _display_placeholder_image(self, text):
        """显示图片占位符文本并清除任何现有图片。"""
        # 清除旧图片引用
        self.sidebar_image_ref = None 
        # 同时清除 Label 上的 image 和更新文本
        self.image_display_label.config(text=text, image='') 
        
    def _process_and_display_sidebar_image(self, image_data, url):
        """
        在主线程中将图片数据转换为 Tkinter 图像对象并显示在侧边栏 Label 上。
        """
        if not Image or not ImageTk:
             self._display_placeholder_image("[图片加载失败: Pillow 库未安装]")
             return
             
        # 防止加载过程中，用户快速滚动导致加载了旧的图片
        if url != self.current_image_url:
             return
             
        try:
            image_stream = io.BytesIO(image_data)
            pil_image = Image.open(image_stream)
            
            # 计算缩放尺寸，以适应右侧面板
            # 假定 Label 占据 1/3 宽度，并留出边距 (1/3 * 480 = 160)
            max_width = int(APP_WIDTH / 3) - 10 # 留出边框和 padding
            max_height = APP_HEIGHT - 60 # 留出顶部输入框和底部边距
            
            width, height = pil_image.size
            
            if width > max_width or height > max_height:
                # 计算缩放比例，取最小的，确保图片能完全放下
                ratio = min(max_width / width, max_height / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                # 使用 LANCZOS 获得高质量缩放
                pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                 
            tk_image = ImageTk.PhotoImage(pil_image)
            
            # 存储引用到实例变量中，防止被垃圾回收
            self.sidebar_image_ref = tk_image

            # 更新 Label: 清除文本，显示图片
            self.image_display_label.config(image=self.sidebar_image_ref, text="")
            
        except Exception as e:
            # Tkinter 图像处理失败
            self._display_placeholder_image(f"[图片处理失败: {url[:30]}...]")
            self.current_image_url = "#error" # 标记为错误，避免重复尝试加载

    def _load_and_display_sidebar_image(self, url):
        """
        在后台线程中加载图片，并在主线程中调度显示在侧边栏 Label 上。
        """
        
        # 如果当前URL已经是占位符或错误状态，则不重复加载
        if url == self.current_image_url:
            return
            
        self._display_placeholder_image("正在加载图片...")
        self.current_image_url = url
        
        def fetch_image():
            try:
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                image_data = response.content
                
                # 成功后，在主线程中处理图像对象和插入
                self.master.after(0, lambda: self._process_and_display_sidebar_image(image_data, url))
            
            except requests.exceptions.RequestException as e:
                # 图像加载失败，在主线程中插入错误提示
                # 修复: 通过默认参数捕获 'e' 的值 (NameError 修复)
                self.master.after(0, lambda error_e=e: self._display_placeholder_image(f"[图片加载失败: {error_e}]"))
                self.current_image_url = "#error"
            except Exception as e:
                # 修复: 通过默认参数捕获 'e' 的值 (NameError 修复)
                self.master.after(0, lambda error_e=e: self._display_placeholder_image(f"[图片未知错误: {error_e}]"))
                self.current_image_url = "#error"

        # 仅在 Pillow 成功导入时才尝试加载图片
        if Image and ImageTk:
            # 启动后台线程
            thread = threading.Thread(target=fetch_image)
            thread.daemon = True
            thread.start()
        else:
             self.master.after(0, lambda: self._display_placeholder_image("[图片加载失败: Pillow 库未安装]"))


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
        在主线程中接收解析结果并更新 UI。
        """
        
        self._clear_content(initial=False) 
        self.article_image_urls = [] # 清空缓存的图片 URL
        
        if not result['success']:
            # 处理错误情况
            error_message = result.get('error', '加载失败，无详细错误信息。')
            self.title_label.config(text="博客标题: 错误")
            self.feed_desc_var.set(f"描述: 加载失败\n{error_message}")
            self._display_placeholder_image("加载失败")
            return
            
        feed = result['feed']
        
        # 1. 更新标题和描述
        feed_title = feed.feed.get('title', '未知标题')
        feed_description = feed.feed.get('subtitle', feed.feed.get('description', '无描述信息'))
        
        self.title_label.config(text=f"博客标题: {feed_title}")
        self.feed_desc_var.set(f"描述: {feed_description}") 

        # 2. 插入文章内容和处理主图
        self.content_text.config(state='normal')
        
        if not feed.entries:
            self.content_text.insert('1.0', "此订阅源加载成功，但目前没有文章内容。")
        
        for entry_index, entry in enumerate(feed.entries):
            # --- 1. 获取信息 ---
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
                
            # 提取文本和图片URL
            summary_cleaned_with_placeholders, image_urls = self._extract_text_and_images(summary)
            
            # 移除占位符，确保 Text 控件中只有纯文本
            summary_cleaned = re.sub(r'\[\[TEMP_IMG_LOC_\d+\]\]', '', summary_cleaned_with_placeholders).strip()

            # 缓存每篇文章的第一个图片 URL
            first_image_url = image_urls[0] if image_urls else '#'
            self.article_image_urls.append(first_image_url)
            
            # --- 2. 插入内容，创建新排版 ---
            
            # 插入标记 (Mark) 用于定位文章的起始位置
            mark_name = f"article_{entry_index}"
            self.content_text.mark_set(mark_name, tk.END) # 将标记设置在文章起始点
            self.content_text.mark_gravity(mark_name, 'left') # 确保标记在文本插入后保持在起始位置

            # 插入标题
            start_index = self.content_text.index(tk.END)
            self.content_text.insert(tk.END, title, 'title') 
            end_index_of_title = self.content_text.index(tk.END)
            self.content_text.tag_add('link', start_index, end_index_of_title)
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
        
        # 3. 初始处理侧边栏图片：显示第一篇文章的图片
        if self.article_image_urls:
            self._load_and_display_sidebar_image(self.article_image_urls[0])
        else:
            self._display_placeholder_image("无图片")


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
        
        # 清除侧边栏图片
        self.current_image_url = None
        self._display_placeholder_image("无图片或正在加载...")

    def _open_link(self, event, url=None):
        """处理链接点击事件，在外部浏览器中打开 URL。"""
        if url and url != '#':
            import webbrowser
            webbrowser.open_new(url)
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
