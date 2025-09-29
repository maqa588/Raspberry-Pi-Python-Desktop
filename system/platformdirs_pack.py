import sys
import os
import json
from platformdirs import PlatformDirs
from pathlib import Path

# 使用 platformdirs 的推荐方式来定义应用名称和作者
APP_NAME = "RaspberryPiDesktop"
APP_AUTHOR = "Spencer Maqa"
# 应用程序的当前版本号
APP_VERSION = "1.0.0.2"

# 创建 PlatformDirs 实例，它会自动处理不同操作系统下的路径
dirs = PlatformDirs(APP_NAME, APP_AUTHOR)

def get_config_path(filename="desktop_layout.json"):
    """
    获取用户配置文件的完整路径，并确保目录存在。
    
    参数:
        filename (str): 配置文件的名称。
        
    返回:
        Path: 配置文件的完整路径 (使用 Path 对象)。
    """
    # 使用 platformdirs 的 user_data_dir 属性来获取用户数据目录
    data_dir = dirs.user_data_dir
    # 确保目录存在
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    return Path(data_dir) / filename

def load_user_config(filename="desktop_layout.json"):
    """
    从用户目录加载配置文件。如果文件不存在、损坏或版本号不匹配，
    则返回一个空字典，表明需要使用默认配置。
    
    参数:
        filename (str): 配置文件的名称。
        
    返回:
        dict: 加载的配置数据。如果加载失败或版本不匹配，返回包含当前版本号的新配置字典。
    """
    config_path = get_config_path(filename)
    
    # 尝试从用户可写目录加载
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            user_config = json.load(f)
            
            # 检查版本号
            file_version = user_config.get("version")
            if file_version == APP_VERSION:
                print(f"从用户目录加载配置文件: {config_path} (版本匹配: {APP_VERSION})")
                return user_config
            else:
                print(f"配置文件版本不匹配。文件版本: {file_version}, 代码版本: {APP_VERSION}。将忽略旧配置。")
                
                # 提示：通常在版本不匹配时，我们会忽略旧配置，并返回一个包含新版本信息的结构，
                # 让主程序知道如何重新初始化。
                
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"用户配置文件不存在或已损坏: {e}。将加载默认配置...")

    # 如果加载失败或版本不匹配，尝试加载默认配置
    
    # PyInstaller 打包后，文件位于 _MEIPASS 目录
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        # 在开发模式下，从当前文件向上两级查找 system 文件夹 (假设结构是 software/app.py -> system/platformdirs_pack.py)
        base_path = Path(os.path.dirname(os.path.abspath(__file__)))
        # 假设 default_path 在 platformdirs_pack.py 所在的同级目录
        default_path = base_path / filename
        
        # 如果找不到，尝试退一级目录查找 (适用于更常见的项目结构)
        if not default_path.exists():
             default_path = base_path.parent / 'system' / filename
    
    # 再次尝试从默认路径加载
    try:
        with open(default_path, 'r', encoding='utf-8') as f:
            print(f"加载默认配置文件: {default_path}")
            default_config = json.load(f)
            
            # 确保默认配置包含正确的版本信息，以便下次保存时写入新版本号
            if default_config.get("version") != APP_VERSION:
                default_config["version"] = APP_VERSION
                
            return default_config
            
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"无法加载默认配置文件: {default_path}")
        print(f"错误: {e}")
        # 如果默认配置也加载失败，返回一个带版本号的空字典
        return {"version": APP_VERSION} 


def save_user_config(data, filename="desktop_layout.json"):
    """
    将配置数据保存到用户目录。在保存前自动添加当前 APP_VERSION。
    
    参数:
        data (dict): 要保存的配置数据。
        filename (str): 配置文件的名称。
    """
    config_path = get_config_path(filename)
    
    # 确保保存的数据包含当前版本号
    if isinstance(data, dict):
        data["version"] = APP_VERSION
        
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
            print(f"配置文件已成功保存到: {config_path}")
    except Exception as e:
        print(f"保存配置文件时出错: {e}")
