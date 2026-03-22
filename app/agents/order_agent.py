import json
import logging
from typing import List, Dict, Any, Optional

from app.agents.base_agent import BaseAgent
from app.services.order_service import (
    get_order_status,
    search_orders_by_product,
    get_user_orders
)
from app.database import SessionLocal
from app.database.models import User

logger = logging.getLogger(__name__)


# ============ 工具定义 ============

def get_order_by_number(order_number: str) -> str:
    """
    根据订单号查询订单状态和物流信息。

    Args:
        order_number: 订单号，例如 "ORD20240319001"

    Returns:
        订单详细信息，包括订单状态、物流状态、快递单号、商品列表等
    """
    db = SessionLocal()
    try:
        result = get_order_status(db, order_number=order_number)
        if result:
            return json.dumps(result, ensure_ascii=False, indent=2)
        else:
            return f"未找到订单号为 {order_number} 的订单"
    finally:
        db.close()


def get_order_by_tracking(tracking_number: str) -> str:
    """
    根据快递单号查询订单的物流状态。

    Args:
        tracking_number: 快递单号，例如 "SF1234567890"

    Returns:
        订单的物流信息，包括订单状态、发货时间、预计送达时间等
    """
    db = SessionLocal()
    try:
        result = get_order_status(db, tracking_number=tracking_number)
        if result:
            return json.dumps(result, ensure_ascii=False, indent=2)
        else:
            return f"未找到快递单号为 {tracking_number} 的订单"
    finally:
        db.close()


def search_product_orders(product_name: str) -> str:
    """
    根据商品名称搜索包含该商品的订单。

    Args:
        product_name: 商品名称或关键词，例如 "键盘"、"iPhone"等

    Returns:
        包含该商品的所有订单列表
    """
    db = SessionLocal()
    try:
        results = search_orders_by_product(db, product_name)
        if results:
            return json.dumps(results, ensure_ascii=False, indent=2)
        else:
            return f"未找到包含商品 '{product_name}' 的订单"
    finally:
        db.close()


def get_user_order_history(username: str) -> str:
    """
    查询用户的所有订单历史。

    Args:
        username: 用户名

    Returns:
        该用户的所有订单列表
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return f"未找到用户名为 {username} 的用户"

        orders = get_user_orders(db, user.id)
        if not orders:
            return f"用户 {username} 暂无订单记录"

        order_list = []
        for order in orders:
            order_list.append({
                "order_number": order.order_number,
                "status": order.status,
                "total_amount": order.total_amount,
                "created_at": order.created_at.isoformat() if order.created_at else None
            })

        return json.dumps(order_list, ensure_ascii=False, indent=2)
    finally:
        db.close()


# 工具列表定义
ORDER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_order_by_number",
            "description": "根据订单号查询订单状态和物流信息。当用户询问具体订单号的状态时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_number": {
                        "type": "string",
                        "description": "订单号，例如 ORD20240319001"
                    }
                },
                "required": ["order_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_by_tracking",
            "description": "根据快递单号查询订单的物流状态。当用户提供快递单号时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "tracking_number": {
                        "type": "string",
                        "description": "快递单号，例如 SF1234567890"
                    }
                },
                "required": ["tracking_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_product_orders",
            "description": "根据商品名称搜索包含该商品的订单。当用户询问买了某个商品的所有订单时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "商品名称或关键词"
                    }
                },
                "required": ["product_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_order_history",
            "description": "查询用户的所有订单历史。当用户询问自己的订单列表时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "用户名"
                    }
                },
                "required": ["username"]
            }
        }
    }
]


# 工具函数映射
TOOL_FUNCTIONS = {
    "get_order_by_number": get_order_by_number,
    "get_order_by_tracking": get_order_by_tracking,
    "search_product_orders": search_product_orders,
    "get_user_order_history": get_user_order_history
}


# ============ Order Agent ============

class OrderAgent(BaseAgent):
    """订单查询Agent，支持Tool Calling"""

    SYSTEM_PROMPT = """你是一个电商客服助手，专门帮助用户查询订单和物流信息。

当用户询问订单相关问题时，你需要：
1. 如果用户提供了订单号，使用 get_order_by_number 查询
2. 如果用户提供了快递单号，使用 get_order_by_tracking 查询
3. 如果用户想查询某个商品的所有订单，使用 search_product_orders 查询
4. 如果用户想查看自己的订单历史，使用 get_user_order_history 查询

请用友好的语气回答用户的问题。
【严格警告】: 绝对不允许编造任何订单号、物流状态或快递公司！必须且只能使用工具查询后，根据工具返回的真实结果回答用户。"""

    def __init__(self):
        super().__init__()
        self.tools = ORDER_TOOLS

    async def process(
        self,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[int] = None,
        username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理用户请求，自动判断是否需要调用工具

        Args:
            user_message: 用户消息
            history: 对话历史
            user_id: 当前登录用户ID（可选，用于个性化查询）
            username: 当前登录用户名（可选）

        Returns:
            包含回复内容和是否调用了工具的信息
        """
        # 如果提供了 user_id但没有 username，从数据库查询用户名
        if user_id and not username:
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    username = user.username
            finally:
                db.close()

        # 如果提供了用户信息，在系统提示词中添加用户上下文
        system_prompt = self.SYSTEM_PROMPT
        if user_id and username:
            system_prompt = f"{system_prompt}\n\n【当前用户信息】\n用户名: {username}\n用户ID: {user_id}\n\n当用户询问自己的订单时，直接使用 get_user_order_history 工具查询。"

        messages = self.build_messages(user_message, system_prompt, history)

        # 第一轮：调用模型，让模型决定是否需要使用工具
        response = await self.chat_with_functions(
            messages=messages,
            functions=self.tools,
            temperature=0.7
        )

        # 检查是否有函数调用
        if "function_call" in response:
            function_call = response["function_call"]
            function_name = function_call["name"]
            arguments = json.loads(function_call["arguments"])

            logger.info(f"调用工具: {function_name}, 参数: {arguments}")

            # 执行工具函数
            tool_result = self._execute_tool(function_name, arguments)

            # 将工具结果添加到消息中
            messages.append({
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": function_name,
                            "arguments": function_call["arguments"]
                        }
                    }
                ]
            })
            messages.append({
                "role": "tool",
                "tool_call_id": "call_1",
                "name": function_name,
                "content": tool_result
            })

            # 第二轮：让模型根据工具结果生成最终回复
            final_response = await self.chat_with_functions(
                messages=messages,
                functions=self.tools,
                temperature=0.7
            )

            return {
                "content": final_response.get("content", "处理完成"),
                "tool_used": True,
                "tool_name": function_name,
                "tool_result": tool_result
            }
        else:
            # 无需调用工具，直接返回回复
            return {
                "content": response.get("content", ""),
                "tool_used": False
            }

    def _execute_tool(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """执行工具函数"""
        func = TOOL_FUNCTIONS.get(function_name)
        if func:
            try:
                return func(**arguments)
            except Exception as e:
                logger.error(f"执行工具 {function_name} 失败: {e}")
                return f"执行查询时出错: {str(e)}"
        else:
            return f"未找到工具: {function_name}"


# 全局实例
order_agent = OrderAgent()
