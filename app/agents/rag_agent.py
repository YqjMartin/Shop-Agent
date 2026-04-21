"""RAG 产品推荐 Agent"""

import logging
from typing import List, Dict, Any, Optional

from app.agents.base_agent import BaseAgent
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)


class RAGAgent(BaseAgent):
    """RAG 产品推荐 Agent"""

    SYSTEM_PROMPT = """你是一个电商产品推荐助手，专门根据用户的需求推荐合适的产品。

当用户询问产品相关问题时，你需要：
1. 理解用户的需求（如：想要什么类型的产品、预算、用途等）
2. 从产品库中搜索相关产品
3. 根据搜索结果，向用户推荐合适的产品

推荐时请：
- 简明扼要地介绍产品特点
- 说明价格
- 如果有多个选项，可以比较推荐

注意：
- 只推荐产品库中存在的商品
- 如有价格信息，必须如实告知用户
- 不要编造产品信息"""

    def __init__(self):
        super().__init__()
        self.vector_store = vector_store

    async def process(
        self,
        user_message: str,
        k: int = 5,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        处理用户的产品推荐请求

        Args:
            user_message: 用户消息（产品咨询）
            k: 返回的产品数量
            history: 对话历史

        Returns:
            包含回复内容和检索结果
        """
        # 确保向量数据库 collection 已初始化
        if self.vector_store.collection is None:
            self.vector_store.get_or_create_collection("products")

        # 1. 向量检索相关产品
        try:
            products = await self.vector_store.search_similar_products(
                query=user_message, k=k
            )
        except Exception as e:
            logger.error(f"产品检索失败: {e}")
            return {
                "content": "抱歉，查询产品时出现错误，请稍后重试。",
                "products": [],
                "error": str(e),
            }

        if not products:
            return {"content": "抱歉，没有找到符合您需求的产品。", "products": []}

        # 2. 构建提示词，包含检索到的产品信息
        product_context = self._build_product_context(products)
        user_prompt = f"""用户问题：{user_message}

请根据以下产品信息回答用户问题：

{product_context}

请给出产品推荐建议："""

        # 3. 调用大模型生成推荐
        messages = self.build_messages(user_prompt, self.SYSTEM_PROMPT, history)

        try:
            response = await self.chat(messages=messages, temperature=0.7)
            content = response.get("content", "推荐处理完成")
        except Exception as e:
            logger.error(f"生成推荐失败: {e}")
            content = f"为您找到以下产品：\n\n{product_context}"

        return {
            "content": content,
            "products": products,
            "tool_used": True,
            "tool_name": ["product_search"],
        }

    def _build_product_context(self, products: List[Dict[str, Any]]) -> str:
        """构建产品上下文文本"""
        lines = []
        for i, p in enumerate(products, 1):
            lines.append(
                f"{i}. **{p['product_name']}**\n"
                f"   - 类别：{p['category']}\n"
                f"   - 价格：¥{p['price']}\n"
                f"   - 描述：{p['description']}\n"
                f"   - 库存：{p['stock']}件"
            )
        return "\n\n".join(lines)


# 全局实例
rag_agent = RAGAgent()
