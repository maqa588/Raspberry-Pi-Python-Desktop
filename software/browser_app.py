import sys
import os
from urllib.parse import urlparse
import wx
import wx.html2 as webview

# -----------------------
# Platform-specific configurations
# -----------------------
IS_LINUX = sys.platform.startswith("linux")

if IS_LINUX:
    WINDOW_WIDTH = 480
    WINDOW_HEIGHT = 320
    FRAMELESS = True
    # For Linux, we move buttons to the menu bar to avoid GTK layout warnings.
    # The toolbar will only contain the URL bar.
else:
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600
    FRAMELESS = False
    # For other platforms, we keep the toolbar as-is.

# -----------------------
# WebView2 path finder
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
            print("✅ Found WebView2Loader.dll:", webview2_path)
        else:
            print("⚠️ WebView2Loader.dll not found, may fall back to IE")
        try:
            return webview.WebView.IsBackendAvailable(webview.WebViewBackendEdge)
        except Exception:
            return False
    elif sys.platform == "darwin":
        print("🍎 macOS uses the system WebKit")
        return True
    elif IS_LINUX:
        print("🐧 Linux uses WebKitGTK (requires libwebkit2gtk-4.0-dev/libwebkit2gtk-6.0-dev)")
        print("--- Diagnostic information ---")
        try:
            is_gtk_backend_available = webview.WebView.IsBackendAvailable(webview.WebViewBackendWebKit)
            print(f"ℹ️ WebKitGTK backend availability: {is_gtk_backend_available}")
        except Exception as e:
            print(f"❌ Error checking WebKitGTK backend availability: {e}")
        print("----------------")
        return True
    else:
        print("Unknown platform, attempting default backend")
        return False

EDGE_AVAILABLE = setup_webview_backend()

class BrowserFrame(wx.Frame):
    def __init__(self):
        style = wx.DEFAULT_FRAME_STYLE
        if FRAMELESS:
            style = wx.NO_BORDER

        super().__init__(None, title="Maqa Browser", size=(WINDOW_WIDTH, WINDOW_HEIGHT), style=style)

        self.create_menu_bar()

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.create_toolbar(panel, vbox)

        self.browser = None
        try:
            if EDGE_AVAILABLE and sys.platform.startswith("win"):
                self.browser = webview.WebView.New(panel, backend=webview.WebViewBackendEdge)
                print("✅ Using Edge WebView2 backend")
            else:
                self.browser = webview.WebView.New(panel)
                print("ℹ️ Using default WebView backend")
        except Exception as e:
            print("❌ WebView creation failed:", e)
            self.browser = wx.StaticText(panel, label="WebView initialization failed\n" + str(e))

        if isinstance(self.browser, webview.WebView):
            try:
                self.browser.Bind(webview.EVT_WEBVIEW_LOADED, self.on_loaded)
                self.browser.Bind(webview.EVT_WEBVIEW_NAVIGATING, self.on_navigating)
                self.browser.Bind(webview.EVT_WEBVIEW_NAVIGATED, self.on_navigated)
            except Exception as e:
                print("⚠️ Failed to bind WebView events:", e)

        vbox.Add(self.browser, proportion=1, flag=wx.EXPAND)
        panel.SetSizer(vbox)

        # Event binding
        self.url_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_go)

        if not IS_LINUX:
            self.btn_back.Bind(wx.EVT_BUTTON, self.on_back)
            self.btn_forward.Bind(wx.EVT_BUTTON, self.on_forward)
            self.btn_reload.Bind(wx.EVT_BUTTON, self.on_reload)
            self.btn_home.Bind(wx.EVT_BUTTON, self.on_home)
            self.btn_go.Bind(wx.EVT_BUTTON, self.on_go)

        self.home_url = "https://www.winddine.top"
        self.load_url(self.home_url)
        wx.CallAfter(self.update_nav_buttons)

    def create_menu_bar(self):
        menubar = wx.MenuBar()
        nav_menu = wx.Menu()

        mi_back = nav_menu.Append(wx.ID_BACKWARD, "后退\tCtrl+Left", "返回上一页")
        mi_forward = nav_menu.Append(wx.ID_FORWARD, "前进\tCtrl+Right", "前进到下一页")
        mi_reload = nav_menu.Append(wx.ID_REFRESH, "刷新\tCtrl+R", "刷新当前页面")
        nav_menu.AppendSeparator()
        mi_home = nav_menu.Append(wx.NewIdRef(), "主页\tCtrl+H", "跳到主页")
        
        if IS_LINUX:
            mi_go = nav_menu.Append(wx.NewIdRef(), "Go\tCtrl+G", "访问输入的URL")
            self.Bind(wx.EVT_MENU, self.on_go, mi_go)

        nav_menu.AppendSeparator()
        mi_exit = nav_menu.Append(wx.ID_EXIT, "退出\tCtrl+Q", "退出程序")
        
        menubar.Append(nav_menu, "导航")
        self.SetMenuBar(menubar)

        self.Bind(wx.EVT_MENU, self.on_back, mi_back)
        self.Bind(wx.EVT_MENU, self.on_forward, mi_forward)
        self.Bind(wx.EVT_MENU, self.on_reload, mi_reload)
        self.Bind(wx.EVT_MENU, self.on_home, mi_home)
        self.Bind(wx.EVT_MENU, self.on_quit, mi_exit)

    def create_toolbar(self, panel, vbox):
        toolbar = wx.BoxSizer(wx.HORIZONTAL)
        
        if not IS_LINUX:
            self.btn_back = wx.Button(panel, id=wx.ID_BACKWARD, label="后退")
            self.btn_forward = wx.Button(panel, id=wx.ID_FORWARD, label="前进")
            self.btn_reload = wx.Button(panel, id=wx.ID_REFRESH, label="刷新")
            self.btn_home = wx.Button(panel, id=wx.ID_HOME, label="主页")
            self.btn_go = wx.Button(panel, label="Go")
            
            toolbar.Add(self.btn_back, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=6)
            toolbar.Add(self.btn_forward, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=6)
            toolbar.Add(self.btn_reload, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=6)
            toolbar.Add(self.btn_home, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=6)

        self.url_ctrl = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        toolbar.Add(self.url_ctrl, proportion=1, flag=wx.EXPAND)

        if not IS_LINUX:
            toolbar.Add(self.btn_go, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=6)

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
        self.update_nav_buttons()

    def on_forward(self, evt):
        if not isinstance(self.browser, webview.WebView): return
        try:
            if self.browser.CanGoForward():
                self.browser.GoForward()
        except Exception:
            pass
        self.update_nav_buttons()

    def on_reload(self, evt):
        if not isinstance(self.browser, webview.WebView): return
        try:
            self.browser.Reload()
        except Exception:
            pass
        self.update_nav_buttons()

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
        self.update_nav_buttons()

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
            if not IS_LINUX:
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
        
        if not IS_LINUX:
            self.btn_back.Enable(can_back)
            self.btn_forward.Enable(can_forward)

def create_browser_window():
    app = wx.App(False)
    frame = BrowserFrame()
    frame.Show()
    app.MainLoop()

if __name__ == "__main__":
    create_browser_window()
