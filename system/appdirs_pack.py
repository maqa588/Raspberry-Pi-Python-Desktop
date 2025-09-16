# system/appdirs_pack.py
import sys
import os
import json
from appdirs import user_data_dir

APP_NAME = "RaspberryPiDesktop"
APP_AUTHOR = "Spencer Maqa" 

def get_config_path(filename="desktop_layout.json"):
    """
    获取用户配置文件的完整路径，并确保目录存在。
    
    参数:
        filename (str): 配置文件的名称。
        
    返回:
        str: 配置文件的完整路径。
    """
    data_dir = user_data_dir(APP_NAME, APP_AUTHOR)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return os.path.join(data_dir, filename)

def load_user_config(filename="desktop_layout.json"):
    """
    从用户目录加载配置文件。如果文件不存在或损坏，
    则从打包的默认文件中加载。
    
    参数:
        filename (str): 配置文件的名称。
        
    返回:
        dict: 加载的配置数据。
    """
    config_path = get_config_path(filename)
    
    # 尝试从用户可写目录加载
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            print(f"从用户目录加载配置文件: {config_path}")
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # 如果文件不存在或格式错误，则加载默认配置
        print(f"用户配置文件不存在或已损坏，加载默认配置...")
        # PyInstaller 打包后，文件位于 _MEIPASS 目录
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        default_path = os.path.join(base_path, '..', 'system', filename)
        
        # 再次尝试从默认路径加载
        try:
            with open(default_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"无法加载默认配置文件: {default_path}")
            print(f"错误: {e}")
            return {} # 返回一个空字典以避免程序崩溃

def save_user_config(data, filename="desktop_layout.json"):
    """
    将配置数据保存到用户目录。
    
    参数:
        data (dict): 要保存的配置数据。
        filename (str): 配置文件的名称。
    """
    config_path = get_config_path(filename)
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
            print(f"配置文件已成功保存到: {config_path}")
    except Exception as e:
        print(f"保存配置文件时出错: {e}")
        print(f"错误: {e}")