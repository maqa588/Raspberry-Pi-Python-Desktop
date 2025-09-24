# -*- mode: python ; coding: utf-8 -*-

# 定义版本号，可以在多处使用
version_string = "1.0.0.1"

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

# 对于 Windows/Linux 可执行文件 (EXE)
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

# 对于 macOS 应用 (BUNDLE)
app = BUNDLE(
    coll,
    name='Raspberry Pi Desktop.app',
    icon='setup_logo.icns',
    bundle_identifier=None,
    # 直接在这里指定版本号，非常方便
    info_plist={
        'CFBundleShortVersionString': version_string,
        'CFBundleVersion': version_string,
    }
)