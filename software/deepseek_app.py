import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import requests
import json
import threading
import time
import sys
import os

current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file_path))
sys.path.insert(0, project_root)

# 在macOS上运行时，Tkinter可能会有IMKCFRunLoopWakeUpReliable错误，这行代码用于抑制该错误
if sys.platform == 'darwin':
    try:
        from AppKit import NSApp # type: ignore
        NSApp.sharedApplication().setActivationPolicy_(0)
    except ImportError:
        pass

from system.config import WINDOW_WIDTH, WINDOW_HEIGHT
from system.button.about import show_system_about, show_developer_about

class DeepSeekChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DeepSeek AI 聊天助手")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg="#f0f0f0")
        
        # API配置
        self.api_key = ""
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        
        # 存储对话历史
        self.conversation_history = [
            {"role": "system", "content": "你是一个有用的助手。"}
        ]
        
        # 创建菜单和界面
        self.create_menu()
        self.create_widgets()

    def create_widgets(self):
        """创建应用程序的GUI组件"""
        # 主框架，现在在第1行
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重，使界面可调整大小
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)  # 更改为第1行
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # API密钥输入区域
        api_frame = ttk.Frame(main_frame)
        api_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(api_frame, text="DeepSeek API密钥:").pack(side=tk.LEFT)
        self.api_entry = ttk.Entry(api_frame, width=50)
        self.api_entry.pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)
        
        # 创建一个新框架来容纳对话记录和用户输入，实现左右布局
        chat_and_input_frame = ttk.Frame(main_frame)
        chat_and_input_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        # 调整列权重，实现2:3的宽度比例
        chat_and_input_frame.columnconfigure(0, weight=2)
        chat_and_input_frame.columnconfigure(1, weight=3)
        chat_and_input_frame.rowconfigure(0, weight=1)
        
        # 聊天记录显示区域（左侧）
        ttk.Label(chat_and_input_frame, text="对话记录:").grid(row=0, column=0, sticky=tk.N+tk.W, pady=(0, 5))
        self.chat_display = scrolledtext.ScrolledText(
            chat_and_input_frame, 
            width=80, 
            height=20, 
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.chat_display.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        # 插入浅色提示文本
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert("1.0", "对话记录会输出在这里...", 'placeholder')
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.tag_config('placeholder', foreground='gray')
        
        # 用户输入区域（右侧）
        ttk.Label(chat_and_input_frame, text="你的消息:").grid(row=0, column=1, sticky=tk.N+tk.W, pady=(0, 5))
        self.user_input = scrolledtext.ScrolledText(
            chat_and_input_frame, 
            width=80, 
            height=20,  # 高度与聊天记录区相同
            wrap=tk.WORD
        )
        self.user_input.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        self.user_input.focus()

        # 浅色提示文本的逻辑
        self.user_input.insert("1.0", "你的消息应该输入在这里...", 'placeholder')
        self.user_input.tag_config('placeholder', foreground='gray')
        
        self.user_input.bind("<FocusIn>", self.on_user_input_focus_in)
        self.user_input.bind("<FocusOut>", self.on_user_input_focus_out)

        # 按钮和状态栏区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.send_button = ttk.Button(
            button_frame, 
            text="发送消息", 
            command=self.send_message
        )
        self.send_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.clear_button = ttk.Button(
            button_frame, 
            text="清空对话", 
            command=self.clear_conversation
        )
        self.clear_button.pack(side=tk.LEFT, padx=(0, 10))

        # 状态栏，放置在按钮区域的最右边
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(button_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(10, 0))
        
        # 绑定Enter键发送消息（Ctrl+Enter）
        self.user_input.bind("<Control-Return>", lambda event: self.send_message())
    
    def on_user_input_focus_in(self, event):
        """当输入框获得焦点时，如果内容是提示文本，则清空它"""
        if self.user_input.get("1.0", "end-1c") == "你的消息应该输入在这里...":
            self.user_input.delete("1.0", tk.END)
            self.user_input.tag_remove('placeholder', "1.0", tk.END)
            # 移除此行，让Tkinter使用系统默认文本颜色，以适应深色模式
            # self.user_input.config(foreground='black')

    def on_user_input_focus_out(self, event):
        """当输入框失去焦点时，如果内容为空，则重新添加提示文本"""
        if not self.user_input.get("1.0", "end-1c").strip():
            self.user_input.delete("1.0", tk.END)
            self.user_input.insert("1.0", "你的消息应该输入在这里...", 'placeholder')

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
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        # 文件菜单
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="导出对话...", command=self.export_conversation)
        file_menu.add_command(label="导入API密钥...", command=self.import_api_key)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)

        # 关于菜单
        about_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="关于", menu=about_menu)
        about_menu.add_command(label="系统信息", command=lambda:show_system_about(self.root))
        about_menu.add_command(label="开发者信息", command=lambda:show_developer_about(self.root))

    def create_custom_menu(self):
        """创建自定义顶部栏（非 macOS 或 Windows 风格）"""
        top_bar_frame = tk.Frame(self.root, bg="#f0f0f0", height=30, bd=1, relief=tk.RAISED)
        # 将顶部栏放置在网格的第0行，确保它始终在最顶部
        top_bar_frame.grid(row=0, column=0, sticky=tk.W+tk.E)
        
        # 文件菜单按钮
        file_mb = tk.Menubutton(top_bar_frame, text="文件", activebackground="#e1e1e1", bg="#f0f0f0", relief=tk.FLAT)
        file_mb.pack(side=tk.LEFT, padx=5, pady=2)
        file_menu = tk.Menu(file_mb, tearoff=0)
        file_menu.add_command(label="导出对话...", command=self.export_conversation)
        file_menu.add_command(label="导入API密钥...", command=self.import_api_key)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        file_mb.config(menu=file_menu)
        
        # 关于菜单按钮
        about_mb = tk.Menubutton(top_bar_frame, text="关于", activebackground="#e1e1e1", bg="#f0f0f0", relief=tk.FLAT)
        about_mb.pack(side=tk.LEFT, padx=5, pady=2)
        about_menu = tk.Menu(about_mb, tearoff=0)
        about_menu.add_command(label="系统信息", command=lambda:show_system_about(self.root))
        about_menu.add_command(label="开发者信息", command=lambda:show_developer_about(self.root))
        about_mb.config(menu=about_menu)

        quit_btn = tk.Button(top_bar_frame, text="X", command=self.root.quit, relief=tk.FLAT, bg="#f0f0f0", fg="red", activebackground="#e1e1e1")
        quit_btn.pack(side=tk.RIGHT, padx=5, pady=2)
    
    def export_conversation(self):
        """导出当前聊天记录到TXT文件"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="保存对话记录"
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                conversation_text = self.chat_display.get("1.0", tk.END)
                f.write(conversation_text)
            messagebox.showinfo("成功", f"对话记录已成功导出到：\n{file_path}")

    def import_api_key(self):
        """从TXT文件导入API密钥"""
        file_path = filedialog.askopenfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="导入API密钥"
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    key = f.read().strip()
                    self.api_entry.delete(0, tk.END)
                    self.api_entry.insert(0, key)
                    messagebox.showinfo("成功", "API密钥已成功导入！")
            except Exception as e:
                messagebox.showerror("错误", f"导入密钥失败：\n{e}")

    def send_message(self):
        """处理用户发送消息的逻辑"""
        user_message = self.user_input.get("1.0", tk.END).strip()
        
        # 如果是提示文本，则不发送
        if user_message == "你的消息应该输入在这里...":
            user_message = ""
        
        api_key = self.api_entry.get().strip() or self.api_key
        
        if not user_message:
            messagebox.showwarning("输入错误", "请输入消息内容")
            return
            
        if not api_key:
            messagebox.showwarning("API密钥错误", "请输入DeepSeek API密钥")
            return
            
        # 禁用发送按钮，防止重复发送
        self.send_button.config(state=tk.DISABLED)
        self.status_var.set("正在发送消息...")
        
        # 在聊天记录中显示用户消息
        self.display_message("你", user_message)
        
        # 清空输入框并恢复提示文本
        self.user_input.delete("1.0", tk.END)
        self.on_user_input_focus_out(None)
        
        # 在新线程中发送API请求，避免界面冻结
        thread = threading.Thread(
            target=self.call_deepseek_api, 
            args=(user_message, api_key)
        )
        thread.daemon = True
        thread.start()
        
    def call_deepseek_api(self, user_message, api_key):
        """在新线程中调用DeepSeek API"""
        try:
            # 添加用户消息到对话历史
            self.conversation_history.append({"role": "user", "content": user_message})
            
            # 准备API请求
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": self.conversation_history,
                "stream": False
            }
            
            # 发送请求
            response = requests.post(self.api_url, headers=headers, json=data)
            
            # 检查响应
            if response.status_code == 200:
                result = response.json()
                assistant_reply = result["choices"][0]["message"]["content"]
                
                # 添加助手回复到对话历史
                self.conversation_history.append({"role": "assistant", "content": assistant_reply})
                
                # 在主线程中更新UI
                self.root.after(0, lambda: self.display_message("DeepSeek", assistant_reply))
                self.root.after(0, lambda: self.status_var.set("消息发送成功"))
            else:
                error_msg = f"API错误: {response.status_code} - {response.text}"
                self.root.after(0, lambda: self.status_var.set(f"错误: {response.status_code}"))
                self.root.after(0, lambda: messagebox.showerror("API错误", error_msg))
                
        except Exception as e:
            error_msg = f"请求失败: {str(e)}"
            self.root.after(0, lambda: self.status_var.set("请求失败"))
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
        
        finally:
            # 无论成功或失败，都在主线程中重新启用发送按钮
            self.root.after(0, lambda: self.send_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.user_input.focus())
            
    def display_message(self, sender, message):
        """在聊天显示区添加消息"""
        self.chat_display.config(state=tk.NORMAL)
        # 为发送者名称添加标签，以便可以自定义样式
        self.chat_display.tag_configure("sender", font=("Helvetica", 10, "bold"))
        self.chat_display.insert(tk.END, f"{sender}:\n", "sender")
        self.chat_display.insert(tk.END, f"{message}\n\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
    def clear_conversation(self):
        """清空聊天记录和对话历史"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
        # 重新插入提示文本
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert("1.0", "对话记录会输出在这里...", 'placeholder')
        self.chat_display.config(state=tk.DISABLED)

        self.user_input.delete("1.0", tk.END)
        self.user_input.insert("1.0", "你的消息应该输入在这里...", 'placeholder')
        
        self.conversation_history = [
            {"role": "system", "content": "你是一个有用的助手。"}
        ]
        
        self.status_var.set("对话已清空")

def create_deepseek_ui():
    """创建一个并运行DeepSeek聊天应用的Tkinter界面"""
    root = tk.Tk()
    app = DeepSeekChatApp(root)
    root.mainloop()

if __name__ == "__main__":
    create_deepseek_ui()
