# src/chatbot.py
import logging
from typing import List, Dict, Optional
from datetime import datetime
import json
import time
from openai import OpenAI
import streamlit as st
from .message_manager import MessageManager

class Chatbot:
    """聊天机器人核心类，处理对话流程和LLM交互"""

    def __init__(self, config: Dict, db_manager):
        """
        初始化聊天机器人
        Args:
            config: 配置信息
            db_manager: 数据库管理器实例
        """
        self.client = OpenAI()
        self.db_manager = db_manager
        self.message_manager = MessageManager(config)
        self.config = config
        self.max_retries = config['openai']['max_retries']
        self.retry_delay = config['openai']['retry_delay']

    def parse_user_input(self, user_input: str, history_messages: List[Dict]) -> Optional[Dict]:
        """解析用户输入"""
        recent_history = self.message_manager._select_relevant_messages(history_messages)
        history_context = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in recent_history
        ])

        system_prompt = f"""
        {self.config['system_prompts']['query_parser']}

        历史对话上下文:
        {history_context}

        示例：
        用户: 客户北京极客邦有限公司的款项到账了多少？
        系统: {{"模块": 1, "客户名称": "北京极客邦有限公司", "查询字段": "amount"}}

        用户:已收了多少？
        系统: {{"模块": 1, "客户名称": "北京极客邦有限公司", "查询字段": "total_received"}}
        
        用户: 还剩多少未收款？
        系统: {{"模块": 1, "客户名称": "北京极客邦有限公司", "查询字段": "remaining_amount"}}
        
        示例2：
        用户：你好
        系统：
        {{'模块':6,'其他数据',None}}
        
        示例3：
        用户：最近一年你过得如何？
        系统：
        {{'模块':6,'其他数据',None}}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.config['openai']['model'],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                response_format={"type": "json_object"},
                temperature=self.config['openai']['temperature']
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logging.error(f"解析用户输入失败: {str(e)}")
            return None

    def retrieve_sales_data(self, query_params: Dict) -> List[Dict]:
        """检索销售数据"""
        try:
            if query_params.get('模块') == 1:
                customer_name = query_params.get('客户名称')
                return self.db_manager.get_sales_records(customer_name)
            return []
        except Exception as e:
            logging.error(f"检索销售数据失败: {str(e)}")
            return []

    def format_response(self,
                       data: List[Dict],
                       query_params: Dict,
                       query_field: str) -> str:
        """
        格式化响应内容
        Args:
            data: 查询结果数据
            query_params: 查询参数
            query_field: 查询字段
        """
        if not data:
            return "未找到相关记录"

        field_names = {
            'amount': '总金额',
            'total_received': '已收金额',
            'remaining_amount': '未收金额'
        }

        # 计算合计
        total = sum(float(record[query_field] or 0) for record in data)
        customer_name = query_params.get('客户名称', '未知客户')

        result_lines = [
            f"{customer_name}的{field_names.get(query_field, '金额')}情况：",
            f"找到 {len(data)} 条记录，{field_names.get(query_field, '金额')}合计: {total:,.2f} 元\n"
        ]

        # 添加明细 - 注意 entry_date 已经是字符串格式
        for record in data:
            result_lines.append(
                f"- {record['entry_date']}: "
                f"{float(record[query_field] or 0):,.2f} 元"
            )

        return "\n".join(result_lines)

    def generate_rag_response(self,
                            user_input: str,
                            retrieved_data: List[Dict],
                            query_params: Dict,
                            history_messages: List[Dict]) -> str:
        """生成RAG响应"""
        try:
            # 根据查询字段格式化数据
            query_field = query_params.get('查询字段', 'amount')
            formatted_response = self.format_response(
                retrieved_data,
                query_params,
                query_field
            )

            # 构造完整消息
            messages, context_info = self.message_manager.construct_query_messages(
                retrieved_data,
                user_input,
                history_messages
            )

            # 调用LLM生成补充说明
            for attempt in range(self.max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=self.config['openai']['model'],
                        messages=messages,
                        temperature=self.config['openai']['temperature']
                    )
                    break
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise
                    time.sleep(self.retry_delay)

            # 组合响应
            llm_response = response.choices[0].message.content
            return f"{formatted_response}\n\n{llm_response}"

        except Exception as e:
            logging.error(f"生成RAG响应失败: {str(e)}", exc_info=True)
            return "抱歉，处理您的请求时出现错误。请重试或换个方式提问。"

    def generate_response(self, messages: List[Dict]) -> str:
        """生成普通对话响应"""
        try:
            message_placeholder = st.empty()
            response_text = ""

            for response in self.client.chat.completions.create(
                model=self.config['openai']['model'],
                messages=messages,
                stream=True,
                temperature=self.config['openai']['temperature']
            ):
                if response.choices[0].delta.content is not None:
                    response_text += response.choices[0].delta.content
                    message_placeholder.markdown(response_text + "▌")

            message_placeholder.markdown(response_text)
            return response_text

        except Exception as e:
            logging.error(f"生成响应失败: {str(e)}")
            return "抱歉，处理您的请求时出现错误。请重试。"

    def handle_conversation(self, user_input: str, session_id: str) -> str:
        """处理完整的对话流程"""
        # 1. 获取历史消息
        history_messages = self.db_manager.get_session_messages(session_id)

        # 2. 解析用户输入
        query_params = self.parse_user_input(user_input, history_messages)

        # 3. 保存用户消息
        user_message_id = self.db_manager.save_message(
            session_id=session_id,
            role="user",
            content=user_input
        )

        # 4. 如果有查询参数，保存并执行查询
        response = None
        if query_params:
            start_time = datetime.now()

            # 保存结构化查询
            query_id = self.db_manager.save_structured_query(
                session_id=session_id,
                message_id=user_message_id,
                query_type=str(query_params.get('模块', 'unknown')),
                query_params=query_params,
                context_info={"history_length": len(history_messages)}
            )

            # 执行查询
            retrieved_data = self.retrieve_sales_data(query_params)

            # 记录查询执行情况
            self.db_manager.log_query_execution(
                structured_query_id=query_id,
                raw_query=str(query_params),
                execution_time=(datetime.now() - start_time).total_seconds(),
                result_count=len(retrieved_data) if retrieved_data else 0
            )

            if retrieved_data:
                response = self.generate_rag_response(
                    user_input,
                    retrieved_data,
                    query_params,
                    history_messages
                )

        # 5. 如果没有检索到数据，使用普通对话模式
        if not response:
            response = self.generate_response(
                history_messages + [{"role": "user", "content": user_input}]
            )

        # 6. 保存助手响应
        self.db_manager.save_message(
            session_id=session_id,
            role="assistant",
            content=response,
            parent_message_id=user_message_id
        )

        return response