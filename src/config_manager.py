# 配置管理模块
# 负责从 JSON 配置文件加载和解析配置信息
# 提供静态方法加载配置，支持错误处理

import json
import streamlit as st

class ConfigManager:
    """
    配置管理类，提供配置文件加载方法

    主要功能：
    1. 从 JSON 文件读取配置
    2. 处理配置文件读取过程中可能出现的异常
    """
    @staticmethod
    def load_config(config_path='config/config.json'):
        """
        从指定路径加载配置文件

        参数:
        - config_path (str): 配置文件路径，默认为 'config/config.json'

        返回:
        - dict: 解析后的配置字典
        - None: 配置加载失败
        """
        try:
            # 使用 utf-8 编码打开文件
            with open(config_path, 'r', encoding='utf-8') as f:
                # 解析 JSON 配置
                return json.load(f)
        except FileNotFoundError:
            # 处理文件未找到的异常
            st.error(f"配置文件 {config_path} 未找到")
            return None
        except json.JSONDecodeError:
            # 处理 JSON 解析错误
            st.error(f"配置文件 {config_path} 解析错误")
            return None
