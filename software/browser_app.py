# software/browser_app.py
import sys
from urllib.parse import urlparse
import wx
import wx.html2 as webview

# --- 平台判断逻辑（保留 Linux 与 非 Linux 的不同窗口尺寸） ---
if sys.platform.startswith('linux'):
    WINDOW_WIDTH = 480
    WINDOW_HEIGHT = 320
    FRAMELESS = True
else:
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600
    FRAMELESS = False


class BrowserFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        style = wx.DEFAULT_FRAME_STYLE
        if FRAMELESS:
            # 无边框模式下仍然保留拖动/关闭的基本功能可以按需增强
            style = wx.NO_BORDER

        super().__init__(None, title="Browser", size=(WINDOW_WIDTH, WINDOW_HEIGHT), style=style)

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # 顶部工具栏（后退/前进/刷新/主页 + 地址栏 + 转到）
        toolbar = wx.BoxSizer(wx.HORIZONTAL)

        self.btn_back = wx.Button(panel, label="←")
        self.btn_forward = wx.Button(panel, label="→")
        self.btn_reload = wx.Button(panel, label="⟳")
        self.btn_home = wx.Button(panel, label="主页")

        for btn in (self.btn_back, self.btn_forward, self.btn_reload, self.btn_home):
            toolbar.Add(btn, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=6)

        # 地址栏（注意：不要同时使用 wx.EXPAND 和 对齐标志）
        self.url_ctrl = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        # 把地址栏设置为可扩展（proportion=1），但不同时使用对齐标志
        toolbar.Add(self.url_ctrl, proportion=1, flag=wx.EXPAND)

        # Go 按钮：不 expand，但垂直居中
        self.btn_go = wx.Button(panel, label="Go")
        toolbar.Add(self.btn_go, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=6)

        vbox.Add(toolbar, flag=wx.EXPAND | wx.ALL, border=6)

        # WebView 容器（兼容不同 wxPython 版本的构造）
        try:
            self.browser = webview.WebView.New(panel)
        except Exception:
            # 旧版本 API
            self.browser = webview.WebView(panel, -1)

        vbox.Add(self.browser, proportion=1, flag=wx.EXPAND)

        panel.SetSizer(vbox)

        # 事件绑定
        self.btn_back.Bind(wx.EVT_BUTTON, self.on_back)
        self.btn_forward.Bind(wx.EVT_BUTTON, self.on_forward)
        self.btn_reload.Bind(wx.EVT_BUTTON, self.on_reload)
        self.btn_home.Bind(wx.EVT_BUTTON, self.on_home)
        self.btn_go.Bind(wx.EVT_BUTTON, self.on_go)
        self.url_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_go)

        # WebView 导航相关事件：尽量使用兼容性的事件名
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

        # 默认主页
        self.home_url = "https://www.winddine.top"
        # 加载起始页面
        self.load_url(self.home_url)

        # 初次更新按钮状态
        wx.CallAfter(self.update_nav_buttons)

    def normalize_url(self, url: str) -> str:
        """确保 URL 带有 scheme（若用户输入 example.com 自动补 http://）。"""
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
            # 目前 webview API 的常见方法名
            self.browser.LoadURL(url)
        except Exception:
            try:
                self.browser.LoadUrl(url)
            except Exception as e:
                print("load_url failed:", e)
        # 立即把地址回写到地址栏（有时 webview 会稍后再更新）
        self.url_ctrl.SetValue(url)
        wx.CallLater(200, self.update_nav_buttons)

    # 事件处理器
    def on_back(self, evt):
        try:
            if self.browser.CanGoBack():
                self.browser.GoBack()
        except Exception:
            try:
                self.browser.RunScript("history.back();")
            except Exception:
                pass

    def on_forward(self, evt):
        try:
            if self.browser.CanGoForward():
                self.browser.GoForward()
        except Exception:
            try:
                self.browser.RunScript("history.forward();")
            except Exception:
                pass

    def on_reload(self, evt):
        try:
            self.browser.Reload()
        except Exception:
            try:
                self.browser.RunScript("location.reload();")
            except Exception:
                pass

    def on_home(self, evt):
        self.load_url(self.home_url)

    def on_go(self, evt):
        url = self.url_ctrl.GetValue()
        self.load_url(url)

    def on_navigating(self, evt):
        # 当开始导航时可用于显示加载状态（这里简单更新地址栏）
        try:
            url = evt.GetURL()
            if url:
                self.url_ctrl.SetValue(url)
        except Exception:
            pass

    def on_navigated(self, evt):
        # 导航完成（如果存在此事件），更新地址栏和按钮
        try:
            url = evt.GetURL()
            if url:
                self.url_ctrl.SetValue(url)
        except Exception:
            pass
        wx.CallAfter(self.update_nav_buttons)

    def on_loaded(self, evt):
        # 页面加载完成，更新地址栏与导航按钮
        try:
            url = evt.GetURL()
            if url:
                self.url_ctrl.SetValue(url)
        except Exception:
            # 在某些后端上 event.GetURL 可能不可用，尝试从 browser 获取
            try:
                if hasattr(self.browser, 'GetCurrentURL'):
                    url = self.browser.GetCurrentURL()
                elif hasattr(self.browser, 'GetURL'):
                    url = self.browser.GetURL()
                else:
                    url = None
                if url:
                    self.url_ctrl.SetValue(url)
            except Exception:
                pass
        wx.CallAfter(self.update_nav_buttons)

    def update_nav_buttons(self):
        # 根据浏览器当前状态启用/禁用后退/前进按钮
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
    """
    对外接口：创建并运行浏览器窗口（阻塞，启动 wx 的主循环）。
    这个函数在你从主程序以子进程方式启动 browser 时被调用，
    也可以单独运行 `python -m software.browser_app` / `python software/browser_app.py`.
    """
    app = wx.App(False)
    frame = BrowserFrame()
    frame.Show()
    app.MainLoop()


# 保持脚本可直接运行（用于测试或直接启动）
if __name__ == '__main__':
    create_browser_window()
