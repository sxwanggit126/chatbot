# src/config_manager.py
from typing import Dict, Optional
import json
import logging
from pathlib import Path


class ConfigManager:
    """配置管理类，负责加载和验证配置"""

    @staticmethod
    def load_config(config_path: str = 'config/config.json') -> Optional[Dict]:
        """
        从指定路径加载配置文件
        Args:
            config_path: 配置文件路径
        Returns:
            加载的配置字典，失败则返回None
        """
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"配置文件不存在: {config_path}")

            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            ConfigManager._validate_config(config)
            return config

        except Exception as e:
            logging.error(f"加载配置失败: {str(e)}")
            return None

    @staticmethod
    def _validate_config(config: Dict) -> None:
        """
        验证配置完整性
        Args:
            config: 配置字典
        Raises:
            ValueError: 配置不完整或无效
        """
        required_sections = ['mysql', 'openai', 'system_prompts', 'app']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"配置缺少必要部分: {section}")

        # 验证数据库配置
        required_mysql = ['host', 'database', 'user', 'password']
        for field in required_mysql:
            if field not in config['mysql']:
                raise ValueError(f"数据库配置缺少字段: {field}")