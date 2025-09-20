# software/browser.py （可选替换）
import sys
import subprocess
import os
from tkinter import messagebox
from pathlib import Path

def open_browser(app_instance):
    """
    启动浏览器子进程。
    - 如果程序被 PyInstaller 打包（frozen），则复用主 exe 并传入 browser_only 参数（原有逻辑）。
    - 否则在开发环境直接运行 software/browser_app.py（更直接）。
    """
    try:
        main_executable = sys.executable
        is_frozen = getattr(sys, 'frozen', False)

        if is_frozen:
            # 打包后：假设主 exe 支持 browser_only 参数（app.py 的命令行分支）
            command = [main_executable, "browser_only"]
        else:
            # 开发模式：直接运行 software/browser_app.py（使路径解析更稳健）
            current_dir = Path(__file__).resolve().parent
            browser_script = current_dir / "browser_app.py"
            if not browser_script.exists():
                # 退回到原来通过 app.py 启动的方式（兼容旧项目结构）
                app_path = os.path.join(current_dir.parent, 'app.py')
                command = [main_executable, app_path, "browser_only"]
            else:
                command = [main_executable, str(browser_script)]

        subprocess.Popen(command)
        return True

    except Exception as e:
        messagebox.showerror("启动失败", f"启动浏览器时发生未知错误：{e}")
        return False
