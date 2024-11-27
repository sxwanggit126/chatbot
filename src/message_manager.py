# src/message_manager.py
import json
from typing import List, Dict, Tuple
from datetime import datetime
import logging
from typing import Dict, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
class DateTimeEncoder(json.JSONEncoder):
    """处理datetime的JSON编码器"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        return super().default(obj)


class MessageManager:
    def __init__(self, config: Dict):
        self.system_prompts = config['system_prompts']
        self.max_context_messages = config['app']['max_context_messages']

    def _format_query_results(self, query_results: List[Dict]) -> str:
        """
        格式化查询结果
        Args:
            query_results: 数据库查询结果列表
        Returns:
            格式化后的字符串
        """
        if not query_results:
            return "未找到相关记录"

        total_amount = sum(float(record['amount']) for record in query_results)
        total_received = sum(float(record['total_received'] or 0) for record in query_results)
        total_remaining = sum(float(record['remaining_amount'] or 0) for record in query_results)

        result_lines = [
            f"找到 {len(query_results)} 条记录:",
            f"总金额: {total_amount:,.2f} 元",
            f"已收金额: {total_received:,.2f} 元",
            f"未收金额: {total_remaining:,.2f} 元\n"
        ]

        for record in query_results:
            # entry_date 现在已经是字符串格式，直接使用
            result_lines.append(
                f"- {record['entry_date']}: "
                f"{record['customer']} "
                f"金额: {float(record['amount']):,.2f} 元, "
                f"已收: {float(record['total_received'] or 0):,.2f} 元, "
                f"未收: {float(record['remaining_amount'] or 0):,.2f} 元"
            )

        return "\n".join(result_lines)

    def construct_query_messages(self,
                                 query_results: List[Dict],
                                 user_input: str,
                                 history_messages: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        构造查询消息
        Args:
            query_results: 查询结果
            user_input: 用户输入
            history_messages: 历史消息
        Returns:
            (消息列表, 上下文信息)
        """
        context = self._format_query_results(query_results)
        relevant_history = self._select_relevant_messages(history_messages)

        messages = [
            {
                "role": "system",
                "content": self.system_prompts['sales_assistant']
            },
            *relevant_history,
            {
                "role": "user",
                "content": f"上下文信息:\n{context}\n\n用户问题: {user_input}"
            }
        ]

        context_info = {
            "query_results": query_results,
            "relevant_history": relevant_history,
            "system_prompt": self.system_prompts['sales_assistant']
        }

        return messages, context_info

    def _select_relevant_messages(self, history_messages: List[Dict]) -> List[Dict]:
        """选择相关的历史消息"""
        return history_messages[-self.max_context_messages:]