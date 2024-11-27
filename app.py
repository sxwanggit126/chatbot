# app.py
import streamlit as st
from src.config_manager import ConfigManager
from src.database_manager import DatabaseManager
from src.chatbot import Chatbot
import logging
from typing import Dict, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_session_state():
    """初始化会话状态"""
    if 'sessions' not in st.session_state:
        st.session_state.sessions = {}
    if 'current_session' not in st.session_state:
        st.session_state.current_session = None
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = None
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = None


def create_new_session(db_manager: DatabaseManager) -> str:
    """创建新会话"""
    session_id = db_manager.get_or_create_session()
    st.session_state.sessions[session_id] = {
        "name": f"会话 {len(st.session_state.sessions) + 1}",
        "messages": []
    }
    return session_id


def delete_session(session_id: str, db_manager: DatabaseManager):
    """删除会话"""
    if session_id in st.session_state.sessions:
        del st.session_state.sessions[session_id]
        if session_id == st.session_state.current_session:
            if st.session_state.sessions:
                st.session_state.current_session = next(iter(st.session_state.sessions))
            else:
                st.session_state.current_session = create_new_session(db_manager)


def display_chat_messages(messages: list):
    """显示聊天消息"""
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def main():
    # 设置页面配置
    st.set_page_config(
        page_title="智能客服系统",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 初始化会话状态
    initialize_session_state()

    try:
        # 加载配置
        config = ConfigManager.load_config()
        if not config:
            st.error("无法加载配置，请检查config.json文件")
            return

        # 初始化数据库管理器和聊天机器人
        if st.session_state.db_manager is None:
            st.session_state.db_manager = DatabaseManager(config)
        if st.session_state.chatbot is None:
            st.session_state.chatbot = Chatbot(config, st.session_state.db_manager)

    except Exception as e:
        st.error(f"初始化失败: {str(e)}")
        logger.error(f"初始化失败: {str(e)}", exc_info=True)
        return

    # 如果没有当前会话，创建一个新会话
    if not st.session_state.current_session:
        st.session_state.current_session = create_new_session(st.session_state.db_manager)

    # 侧边栏会话管理
    with st.sidebar:
        st.title("🤖 会话管理")

        # 创建新会话按钮
        if st.button("➕ 新建会话", key="new_session"):
            st.session_state.current_session = create_new_session(st.session_state.db_manager)
            st.rerun()

        # 会话列表
        st.subheader("当前会话列表")
        for session_id, session_info in st.session_state.sessions.items():
            col1, col2 = st.columns([4, 1])

            with col1:
                if st.button(
                        session_info["name"],
                        key=f"session_{session_id}",
                        use_container_width=True,
                        type="secondary" if session_id != st.session_state.current_session else "primary"
                ):
                    st.session_state.current_session = session_id
                    st.rerun()

            with col2:
                if st.button("❌", key=f"delete_{session_id}", help="删除会话"):
                    delete_session(session_id, st.session_state.db_manager)
                    st.rerun()

    # 主聊天界面
    current_session = st.session_state.current_session
    current_session_info = st.session_state.sessions[current_session]

    # 显示当前会话标题
    st.title(current_session_info["name"])

    try:
        # 加载并显示历史消息
        current_session_info["messages"] = st.session_state.db_manager.get_session_messages(current_session)
        display_chat_messages(current_session_info["messages"])

        # 聊天输入处理
        if prompt := st.chat_input("请输入您的问题"):
            try:
                # 检查数据库连接状态
                if not st.session_state.db_manager:
                    st.session_state.db_manager = DatabaseManager(config)

                # 生成响应
                with st.spinner('正在处理您的请求...'):
                    response = st.session_state.chatbot.handle_conversation(
                        prompt,
                        current_session
                    )

                    # 显示新消息
                    with st.chat_message("user"):
                        st.markdown(prompt)

                    with st.chat_message("assistant"):
                        st.markdown(response)

                    # 更新会话消息
                    current_session_info["messages"] = st.session_state.db_manager.get_session_messages(current_session)

            except Exception as chat_error:
                st.error(f"处理消息失败: {str(chat_error)}")
                logger.error(f"处理消息失败: {str(chat_error)}", exc_info=True)

                # 尝试重新初始化连接
                try:
                    st.session_state.db_manager = DatabaseManager(config)
                    st.session_state.chatbot = Chatbot(config, st.session_state.db_manager)
                except Exception as reinit_error:
                    logger.error(f"重新初始化失败: {str(reinit_error)}", exc_info=True)

    except Exception as e:
        st.error(f"加载会话失败: {str(e)}")
        logger.error(f"加载会话失败: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()