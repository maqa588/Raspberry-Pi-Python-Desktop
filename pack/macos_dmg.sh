#!/bin/bash

# 定义要生成的 .dmg 文件名
DMG_FILE="Raspberry Pi Desktop.dmg"

# 检查 .dmg 文件是否存在，如果存在则删除
if [ -f "$DMG_FILE" ]; then
    echo "检测到旧的 .dmg 文件，正在删除..."
    rm "$DMG_FILE"
fi

# 执行 create-dmg 命令
create-dmg \
  --volname "Raspberry Pi Desktop Installer" \
  --background "macos_background.png" \
  --volicon "setup_logo.icns" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "Raspberry Pi Desktop.app" 170 190 \
  --hide-extension "Raspberry Pi Desktop.app" \
  --app-drop-link 430 190 \
  "$DMG_FILE" \
  "dist/Raspberry Pi Desktop.app"

echo "DMG 文件已成功生成！"