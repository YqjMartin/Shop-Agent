"""
Agent 记忆管理模块

负责管理长对话历史，通过分层策略压缩历史记录：
- 最近 3 轮：完整保留
- 第 4-8 轮：摘要化保留
- 第 9+ 轮：删除

这样可以显著降低 LLM 处理的 Token 数量，同时保留关键上下文。
"""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class InteractionRecord:
    """单条交互记录"""

    def __init__(
        self,
        role: str,
        content: str,
        mode: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        """
        Args:
            role: "user" 或 "assistant"
            content: 消息内容
            mode: 交互模式 ("general", "router", "order_agent", "rag_agent", "tool_calling")
            metadata: 额外元数据（如提取的订单号、商品信息等）
            timestamp: 交互时间戳
        """
        self.role = role
        self.content = content
        self.mode = mode
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "role": self.role,
            "content": self.content,
            "mode": self.mode,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InteractionRecord":
        """从字典恢复"""
        timestamp = (
            datetime.fromisoformat(data["timestamp"])
            if "timestamp" in data
            else datetime.now()
        )
        return cls(
            role=data["role"],
            content=data["content"],
            mode=data.get("mode", "general"),
            metadata=data.get("metadata", {}),
            timestamp=timestamp,
        )

    def get_summary(self, max_length: int = 100) -> str:
        """生成摘要（用于压缩长历史）"""
        if len(self.content) <= max_length:
            return self.content

        # 简单的摘要策略：保留内容的关键部分
        summary = self.content[:max_length] + "..."
        return summary


class AgentMemory:
    """Agent 记忆管理器"""

    # 配置参数
    FULL_RECENT_TURNS = 3  # 保留完整内容的轮数
    SUMMARY_TURNS_START = 4  # 开始做摘要的轮数
    SUMMARY_TURNS_END = 8  # 摘要的最后一轮
    MAX_HISTORY_LENGTH = 20  # 总历史最大轮数
    TARGET_CHAR_LENGTH = 2000  # 目标字符限制

    ORDER_KEYWORDS = [
        "订单",
        "物流",
        "快递",
        "发货",
        "签收",
        "配送",
        "tracking",
        "shipment",
        "delivery",
    ]
    PRODUCT_KEYWORDS = [
        "推荐",
        "商品",
        "产品",
        "购买",
        "性价比",
        "预算",
        "category",
        "price",
    ]
    CATEGORY_KEYWORDS = {
        "电子产品": ["键盘", "鼠标", "耳机", "显示器", "手机", "电脑", "充电器"],
        "家电": ["冰箱", "空调", "洗衣机", "吸尘器"],
        "服饰": ["外套", "鞋", "裤", "T恤", "卫衣"],
    }

    def __init__(self):
        """初始化记忆"""
        self.history: List[InteractionRecord] = []
        self.summary_text: Optional[str] = None  # 历史摘要（用于LLM压缩）
        self.historical_summary: Dict[str, Any] = {
            "order_queries": [],
            "products_viewed": [],
            "user_preferences": {},
        }

    @classmethod
    def detect_mode(cls, message: str, response: Optional[str] = None) -> str:
        """根据消息和响应内容检测对话模式。"""
        text = f"{message} {response or ''}".lower()

        if re.search(r"ORD[0-9A-Za-z-]*", text, flags=re.IGNORECASE):
            return "order_query"
        if re.search(r"(?:SF|YT|ZT|JD|EMS)[0-9A-Za-z-]*", text, flags=re.IGNORECASE):
            return "order_query"
        if any(keyword in text for keyword in cls.ORDER_KEYWORDS):
            return "order_query"
        if any(keyword in text for keyword in cls.PRODUCT_KEYWORDS):
            return "product_recommend"
        return "general"

    @classmethod
    def extract_key_info(cls, mode: str, content: str) -> Dict[str, Any]:
        """按模式提取关键信息。"""
        info: Dict[str, Any] = {}

        if mode == "order_query":
            order_numbers = re.findall(
                r"ORD[0-9A-Za-z-]*", content, flags=re.IGNORECASE
            )
            tracking_numbers = re.findall(
                r"(?:SF|YT|ZT|JD|EMS)[0-9A-Za-z-]*", content, flags=re.IGNORECASE
            )
            status_match = re.search(
                r"已发货|待发货|运输中|派送中|已签收|已取消|shipped|delivered|pending",
                content,
                flags=re.IGNORECASE,
            )
            eta_match = re.search(
                r"明天|后天|\d+天(内|后)?|预计[^，。\n]*到达",
                content,
                flags=re.IGNORECASE,
            )

            if order_numbers:
                info["order_numbers"] = sorted(set(order_numbers))
            if tracking_numbers:
                info["tracking_numbers"] = sorted(set(tracking_numbers))
            if status_match:
                info["status"] = status_match.group(0)
            if eta_match:
                info["eta"] = eta_match.group(0)

        if mode == "product_recommend":
            budget_values = re.findall(r"(\d{2,5})\s*(?:元|块|rmb|RMB|¥)", content)
            if budget_values:
                # 只保留最近提到的预算
                info["budget"] = f"{budget_values[-1]}元"

            categories = []
            for category, keywords in cls.CATEGORY_KEYWORDS.items():
                if any(word in content for word in keywords):
                    categories.append(category)
            if categories:
                info["categories"] = sorted(set(categories))

            product_tokens = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,20}", content)
            stop_words = {
                "推荐",
                "商品",
                "产品",
                "预算",
                "以内",
                "可以",
                "一个",
                "这个",
                "那个",
            }
            product_names = [
                token
                for token in product_tokens
                if token not in stop_words and not token.isdigit() and len(token) >= 2
            ]
            if product_names:
                info["product_names"] = product_names[:5]

        return info

    def _merge_metadata(
        self, extracted: Dict[str, Any], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        merged = dict(metadata)
        for key, value in extracted.items():
            if key not in merged:
                merged[key] = value
        return merged

    @staticmethod
    def _format_relative_time(ts: datetime) -> str:
        delta = datetime.now() - ts
        minutes = int(delta.total_seconds() // 60)
        if minutes < 1:
            return "刚刚"
        if minutes < 60:
            return f"{minutes}分钟前"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}小时前"
        return f"{hours // 24}天前"

    def build_historical_summary(self) -> Dict[str, Any]:
        """基于历史对话构建结构化摘要。"""
        if len(self.history) <= self.FULL_RECENT_TURNS:
            return self.historical_summary

        old_records = self.history[: -self.FULL_RECENT_TURNS]

        order_queries = []
        products_viewed = []
        budgets = []
        category_counter: Dict[str, int] = {}

        for record in old_records:
            mode = record.mode
            if mode == "general":
                mode = self.detect_mode(record.content)

            extracted = self.extract_key_info(mode, record.content)
            merged_info = self._merge_metadata(extracted, record.metadata)

            if mode == "order_query":
                item: Dict[str, Any] = {
                    "last_ask_time": self._format_relative_time(record.timestamp)
                }
                if merged_info.get("order_numbers"):
                    item["order_id"] = merged_info["order_numbers"][0]
                if merged_info.get("tracking_numbers"):
                    item["tracking_id"] = merged_info["tracking_numbers"][0]
                if merged_info.get("status"):
                    item["status"] = merged_info["status"]
                if merged_info.get("eta"):
                    item["eta"] = merged_info["eta"]
                if len(item) > 1:
                    order_queries.append(item)

            if mode == "product_recommend":
                product_item: Dict[str, Any] = {
                    "last_ask_time": self._format_relative_time(record.timestamp)
                }
                names = merged_info.get("product_names") or []
                if names:
                    product_item["name"] = names[0]
                categories = merged_info.get("categories") or []
                if categories:
                    product_item["category"] = categories[0]
                    for category in categories:
                        category_counter[category] = (
                            category_counter.get(category, 0) + 1
                        )
                if merged_info.get("budget"):
                    budgets.append(merged_info["budget"])
                    product_item["price_range"] = merged_info["budget"]
                if len(product_item) > 1:
                    products_viewed.append(product_item)

        dedup_order = []
        seen_order_keys = set()
        for item in order_queries:
            key = (item.get("order_id"), item.get("tracking_id"), item.get("status"))
            if key in seen_order_keys:
                continue
            seen_order_keys.add(key)
            dedup_order.append(item)

        dedup_products = []
        seen_product_keys = set()
        for item in products_viewed:
            key = (item.get("name"), item.get("category"), item.get("price_range"))
            if key in seen_product_keys:
                continue
            seen_product_keys.add(key)
            dedup_products.append(item)

        user_preferences: Dict[str, Any] = {}
        if budgets:
            user_preferences["budget"] = budgets[-1]
        if category_counter:
            top_category = max(category_counter, key=category_counter.get)
            user_preferences["category"] = top_category

        self.historical_summary = {
            "order_queries": dedup_order[:5],
            "products_viewed": dedup_products[:5],
            "user_preferences": user_preferences,
        }
        return self.historical_summary

    def format_historical_summary(self) -> str:
        """将结构化摘要格式化为可注入提示词的文本。"""
        summary = self.build_historical_summary()
        lines: List[str] = []

        if summary["order_queries"]:
            items = []
            for item in summary["order_queries"][:3]:
                parts = []
                if item.get("order_id"):
                    parts.append(item["order_id"])
                if item.get("tracking_id"):
                    parts.append(item["tracking_id"])
                if item.get("status"):
                    parts.append(item["status"])
                if item.get("eta"):
                    parts.append(item["eta"])
                if parts:
                    items.append(
                        "(".join([parts[0], "，".join(parts[1:]) + ")"])
                        if len(parts) > 1
                        else parts[0]
                    )
            if items:
                lines.append(f"- 最近查询的订单：{'；'.join(items)}")

        if summary["products_viewed"]:
            names = [
                item.get("name")
                for item in summary["products_viewed"][:5]
                if item.get("name")
            ]
            if names:
                lines.append(f"- 浏览或咨询的商品：{'、'.join(names)}")

        prefs = summary.get("user_preferences", {})
        pref_parts = []
        if prefs.get("budget"):
            pref_parts.append(f"预算{prefs['budget']}")
        if prefs.get("category"):
            pref_parts.append(f"偏好{prefs['category']}")
        if pref_parts:
            lines.append(f"- 用户偏好：{'，'.join(pref_parts)}")

        return "\n".join(lines)

    def add_interaction(
        self,
        role: str,
        content: str,
        mode: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        添加一条交互记录

        Args:
            role: "user" 或 "assistant"
            content: 消息内容
            mode: 交互模式
            metadata: 元数据
        """
        detected_mode = mode
        if detected_mode == "general":
            detected_mode = self.detect_mode(content)

        extracted_info = self.extract_key_info(detected_mode, content)
        merged_metadata = self._merge_metadata(extracted_info, metadata or {})

        record = InteractionRecord(
            role=role,
            content=content,
            mode=detected_mode,
            metadata=merged_metadata,
        )
        self.history.append(record)
        logger.debug(
            f"Added interaction: {role} ({detected_mode}) - {len(content)} chars"
        )

    def get_recent_turns(self, n: int = 3) -> List[Dict[str, str]]:
        """获取最近N轮（完整保留）"""
        recent = self.history[-n:] if len(self.history) > n else self.history
        return [{"role": r.role, "content": r.content} for r in recent]

    def get_summarized_turns(self) -> List[Dict[str, str]]:
        """获取需要摘要化的轮次"""
        # 最近3轮不摘要
        if len(self.history) <= self.FULL_RECENT_TURNS:
            return []

        # 取第4-8轮进行摘要
        start_idx = self.FULL_RECENT_TURNS
        end_idx = min(
            self.SUMMARY_TURNS_END, len(self.history) - self.FULL_RECENT_TURNS
        )

        if start_idx >= len(self.history):
            return []

        summarized = []
        for record in self.history[start_idx:end_idx]:
            # 标记关键的Tool Calling和RAG结果
            if record.mode in ["tool_calling", "rag_agent"]:
                summary = f"[{record.mode.upper()}] {record.get_summary(150)}"
            else:
                summary = record.get_summary(100)

            summarized.append({"role": record.role, "content": summary})

        return summarized

    def get_compressed_history(
        self, target_length: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        获取压缩后的历史记录

        压缩策略：
        1. 如果有全局摘要，作为首条系统消息
        2. 最近 3 轮完整保留
        3. 之前的 5 轮摘要化
        4. 更早的删除

        Args:
            target_length: 目标字符长度限制（可选）

        Returns:
            可以直接传给 LLM 的消息列表
        """
        target_length = target_length or self.TARGET_CHAR_LENGTH
        messages = []

        # 1. 优先加入结构化历史摘要
        structured_summary = self.format_historical_summary()
        if structured_summary:
            messages.append(
                {
                    "role": "system",
                    "content": f"【用户概览摘要】\n{structured_summary}\n\n【最近对话】",
                }
            )
        elif self.summary_text:
            messages.append(
                {
                    "role": "system",
                    "content": f"【用户历史概览】\n{self.summary_text}\n\n【最近对话】",
                }
            )

        # 2. 计算当前字符总数
        current_chars = sum(len(m.get("content", "")) for m in messages)

        # 3. 尝试加入摘要化的轮次（第4-8轮）
        summarized = self.get_summarized_turns()
        for msg in summarized:
            if current_chars >= target_length * 0.8:  # 留20%的余量
                break
            messages.append(msg)
            current_chars += len(msg["content"])

        # 4. 加入最近的完整轮次
        recent = self.get_recent_turns(self.FULL_RECENT_TURNS)
        messages.extend(recent)

        logger.debug(
            f"Compressed history: {len(messages)} messages, ~{current_chars} chars"
        )
        return messages

    def clear(self) -> None:
        """清空所有历史和摘要"""
        self.history.clear()
        self.summary_text = None
        logger.info("Memory cleared")

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典（便于存储到DB或session）"""
        return {
            "history": [r.to_dict() for r in self.history],
            "summary_text": self.summary_text,
            "historical_summary": self.historical_summary,
            "timestamp": datetime.now().isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMemory":
        """从字典恢复（用于加载保存的状态）"""
        memory = cls()

        if "history" in data:
            for record_data in data["history"]:
                memory.history.append(InteractionRecord.from_dict(record_data))

        if "summary_text" in data:
            memory.summary_text = data["summary_text"]

        if "historical_summary" in data and isinstance(
            data["historical_summary"], dict
        ):
            memory.historical_summary = data["historical_summary"]

        logger.info(f"Memory restored: {len(memory.history)} interactions")
        return memory

    def get_stats(self) -> Dict[str, Any]:
        """获取内存统计信息"""
        total_chars = sum(len(r.content) for r in self.history)
        mode_counts = {}
        for record in self.history:
            mode_counts[record.mode] = mode_counts.get(record.mode, 0) + 1

        return {
            "total_turns": len(self.history),
            "total_chars": total_chars,
            "avg_chars_per_turn": (
                total_chars // len(self.history) if self.history else 0
            ),
            "mode_distribution": mode_counts,
            "has_summary": self.summary_text is not None,
            "historical_summary": self.historical_summary,
        }

    def __len__(self) -> int:
        """返回历史轮数"""
        return len(self.history)

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"<AgentMemory turns={stats['total_turns']} chars={stats['total_chars']}>"
        )
