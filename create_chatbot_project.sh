#!/bin/bash

# 设置项目根目录
PROJECT_DIR="chatbot"

# 创建项目目录结构
mkdir -p $PROJECT_DIR/config
mkdir -p $PROJECT_DIR/src

# 创建 config.json
cat << EOF > $PROJECT_DIR/config/config.json
{
    "openai": {
        "api_key": "your_openai_api_key_here"
    },
    "mysql": {
        "host": "localhost",
        "database": "chatbot_db",
        "user": "your_mysql_username",
        "password": "your_mysql_password"
    }
}
EOF

# 创建 __init__.py 确保 src 是一个 Python 包
touch $PROJECT_DIR/src/__init__.py

# 创建 config_manager.py
cat << EOF > $PROJECT_DIR/src/config_manager.py
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
EOF

# 创建 database_manager.py
cat << EOF > $PROJECT_DIR/src/database_manager.py
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
            # 创建必要的数据库表
            self._create_tables()
        except Error as e:
            st.error(f"数据库连接错误: {e}")
            raise

    def _create_tables(self):
        """
        创建聊天会话和消息表
        使用 IF NOT EXISTS 确保表不会重复创建
        """
        # 会话表 SQL 定义
        create_session_table = """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id VARCHAR(36) PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        # 消息表 SQL 定义，外键关联会话表
        create_messages_table = """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            session_id VARCHAR(36),
            role VARCHAR(20),
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
        )
        """
        try:
            self.cursor.execute(create_session_table)
            self.cursor.execute(create_messages_table)
            self.connection.commit()
        except Error as e:
            st.error(f"创建表错误: {e}")

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
EOF

# 创建 chatbot.py
cat << EOF > $PROJECT_DIR/src/chatbot.py
# 聊天机器人核心模块
# 负责与 OpenAI API 交互，生成对话响应
# 提供对话生成的核心逻辑

import streamlit as st
from openai import OpenAI

class Chatbot:
    """
    聊天机器人类，处理与 OpenAI API 的交互

    主要功能：
    1. 初始化 OpenAI 客户端
    2. 生成对话响应
    3. 支持流式响应输出
    """
    def __init__(self, config, db_manager):
        """
        初始化聊天机器人

        参数:
        - config (dict): 配置信息
        - db_manager (DatabaseManager): 数据库管理器
        """
        # 使用配置中的 API Key 初始化 OpenAI 客户端
        self.client = OpenAI(api_key=config["openai"]["api_key"])
        self.db_manager = db_manager

    def generate_response(self, messages):
        """
        生成对话响应，支持流式输出

        参数:
        - messages (list): 对话历史消息列表

        返回:
        - str: 生成的完整响应文本
        """
        response_text = ""
        # 创建一个可以动态更新的 Streamlit 占位符
        message_placeholder = st.empty()

        # 调用 OpenAI API，使用流式输出
        for response in self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            stream=True,
        ):
            # 逐字符获取并显示响应
            if response.choices[0].delta.content is not None:
                response_text += response.choices[0].delta.content
                # 实时更新响应，添加闪烁光标效果
                message_placeholder.markdown(response_text + "▌")

        # 最终显示完整响应
        message_placeholder.markdown(response_text)
        return response_text
EOF

# 创建主应用入口 app.py
cat << EOF > $PROJECT_DIR/app.py
import streamlit as st
from src.config_manager import ConfigManager
from src.database_manager import DatabaseManager
from src.chatbot import Chatbot


def main():
    st.set_page_config(page_title="多会话聊天机器人", page_icon="🤖", layout="wide")

    # 加载配置
    config = ConfigManager.load_config()
    if not config:
        st.error("无法加载配置，请检查config.json文件")
        return

    try:
        # 初始化数据库管理器和聊天机器人
        db_manager = DatabaseManager(config)
        chatbot = Chatbot(config, db_manager)
    except Exception as e:
        st.error(f"初始化失败: {e}")
        return

    # 初始化会话状态管理
    if 'current_session' not in st.session_state:
        # 如果没有当前会话，创建一个新会话
        st.session_state.current_session = db_manager.get_or_create_session()
        st.session_state.sessions = {
            st.session_state.current_session: {
                "name": "会话 1",
                "messages": db_manager.get_session_messages(st.session_state.current_session)
            }
        }

    # 侧边栏会话管理
    with st.sidebar:
        st.title("🤖 会话管理")

        # 创建新会话按钮
        if st.button("➕ 新建会话"):
            new_session_id = db_manager.get_or_create_session()
            st.session_state.sessions[new_session_id] = {
                "name": f"会话 {len(st.session_state.sessions) + 1}",
                "messages": []
            }
            st.session_state.current_session = new_session_id

        # 显示并选择已有会话
        for session_id, session_info in st.session_state.sessions.items():
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(session_info["name"], key=f"session_{session_id}"):
                    st.session_state.current_session = session_id
            with col2:
                # 删除会话按钮
                if st.button("❌", key=f"delete_{session_id}"):
                    if session_id in st.session_state.sessions:
                        del st.session_state.sessions[session_id]
                    break

    # 当前会话处理
    current_session = st.session_state.current_session
    st.title(st.session_state.sessions[current_session]["name"])

    # 显示历史消息
    messages = st.session_state.sessions[current_session]["messages"]
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 处理用户输入
    if prompt := st.chat_input("请输入您的问题"):
        # 保存用户消息
        db_manager.save_message(current_session, "user", prompt)
        st.session_state.sessions[current_session]["messages"].append({"role": "user", "content": prompt})

        # 显示用户消息
        with st.chat_message("user"):
            st.markdown(prompt)

        # 生成AI响应
        with st.chat_message("assistant"):
            # 准备对话历史
            formatted_messages = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.sessions[current_session]["messages"]
            ]
            # 调用聊天机器人生成响应
            response = chatbot.generate_response(formatted_messages)

        # 保存AI响应
        db_manager.save_message(current_session, "assistant", response)
        st.session_state.sessions[current_session]["messages"].append({"role": "assistant", "content": response})

        # 刷新页面
        st.rerun()


if __name__ == "__main__":
    main()
EOF

# 创建依赖文件 requirements.txt
cat << EOF > $PROJECT_DIR/requirements.txt
streamlit
openai
mysql-connector-python
EOF

# 创建 README.md
cat << EOF > $PROJECT_DIR/README.md
# 持久化聊天机器人

## 项目简介
基于 Streamlit、OpenAI 和 MySQL 的聊天机器人应用

## 环境准备
1. 安装依赖: \`pip install -r requirements.txt\`
2. 配置 \`config/config.json\`
3. 创建 MySQL 数据库

## 运行
\`\`\`bash
streamlit run app.py
\`\`\`

## 功能
- 持久化对话记录
- OpenAI 对话生成
- 会话管理
EOF

# 输出成功信息
echo "项目 $PROJECT_DIR 创建成功！"
echo "请配置 config/config.json 后使用 'streamlit run app.py' 启动应用"