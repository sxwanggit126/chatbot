# 数据库管理模块
# 负责处理数据库连接、表创建、消息存储和检索
# 使用 MySQL 作为持久化存储

import streamlit as st
import mysql.connector
from mysql.connector import Error
import uuid

class DatabaseManager:
    """
    数据库管理类，处理聊天会话和消息的数据库操作

    主要功能：
    1. 建立数据库连接
    2. 创建必要的数据库表
    3. 管理会话和消息存储
    """
    def __init__(self, config):
        """
        初始化数据库连接

        参数:
        - config (dict): 数据库配置信息
        """
        try:
            # 使用配置信息建立数据库连接
            self.connection = mysql.connector.connect(
                host=config['mysql']['host'],
                database=config['mysql']['database'],
                user=config['mysql']['user'],
                password=config['mysql']['password']
            )
            # 创建游标对象，支持字典形式返回结果
            self.cursor = self.connection.cursor(dictionary=True)
        except Error as e:
            st.error(f"数据库连接错误: {e}")
            raise

    def get_or_create_session(self, session_id=None):
        """
        获取或创建新的会话ID

        参数:
        - session_id (str, 可选): 现有会话ID

        返回:
        - str: 会话ID
        """
        if not session_id:
            # 生成新的唯一会话ID
            session_id = str(uuid.uuid4())
            # 将新会话插入数据库
            insert_query = "INSERT INTO chat_sessions (session_id) VALUES (%s)"
            self.cursor.execute(insert_query, (session_id,))
            self.connection.commit()
        return session_id

    def save_message(self, session_id, role, content):
        """
        保存聊天消息到数据库

        参数:
        - session_id (str): 会话ID
        - role (str): 消息角色（user/assistant）
        - content (str): 消息内容
        """
        try:
            insert_query = """
            INSERT INTO chat_messages (session_id, role, content)
            VALUES (%s, %s, %s)
            """
            self.cursor.execute(insert_query, (session_id, role, content))
            self.connection.commit()
        except Error as e:
            st.error(f"保存消息错误: {e}")

    def get_session_messages(self, session_id):
        """
        获取特定会话的所有消息

        参数:
        - session_id (str): 会话ID

        返回:
        - list: 消息列表，每个消息是一个字典
        """
        try:
            query = """
            SELECT role, content
            FROM chat_messages
            WHERE session_id = %s
            ORDER BY timestamp
            """
            self.cursor.execute(query, (session_id,))
            return [{"role": msg['role'], "content": msg['content']} for msg in self.cursor.fetchall()]
        except Error as e:
            st.error(f"获取消息错误: {e}")
            return []
