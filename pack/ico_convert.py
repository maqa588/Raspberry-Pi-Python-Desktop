from PIL import Image

# 打开 PNG 文件
img = Image.open('setup_logo.png')

# 保存为 ICO (支持多尺寸)
img.save('setup_logo.ico', sizes=[(16, 16), (24, 24), (32, 32), (64, 64), (256, 256)])

# 保存为 ICNS (macOS)
# Pillow 库直接保存为 .icns 格式可能会有问题，通常建议使用特定工具或 macOS 自身的命令