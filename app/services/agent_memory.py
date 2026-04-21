"""
Agent 记忆管理模块

负责管理长对话历史，通过分层策略压缩历史记录：
- 最近 3 轮：完整保留
- 第 4-8 轮：摘要化保留
- 第 9+ 轮：删除

这样可以显著降低 LLM 处理的 Token 数量，同时保留关键上下文。
"""

import json
import logging
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

    def __init__(self):
        """初始化记忆"""
        self.history: List[InteractionRecord] = []
        self.summary_text: Optional[str] = None  # 历史摘要（用于LLM压缩）

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
        record = InteractionRecord(
            role=role, content=content, mode=mode, metadata=metadata
        )
        self.history.append(record)
        logger.debug(f"Added interaction: {role} ({mode}) - {len(content)} chars")

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

        # 1. 如果有全局摘要，加入系统提示
        if self.summary_text:
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
        }

    def __len__(self) -> int:
        """返回历史轮数"""
        return len(self.history)

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"<AgentMemory turns={stats['total_turns']} chars={stats['total_chars']}>"
        )
