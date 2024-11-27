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
        self.client = OpenAI()
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
            model="gpt-4o-mini",
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
