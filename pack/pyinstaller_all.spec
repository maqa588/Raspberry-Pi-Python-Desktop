# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import wx
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
binaries = []

# --- 平台判断 ---
if sys.platform.startswith("win"):
    # Windows: 找到 wxPython 里的 WebView2Loader.dll
    wx_pkg_dir = os.path.dirname(wx.__file__)
    dll_src = os.path.join(wx_pkg_dir, 'WebView2Loader.dll')
    if os.path.exists(dll_src):
        binaries.append((dll_src, '.'))
    else:
        print("⚠️ 警告: 未找到 WebView2Loader.dll, 打包后可能只能用 IE backend")
else:
    # macOS / Linux 使用系统 WebKit，不需要 DLL
    print("ℹ️ 非 Windows 平台，使用系统 WebKit，不打包额外 DLL")

a = Analysis(
    ['../app.py'],  # ✅ 不修改原来的入口路径
    pathex=['..'],  # ✅ 不修改原来的搜索路径
    binaries=binaries,
    datas=[
        ('../icons', 'icons'),
        ('../software', 'software'),
        ('../system', 'system'),
    ],
    hiddenimports=['wx.html2'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RaspberryPiDesktop',  # ✅ 保持原有项目名称
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RaspberryPiDesktop',  # ✅ 保持打包目录名不变
)
