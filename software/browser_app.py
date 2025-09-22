import sys
import os
from urllib.parse import urlparse
import wx
import wx.html2 as webview

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
        print("🐧 Linux 使用 WebKitGTK (需安装 libwebkitgtk-6.0-dev)")
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

        self.create_toolbar(panel, vbox)

        # 核心修改部分
        self.browser = None
        try:
            if EDGE_AVAILABLE and sys.platform.startswith("win"):
                self.browser = webview.WebView.New(panel, backend=webview.WebViewBackendEdge)
                print("✅ 使用 Edge WebView2 backend")
            else:
                self.browser = webview.WebView.New(panel)
                print("ℹ️ 使用默认 WebView backend")
        except Exception as e:
            print("❌ WebView 创建失败:", e)
            self.browser = wx.StaticText(panel, label="WebView 初始化失败\n" + str(e))

        # 检查 self.browser 是否为 WebView 对象，如果是，则添加事件绑定
        if isinstance(self.browser, webview.WebView):
            try:
                self.browser.Bind(webview.EVT_WEBVIEW_LOADED, self.on_loaded)
                self.browser.Bind(webview.EVT_WEBVIEW_NAVIGATING, self.on_navigating)
                self.browser.Bind(webview.EVT_WEBVIEW_NAVIGATED, self.on_navigated)
            except Exception as e:
                print("⚠️ 绑定 WebView 事件失败:", e)

        vbox.Add(self.browser, proportion=1, flag=wx.EXPAND)
        panel.SetSizer(vbox)

        # 事件绑定
        self.btn_back.Bind(wx.EVT_BUTTON, self.on_back)
        self.btn_forward.Bind(wx.EVT_BUTTON, self.on_forward)
        self.btn_reload.Bind(wx.EVT_BUTTON, self.on_reload)
        self.btn_home.Bind(wx.EVT_BUTTON, self.on_home)
        self.btn_go.Bind(wx.EVT_BUTTON, self.on_go)
        self.url_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_go)

        self.home_url = "https://www.winddine.top"
        self.load_url(self.home_url)
        wx.CallAfter(self.update_nav_buttons)

    def create_menu_bar(self):
        menubar = wx.MenuBar()
        file_menu = wx.Menu()

        mi_refresh = file_menu.Append(wx.ID_REFRESH, "刷新\tCtrl+R", "刷新当前页面")
        mi_home = file_menu.Append(wx.NewIdRef(), "主页\tCtrl+H", "跳到主页")
        file_menu.AppendSeparator()
        mi_exit = file_menu.Append(wx.ID_EXIT, "退出\tCtrl+Q", "退出程序")

        menubar.Append(file_menu, "文件")
        self.SetMenuBar(menubar)

        self.Bind(wx.EVT_MENU, self.on_reload, mi_refresh)
        self.Bind(wx.EVT_MENU, self.on_home, mi_home)
        self.Bind(wx.EVT_MENU, self.on_quit, mi_exit)

    def create_toolbar(self, panel, vbox):
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

    def on_quit(self, event):
        self.Close()

    def normalize_url(self, url: str) -> str:
        url = url.strip()
        if not url:
            return ""
        parsed = urlparse(url)
        if not parsed.scheme:
            return "http://" + url
        return url

    def load_url(self, url: str):
        if not url or not isinstance(self.browser, webview.WebView):
            return
        url = self.normalize_url(url)
        try:
            self.browser.LoadURL(url)
        except Exception as e:
            print("load_url failed:", e)
        self.url_ctrl.SetValue(url)
        wx.CallLater(200, self.update_nav_buttons)

    def on_back(self, evt):
        if not isinstance(self.browser, webview.WebView): return
        try:
            if self.browser.CanGoBack():
                self.browser.GoBack()
        except Exception:
            pass

    def on_forward(self, evt):
        if not isinstance(self.browser, webview.WebView): return
        try:
            if self.browser.CanGoForward():
                self.browser.GoForward()
        except Exception:
            pass

    def on_reload(self, evt):
        if not isinstance(self.browser, webview.WebView): return
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
        if not isinstance(self.browser, webview.WebView): return
        try:
            url = evt.GetURL()
            if url:
                self.url_ctrl.SetValue(url)
        except Exception:
            pass

    def on_navigated(self, evt):
        if not isinstance(self.browser, webview.WebView): return
        try:
            url = evt.GetURL()
            if url:
                self.url_ctrl.SetValue(url)
        except Exception:
            pass
        wx.CallAfter(self.update_nav_buttons)

    def on_loaded(self, evt):
        if not isinstance(self.browser, webview.WebView): return
        try:
            url = evt.GetURL()
            if url:
                self.url_ctrl.SetValue(url)
        except Exception:
            pass
        wx.CallAfter(self.update_nav_buttons)

    def update_nav_buttons(self):
        if not isinstance(self.browser, webview.WebView):
            self.btn_back.Enable(False)
            self.btn_forward.Enable(False)
            return

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
