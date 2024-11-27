# src/database_manager.py
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
import logging
from typing import List, Dict, Optional
from datetime import datetime
import json
import uuid


class DatabaseManager:
    def __init__(self, config: Dict):
        """初始化数据库配置"""
        self.db_config = {
            'host': config['mysql']['host'],
            'user': config['mysql']['user'],
            'password': config['mysql']['password'],
            'database': config['mysql']['database'],
            'charset': 'utf8mb4',
            'cursorclass': DictCursor
        }

    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = pymysql.connect(**self.db_config)
        try:
            yield conn
        finally:
            conn.close()

    def get_sales_records(self, customer_name: Optional[str] = None) -> List[Dict]:
        """获取销售记录"""
        if not customer_name:
            return []

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    # 先尝试精确匹配
                    sql = """
                    SELECT 
                        id,
                        customer,
                        entry_date,
                        amount,
                        IFNULL(total_received, 0) as total_received,
                        IFNULL(remaining_amount, 0) as remaining_amount
                    FROM sales_records 
                    WHERE customer = %s
                    ORDER BY entry_date DESC
                    """

                    cursor.execute(sql, (customer_name,))
                    results = cursor.fetchall()

                    # 如果没有找到，尝试模糊匹配
                    if not results:
                        fuzzy_sql = """
                        SELECT 
                            id,
                            customer,
                            entry_date,
                            amount,
                            IFNULL(total_received, 0) as total_received,
                            IFNULL(remaining_amount, 0) as remaining_amount
                        FROM sales_records 
                        WHERE customer LIKE %s
                        ORDER BY entry_date DESC
                        """
                        cursor.execute(fuzzy_sql, (f'%{customer_name}%',))
                        results = cursor.fetchall()

                    # 转换日期格式为字符串
                    for row in results:
                        if isinstance(row['entry_date'], datetime):
                            row['entry_date'] = row['entry_date'].strftime('%Y-%m-%d %H:%M:%S')

                    return results

                except Exception as e:
                    logging.error(f"查询销售记录失败: {str(e)}", exc_info=True)
                    return []

    def save_message(self, session_id: str, role: str, content: str,
                     parent_message_id: Optional[int] = None) -> int:
        """保存消息"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    sql = """
                    INSERT INTO chat_messages 
                    (session_id, role, content, parent_message_id) 
                    VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(sql, (session_id, role, content, parent_message_id))
                    conn.commit()
                    return cursor.lastrowid
                except Exception as e:
                    logging.error(f"保存消息失败: {str(e)}", exc_info=True)
                    conn.rollback()
                    raise

    def get_session_messages(self, session_id: str) -> List[Dict]:
        """获取会话消息"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                SELECT role, content
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY timestamp
                """
                cursor.execute(sql, (session_id,))
                return cursor.fetchall()

    def get_or_create_session(self, session_id: Optional[str] = None) -> str:
        """获取或创建会话"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                if not session_id:
                    session_id = str(uuid.uuid4())
                    cursor.execute(
                        "INSERT INTO chat_sessions (session_id) VALUES (%s)",
                        (session_id,)
                    )
                    conn.commit()
                return session_id

    def save_structured_query(self,
                              session_id: str,
                              message_id: int,
                              query_type: str,
                              query_params: Dict,
                              context_info: Dict) -> int:
        """保存结构化查询"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    sql = """
                    INSERT INTO structured_queries 
                    (session_id, message_id, query_type, query_params, context_messages)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql, (
                        session_id,
                        message_id,
                        query_type,
                        json.dumps(query_params, ensure_ascii=False),
                        json.dumps(context_info, ensure_ascii=False)
                    ))
                    conn.commit()
                    return cursor.lastrowid
                except Exception as e:
                    logging.error(f"保存结构化查询失败: {str(e)}", exc_info=True)
                    conn.rollback()
                    raise

    def log_query_execution(self,
                            structured_query_id: int,
                            raw_query: str,
                            execution_time: float,
                            result_count: int) -> None:
        """
        记录查询执行情况
        Args:
            structured_query_id: 结构化查询ID
            raw_query: 原始查询语句
            execution_time: 执行时间
            result_count: 结果数量
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    sql = """
                    INSERT INTO query_logs 
                    (structured_query_id, raw_query, execution_time, result_count)
                    VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(sql, (
                        structured_query_id,
                        raw_query,
                        execution_time,
                        result_count
                    ))
                    conn.commit()
                except Exception as e:
                    logging.error(f"保存查询日志失败: {str(e)}", exc_info=True)
                    conn.rollback()