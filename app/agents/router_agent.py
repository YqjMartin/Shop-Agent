"""
统一Agent路由器

根据用户意图自动判断并路由到相应的专用Agent：
- 订单查询意图 -> OrderAgent
- 产品推荐意图 -> RAGAgent
"""

import json
import logging
from typing import List, Dict, Any, Optional

from app.agents.base_agent import BaseAgent
from app.agents.order_agent import order_agent
from app.agents.rag_agent import rag_agent

logger = logging.getLogger(__name__)


# 意图分类工具
INTENT_CLASSIFICATION_SYSTEM_PROMPT = """你是一个意图分类器。根据用户消息判断用户想要做什么。

可选意图：
1. order_query - 用户想查询订单、物流、快递相关问题
2. product_recommend - 用户想了解产品、推荐、购物相关问题
3. general - 其他一般性问题，不属于上述两类

注意事项：
- 结合上下文判断用户意图，特别是当用户回复简短信息（如订单号）时
- 如果用户的历史问题涉及订单查询，即使当前消息是"ORD12345"这样的单号，也应分类为order_query
- 返回JSON格式的分类结果

请直接返回JSON，不要有其他内容。格式如下：
{"intent": "order_query|product_recommend|general", "confidence": 0.0-1.0, "reason": "简短的理由"}
"""


class RouterAgent(BaseAgent):
    """统一路由器Agent"""

    SYSTEM_PROMPT = """你是一个电商客服助手，可以帮助用户：
1. 查询订单状态、物流信息
2. 推荐产品、解答产品相关问题

请根据用户的问题，选择最合适的功能来帮助用户。
"""

    async def classify_intent(self, user_message: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """使用LLM进行意图分类

        Args:
            user_message: 当前用户消息
            history: 对话历史，用于结合上下文判断意图
        """
        # 构建消息列表，包含历史记录
        messages = [
            {"role": "system", "content": INTENT_CLASSIFICATION_SYSTEM_PROMPT}
        ]

        # 添加历史记录（只取最近3轮，避免过长）
        if history:
            recent_history = history[-6:] if len(history) > 6 else history
            for msg in recent_history:
                messages.append({"role": msg["role"], "content": msg["content"]})

        # 添加当前用户消息
        messages.append({"role": "user", "content": user_message})

        try:
            # 使用response_format确保返回有效JSON
            response = await self.chat(
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            content = response.get("content", "")

            if not content:
                logger.warning("意图分类返回内容为空")
                return {"intent": "general", "confidence": 0.5, "reason": "返回为空"}

            # 尝试解析JSON
            try:
                result = json.loads(content.strip())
                return {
                    "intent": result.get("intent", "general"),
                    "confidence": result.get("confidence", 0.5),
                    "reason": result.get("reason", "")
                }
            except (json.JSONDecodeError, AttributeError) as e:
                logger.warning(f"解析意图分类结果失败: {e}, content: {content}")
                return {"intent": "general", "confidence": 0.5, "reason": "解析失败"}

        except Exception as e:
            logger.error(f"意图分类失败: {e}")
            return {"intent": "general", "confidence": 0.5, "reason": f"分类出错: {str(e)}"}

    async def process(
        self,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        处理用户请求，自动路由到合适的Agent

        Args:
            user_message: 用户消息
            history: 对话历史
            user_id: 当前登录用户ID（可选，用于个性化订单查询）

        Returns:
            包含回复内容和路由信息的字典
        """
        # 第一步：意图分类（传入历史记录以支持多轮对话）
        intent_result = await self.classify_intent(user_message, history)
        intent = intent_result.get("intent", "general")
        confidence = intent_result.get("confidence", 0.5)

        logger.info(f"意图分类结果: {intent} (置信度: {confidence})")

        # 第二步：根据意图路由
        if intent == "order_query":
            logger.info("路由到 OrderAgent")
            result = await order_agent.process(
                user_message,
                history,
                user_id=user_id
            )
            result["intent"] = "order_query"
            result["confidence"] = confidence
            return result

        elif intent == "product_recommend":
            logger.info("路由到 RAGAgent")
            result = await rag_agent.process(user_message, k=5, history=history)
            result["intent"] = "product_recommend"
            result["confidence"] = confidence
            return result

        else:
            # 一般性问题，直接用基础对话
            logger.info("路由到 基础对话")
            messages = self.build_messages(user_message, self.SYSTEM_PROMPT, history)
            response = await self.chat(messages, temperature=0.7)

            return {
                "content": response.get("content", "抱歉，我无法理解您的问题。请尝试询问关于订单或产品的问题。"),
                "intent": "general",
                "confidence": confidence,
                "tool_used": False
            }


# 全局实例
router_agent = RouterAgent()
