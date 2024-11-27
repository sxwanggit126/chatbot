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