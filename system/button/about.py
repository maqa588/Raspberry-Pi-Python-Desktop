import tkinter as tk
import platform
import psutil
import os
from PIL import Image, ImageTk

# 导入你的项目常量（如果需要）
from system.config import WINDOW_WIDTH, WINDOW_HEIGHT

def show_system_about(root):
    """
    显示系统信息窗口。
    :param root: Tkinter 主窗口实例。
    """
    # 定义子窗口尺寸
    win_width, win_height = 350, 200
    # 计算居中位置
    x_pos = (WINDOW_WIDTH - win_width) // 2
    y_pos = (WINDOW_HEIGHT - win_height) // 2
    
    # 创建一个顶级（悬浮）窗口
    about_window = tk.Toplevel(root)
    about_window.title("系统信息")
    about_window.geometry(f"{win_width}x{win_height}+{x_pos}+{y_pos}")
    about_window.resizable(False, False)

    # 创建一个标签列表，用于实时更新
    info_labels = []
    for _ in range(4):
        label = tk.Label(about_window, text="", font=("Helvetica", 12), justify="left")
        label.pack(anchor="w", padx=10, pady=5)
        info_labels.append(label)

    # 添加一个用于关闭窗口的按钮
    close_button = tk.Button(about_window, text="关闭", command=about_window.destroy)
    close_button.pack(pady=10)

    # 定义一个更新信息的函数
    def update_info():
        # 获取系统架构和发行版信息
        arch = platform.machine()
        distro_name = platform.platform(terse=True)
        
        # 获取内存和CPU信息
        mem = psutil.virtual_memory()
        cpu_usage = psutil.cpu_percent(interval=None) # interval=None表示非阻塞获取

        # 更新标签文本
        info_labels[0].config(text=f"系统架构: {arch}")
        info_labels[1].config(text=f"发行版: {distro_name}")
        info_labels[2].config(text=f"内存占用: {mem.percent}% ({mem.used / (1024**3):.2f} GB)")
        info_labels[3].config(text=f"CPU 占用: {cpu_usage}%")
        
        # 每秒钟调用一次自身以实现实时更新
        about_window.after(1000, update_info)

    # 首次调用函数以显示信息
    update_info()

def show_developer_about(root):
    """
    显示关于开发者窗口，并加载图片。
    :param root: Tkinter 主窗口实例。
    """
    # 定义子窗口尺寸
    win_width, win_height = 450, 250
    # 计算居中位置
    x_pos = (WINDOW_WIDTH - win_width) // 2
    y_pos = (WINDOW_HEIGHT - win_height) // 2

    # 创建一个顶级（悬浮）窗口
    about_window = tk.Toplevel(root)
    about_window.title("关于开发者")
    about_window.geometry(f"{win_width}x{win_height}+{x_pos}+{y_pos}")
    about_window.resizable(False, False)

    main_frame = tk.Frame(about_window)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # --- 左侧：开发者头像 ---
    left_frame = tk.Frame(main_frame, width=150, height=150)
    left_frame.pack(side="left", fill="y", padx=(0, 10))
    left_frame.pack_propagate(False)

    avatar_label = tk.Label(left_frame)
    avatar_label.pack(expand=True)

    # 尝试加载开发者头像
    try:
        # 优化路径计算，确保从 system/button/about.py 正确回到项目根目录
        # current_file_path: /path/to/Raspberry-Pi-Python-Desktop/system/button/about.py
        current_file_path = os.path.abspath(__file__)
        
        # current_dir: /path/to/Raspberry-Pi-Python-Desktop/system/button
        current_dir = os.path.dirname(current_file_path)
        
        # system_dir: /path/to/Raspberry-Pi-Python-Desktop/system
        system_dir = os.path.dirname(current_dir)
        
        # project_root_dir: /path/to/Raspberry-Pi-Python-Desktop
        project_root_dir = os.path.dirname(system_dir)
        
        # 拼接图片的最终路径
        avatar_full_path = os.path.join(project_root_dir, "icons", "developer_avatar.png")
        
        # 打印规范化后的路径用于调试
        print(f"正在尝试加载开发者头像，规范化后的完整路径为: {avatar_full_path}")

        # 使用 with 语句确保图片正确处理
        with Image.open(avatar_full_path) as original_image:
            original_image.thumbnail((140, 140), Image.LANCZOS)
            
            # 将图片对象存储在 about_window 上，以防止被垃圾回收
            about_window.developer_photo = ImageTk.PhotoImage(original_image)
            
            # 配置 Label 以显示图片
            avatar_label.config(image=about_window.developer_photo)
            
        print("开发者头像加载成功！")

    except FileNotFoundError:
        avatar_label.config(text="无头像", font=("Helvetica", 12))
        print(f"警告: 找不到开发者头像文件: {avatar_full_path}") # 打印完整的失败路径
    except Exception as e:
        avatar_label.config(text="加载头像失败", font=("Helvetica", 10))
        print(f"加载开发者头像时发生错误: {e}")

    # --- 右侧：详细信息 ---
    right_frame = tk.Frame(main_frame)
    right_frame.pack(side="right", fill="both", expand=True)

    developer_info_list = [
        "开发者: Spencer Maqa",
        "项目名称: Raspberry Pi Python Desktop",
        "版本: 0.1.4-alpha",
        "联系方式: maqa588@163.com",
        "项目仓库: https://github.com/maqa588/",
        "Raspberry-Pi-Python-Desktop/",
        "辽宁大学Python程序设计课程 课程设计"
    ]

    for info_text in developer_info_list:
        label = tk.Label(right_frame, text=info_text, font=("Helvetica", 10), justify="left", anchor="w")
        label.pack(fill="x", pady=2)

    # --- 底部：关闭按钮 ---
    close_button = tk.Button(about_window, text="关闭", command=about_window.destroy, font=("Helvetica", 10))
    close_button.pack(pady=10)