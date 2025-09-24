# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['../app.py'],
    pathex=[],
    binaries=[],
    datas=[('../icons', 'icons'), ('../software', 'software'), ('../system', 'system')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Raspberry Pi Desktop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # 添加这行来指定 .exe 文件的图标
    icon='setup_logo.ico', 
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Raspberry Pi Desktop',
)
app = BUNDLE(
    coll,
    name='Raspberry Pi Desktop.app',
    # 添加这行来指定 .app 文件的图标
    icon='setup_logo.iconset',
    bundle_identifier=None,
)