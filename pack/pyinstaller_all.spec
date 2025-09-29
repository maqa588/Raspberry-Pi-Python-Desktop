# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller Specification File for Raspberry Pi Desktop Application
# ------------------------------------------------------------------
# 目标: 将 ../app.py 打包成一个独立的、包含 OpenCV 和 Ultralytics/NCNN 依赖的可执行文件。

# 定义版本号
version_string = "1.0.0.2"

# 导入必要的模块
import os
import sys
import importlib.util
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, copy_metadata

# ------------------------------------------------------------------
# 1. 依赖收集和预处理
# ------------------------------------------------------------------

# 收集 Ultralytics (YOLO) 和 cv2 的子模块
ultralytics_hidden_imports = collect_submodules('ultralytics')
opencv_hidden_imports = collect_submodules('cv2') 

# 核心修正区域：添加所有通过字符串或子进程动态调用的模块
runtime_imports = [
    'numpy.core.multiarray',  
    'simplejpeg',  
    'matplotlib.backends.backend_agg',

    'pygame', 
    'software.games.pong.main_menu',
    'software.games.pong.settings',
    'software.games.pong.ui_elements',
    'software.games.pong.single_player_mode',
    'software.games.pong.online_mode',
    
    'software.camera_pi.camera_mac',  
    'software.camera_pi.camera_win',
    'software.camera_pi.camera_rpi',
    'software.rss_app',
    'software.rss_app.RSSReaderApp',
    'software.deepseek_app.DeepSeekChatApp',
]

# 收集 cv2 和 ultralytics 运行时所需的数据/二进制文件
cv2_datas = collect_data_files('cv2', include_py_files=True)
ultralytics_datas = collect_data_files('ultralytics', include_py_files=True)
numpy_metadata = copy_metadata('numpy')

# ------------------------------------------------------------------
# 2. 针对 Darwin (macOS) 系统的 OpenCV 动态库修复 (解决 FileExistsError)
# ------------------------------------------------------------------
extra_binaries = []

if sys.platform == 'darwin':
    print("INFO: Detected Darwin (macOS). Applying manual OpenCV binary fix...")
    try:
        cv2_spec = importlib.util.find_spec("cv2")
        if cv2_spec and cv2_spec.submodule_search_locations:
            cv2_path = cv2_spec.submodule_search_locations[0]
            
            # 查找动态库目录 (.dylibs 或 .libs)
            opencv_libs_path = os.path.join(cv2_path, '.dylibs')
            if not os.path.isdir(opencv_libs_path):
                opencv_libs_path = os.path.join(cv2_path, '.libs')

            if os.path.isdir(opencv_libs_path):
                added_files = set()
                
                for item in os.listdir(opencv_libs_path):
                    # 只收集动态链接库文件
                    if item.endswith(('.dylib', '.so', '.pyd')):
                        if item in added_files:
                            continue
                            
                        source = os.path.join(opencv_libs_path, item)
                        # ❗ 关键修复: 将手动添加的 .dylib 文件放入一个子目录 (cv2_dylibs)
                        # 格式: (源文件路径, 目标文件夹/目标文件名)
                        target_path = os.path.join('cv2_dylibs', item) 
                        extra_binaries.append((source, target_path)) 
                        added_files.add(item)
                        
                print(f"INFO: Successfully added {len(extra_binaries)} unique OpenCV binary dependencies to 'cv2_dylibs'.")
            else:
                print("WARNING: Could not find typical OpenCV dynamic libraries folder (.libs or .dylibs). Relying on standard hook.")
        else:
            print("WARNING: Could not determine cv2 package location.")
    except Exception as e:
        print(f"ERROR during manual OpenCV path search: {e}")

# ------------------------------------------------------------------
# 3. Analysis (分析阶段)
# ------------------------------------------------------------------

a = Analysis(
    ['../app.py'], # 应用程序的主入口文件
    pathex=[],
    binaries=extra_binaries, # ⬅️ 添加手动收集的 Darwin/OpenCV 动态库
    
    # 静态数据文件和资源路径 (使用相对路径)
    datas=[
        ('../icons', 'icons'), 
        ('../software', 'software'), 
        ('../system', 'system'),
        # 必须明确包含 NCNN 模型文件
        ('../software/camera_pi/models/yolo11n_ncnn_model', 'software/camera_pi/models/yolo11n_ncnn_model'),
    ] + cv2_datas + ultralytics_datas + numpy_metadata,
    
    # 隐藏导入列表
    hiddenimports=ultralytics_hidden_imports + opencv_hidden_imports + runtime_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# ------------------------------------------------------------------
# 4. EXE (生成可执行文件)
# ------------------------------------------------------------------

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
    console=False, # GUI 应用
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='setup_logo.icns', # macOS/Linux 图标
)

# ------------------------------------------------------------------
# 5. COLLECT & BUNDLE (打包和 macOS 应用结构)
# ------------------------------------------------------------------

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
    icon='setup_logo.icns', 
    bundle_identifier=None,
    info_plist={
        'CFBundleShortVersionString': version_string,
        'CFBundleVersion': version_string,
    }
)
