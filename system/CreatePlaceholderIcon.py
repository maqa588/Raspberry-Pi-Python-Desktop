from PIL import Image, ImageDraw
import os

# --- 辅助函数：如果图标不存在，则创建占位图标 ---
def create_placeholder_icon(path, size=(48, 48), color="blue", text="FILE"):
    """如果指定的图标文件不存在，则创建一个临时的占位图"""
    if not os.path.exists(path):
        try:
            img = Image.new('RGBA', size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            # 绘制一个简单的图标背景
            draw.rectangle((2, 2, size[0]-2, size[1]-12), fill=color)
            # 绘制图标文字
            draw.text((size[0]/2, size[1]/2 - 10), text, fill="white", anchor="mm")
            img.save(path)
            print(f"创建占位图标: {path}")
        except Exception as e:
            print(f"创建占位图标失败: {e}")