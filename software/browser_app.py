import sys
import os
from urllib.parse import urlparse
import wx
import wx.html2 as webview

# -----------------------
# 平台窗口尺寸设置
# -----------------------
if sys.platform.startswith("linux"):
    WINDOW_WIDTH = 480
    WINDOW_HEIGHT = 320
    FRAMELESS = True
else:
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600
    FRAMELESS = False

# -----------------------
# WebView2 路径查找
# -----------------------
def find_webview2_dll():
    possible_paths = [
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Microsoft", "EdgeWebView", "Application", "WebView2Loader.dll"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Microsoft", "EdgeWebView", "Application", "WebView2Loader.dll"),
        "WebView2Loader.dll",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def setup_webview_backend():
    if sys.platform.startswith("win"):
        webview2_path = find_webview2_dll()
        if webview2_path:
            os.environ["WEBVIEW2_CORE_DLL_PATH"] = os.path.dirname(webview2_path)
            print("✅ 找到 WebView2Loader.dll:", webview2_path)
        else:
            print("⚠️ 未找到 WebView2Loader.dll，可能会回退到 IE")

        try:
            return webview.WebView.IsBackendAvailable(webview.WebViewBackendEdge)
        except Exception:
            return False

    elif sys.platform == "darwin":
        print("🍎 macOS 使用系统 WebKit")
        return True

    elif sys.platform.startswith("linux"):
        print("🐧 Linux 使用 WebKitGTK (需安装 libwebkit2gtk)")
        return True

    else:
        print("未知平台，尝试默认 backend")
        return False

EDGE_AVAILABLE = setup_webview_backend()

class BrowserFrame(wx.Frame):
    def __init__(self):
        style = wx.DEFAULT_FRAME_STYLE
        if FRAMELESS:
            style = wx.NO_BORDER

        super().__init__(None, title="Maqa Browser", size=(WINDOW_WIDTH, WINDOW_HEIGHT), style=style)

        # --- 新增：创建菜单栏 ---
        self.create_menu_bar()

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # 工具栏
        toolbar = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_back = wx.Button(panel, label="←")
        self.btn_forward = wx.Button(panel, label="→")
        self.btn_reload = wx.Button(panel, label="⟳")
        self.btn_home = wx.Button(panel, label="主页")

        for btn in (self.btn_back, self.btn_forward, self.btn_reload, self.btn_home):
            toolbar.Add(btn, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=6)

        self.url_ctrl = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        toolbar.Add(self.url_ctrl, proportion=1, flag=wx.EXPAND)

        self.btn_go = wx.Button(panel, label="Go")
        toolbar.Add(self.btn_go, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=6)

        if sys.platform.startswith("linux"):
            self.btn_close = wx.Button(panel, label="X")
            toolbar.Add(self.btn_close, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=6)

        vbox.Add(toolbar, flag=wx.EXPAND | wx.ALL, border=6)

        # WebView 部分
        try:
            if EDGE_AVAILABLE and sys.platform.startswith("win"):
                self.browser = webview.WebView.New(panel, backend=webview.WebViewBackendEdge)
                print("✅ 使用 Edge WebView2 backend")
            else:
                self.browser = webview.WebView.New(panel)
                print("ℹ️ 使用默认 WebView backend")
        except Exception as e:
            print("❌ WebView 创建失败:", e)
            self.browser = wx.StaticText(panel, label="WebView 初始化失败")

        vbox.Add(self.browser, proportion=1, flag=wx.EXPAND)
        panel.SetSizer(vbox)

        # 事件绑定
        self.btn_back.Bind(wx.EVT_BUTTON, self.on_back)
        self.btn_forward.Bind(wx.EVT_BUTTON, self.on_forward)
        self.btn_reload.Bind(wx.EVT_BUTTON, self.on_reload)
        self.btn_home.Bind(wx.EVT_BUTTON, self.on_home)
        self.btn_go.Bind(wx.EVT_BUTTON, self.on_go)
        self.url_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_go)

        try:
            self.browser.Bind(webview.EVT_WEBVIEW_LOADED, self.on_loaded)
        except Exception:
            pass
        try:
            self.browser.Bind(webview.EVT_WEBVIEW_NAVIGATING, self.on_navigating)
        except Exception:
            pass
        try:
            self.browser.Bind(webview.EVT_WEBVIEW_NAVIGATED, self.on_navigated)
        except Exception:
            pass

        self.home_url = "https://www.winddine.top"
        self.load_url(self.home_url)
        wx.CallAfter(self.update_nav_buttons)

    def create_menu_bar(self):
        menubar = wx.MenuBar()

        file_menu = wx.Menu()

        # 刷新
        # 使用标准 ID 或自定义 ID
        mi_refresh = file_menu.Append(wx.ID_REFRESH, "刷新\tCtrl+R", "刷新当前页面")

        # 主页
        # 自定义 ID
        mi_home = file_menu.Append(wx.NewIdRef(), "主页\tCtrl+H", "跳到主页")

        # 分隔线
        file_menu.AppendSeparator()

        # 退出
        mi_exit = file_menu.Append(wx.ID_EXIT, "退出\tCtrl+Q", "退出程序")

        menubar.Append(file_menu, "文件")

        self.SetMenuBar(menubar)

        # 绑定菜单事件
        self.Bind(wx.EVT_MENU, self.on_reload, mi_refresh)
        self.Bind(wx.EVT_MENU, self.on_home, mi_home)
        self.Bind(wx.EVT_MENU, self.on_quit, mi_exit)

        # macOS: 常见约定 “退出” 用 Cmd+Q
        # Windows/Linux: Ctrl+Q
        # wx will parse "\tCtrl+Q" 或 "\tCmd+Q" label 来显示快捷键，并通常自动处理 Command key 在 macOS
        # 如果你想强制支持 Cmd 在 macOS，也可以用 AcceleratorTable

    def on_quit(self, event):
        self.Close()

    # 你原来的事件和方法保持不变
    def normalize_url(self, url: str) -> str:
        url = url.strip()
        if not url:
            return ""
        parsed = urlparse(url)
        if not parsed.scheme:
            return "http://" + url
        return url

    def load_url(self, url: str):
        if not url:
            return
        url = self.normalize_url(url)
        try:
            self.browser.LoadURL(url)
        except Exception:
            try:
                self.browser.LoadUrl(url)
            except Exception as e:
                print("load_url failed:", e)
        self.url_ctrl.SetValue(url)
        wx.CallLater(200, self.update_nav_buttons)

    def on_back(self, evt):
        try:
            if self.browser.CanGoBack():
                self.browser.GoBack()
        except Exception:
            pass

    def on_forward(self, evt):
        try:
            if self.browser.CanGoForward():
                self.browser.GoForward()
        except Exception:
            pass

    def on_reload(self, evt):
        # 用菜单“刷新”触发的也调用这个
        try:
            self.browser.Reload()
        except Exception:
            pass

    def on_home(self, evt):
        self.load_url(self.home_url)

    def on_go(self, evt):
        url = self.url_ctrl.GetValue()
        self.load_url(url)

    def on_navigating(self, evt):
        try:
            url = evt.GetURL()
            if url:
                self.url_ctrl.SetValue(url)
        except Exception:
            pass

    def on_navigated(self, evt):
        try:
            url = evt.GetURL()
            if url:
                self.url_ctrl.SetValue(url)
        except Exception:
            pass
        wx.CallAfter(self.update_nav_buttons)

    def on_loaded(self, evt):
        try:
            url = evt.GetURL()
            if url:
                self.url_ctrl.SetValue(url)
        except Exception:
            pass
        wx.CallAfter(self.update_nav_buttons)

    def update_nav_buttons(self):
        try:
            can_back = self.browser.CanGoBack()
        except Exception:
            can_back = False
        try:
            can_forward = self.browser.CanGoForward()
        except Exception:
            can_forward = False

        self.btn_back.Enable(can_back)
        self.btn_forward.Enable(can_forward)

def create_browser_window():
    app = wx.App(False)
    frame = BrowserFrame()
    frame.Show()
    app.MainLoop()

if __name__ == "__main__":
    create_browser_window()
