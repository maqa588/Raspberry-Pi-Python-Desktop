import os
from pathlib import Path
from PIL import Image, ImageTk

class IconLoader:
    def __init__(self):
        self.project_root = self._get_project_root()

    def _get_project_root(self):
        """
        确定项目的根目录。
        适应不同的运行环境（开发或打包后）。
        """
        # 假设 file_manager_app.py 位于 software/file_manager/
        # 那么项目的根目录就是它的三级父目录
        try:
            current_path = Path(__file__).resolve()
            return current_path.parent.parent.parent
        except NameError:
            # 在某些打包环境中 __file__ 可能未定义
            return Path(os.getcwd())

    def load_icons(self):
        """加载所有需要的图标并存储。"""
        icon_references = {}
        icon_names = {
            "folder": "folder.png", "music": "music.png", "photo": "photo.png",
            "video": "video.png", "file": "file.png", "editor": "editor.png",
            "browser": "browser.png"
        }
        icon_path = self.project_root / "icons"
        if not icon_path.exists():
            print("警告: 无法找到图标目录。将使用一个空白图片作为备用。")
            img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
            placeholder = ImageTk.PhotoImage(img)
            for name in icon_names.keys():
                icon_references[name] = placeholder
            return icon_references

        for name, filename in icon_names.items():
            try:
                img_path = icon_path / filename
                if img_path.exists():
                    img = Image.open(img_path).resize((16, 16), Image.Resampling.LANCZOS)
                    icon_references[name] = ImageTk.PhotoImage(img)
                else:
                    raise FileNotFoundError
            except Exception as e:
                print(f"警告: 加载图标 {filename} 失败: {e}. 将使用一个空白图片。")
                img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
                icon_references[name] = ImageTk.PhotoImage(img)
        return icon_references