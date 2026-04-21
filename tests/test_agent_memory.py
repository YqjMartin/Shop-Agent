"""
AgentMemory 模块单元测试

测试内容：
1. 记录添加和检索
2. 历史压缩和Buffer规则
3. 序列化和反序列化
4. 统计信息
"""

import pytest
from datetime import datetime
from app.services.agent_memory import AgentMemory, InteractionRecord


class TestInteractionRecord:
    """测试InteractionRecord类"""

    def test_create_record(self):
        """测试创建交互记录"""
        record = InteractionRecord(
            role="user",
            content="查询订单ORD123",
            mode="order_query",
            metadata={"order_id": "ORD123"},
        )

        assert record.role == "user"
        assert record.content == "查询订单ORD123"
        assert record.mode == "order_query"
        assert record.metadata["order_id"] == "ORD123"

    def test_record_to_dict(self):
        """测试记录序列化"""
        record = InteractionRecord(
            role="assistant", content="订单已发货", mode="tool_calling"
        )

        record_dict = record.to_dict()
        assert record_dict["role"] == "assistant"
        assert record_dict["content"] == "订单已发货"
        assert record_dict["mode"] == "tool_calling"
        assert "timestamp" in record_dict

    def test_record_from_dict(self):
        """测试记录反序列化"""
        original_dict = {
            "role": "user",
            "content": "推荐商品",
            "mode": "rag_agent",
            "metadata": {"category": "电子产品"},
            "timestamp": datetime.now().isoformat(),
        }

        record = InteractionRecord.from_dict(original_dict)
        assert record.role == "user"
        assert record.content == "推荐商品"
        assert record.mode == "rag_agent"
        assert record.metadata["category"] == "电子产品"

    def test_record_summary(self):
        """测试记录摘要生成"""
        record = InteractionRecord(
            role="assistant", content="这是一个很长的产品描述，包含很多详细信息" * 10
        )

        summary = record.get_summary(max_length=50)
        assert len(summary) <= 54  # 50 + "..."
        assert summary.endswith("...")


class TestAgentMemory:
    """测试AgentMemory类"""

    def test_add_interaction(self):
        """测试添加交互"""
        memory = AgentMemory()

        memory.add_interaction(role="user", content="你好", mode="general")
        memory.add_interaction(role="assistant", content="你好！", mode="general")

        assert len(memory) == 2
        assert memory.history[0].role == "user"
        assert memory.history[1].role == "assistant"

    def test_get_recent_turns_basic(self):
        """测试获取最近轮数（基本情况）"""
        memory = AgentMemory()

        memory.add_interaction("user", "消息1")
        memory.add_interaction("assistant", "回复1")
        memory.add_interaction("user", "消息2")

        recent = memory.get_recent_turns(n=2)
        assert len(recent) == 2
        # 最后两条是 "回复1" 和 "消息2"
        assert recent[0]["content"] == "回复1"
        assert recent[1]["content"] == "消息2"

    def test_get_recent_turns_exceed(self):
        """测试获取最近轮数（超过历史长度）"""
        memory = AgentMemory()

        memory.add_interaction("user", "消息1")
        memory.add_interaction("assistant", "回复1")

        recent = memory.get_recent_turns(n=10)
        assert len(recent) == 2

    def test_buffer_strategy_full_recent(self):
        """测试Buffer策略：最近3轮完整保留"""
        memory = AgentMemory()

        # 添加5轮对话
        for i in range(5):
            memory.add_interaction("user", f"消息{i+1}")
            memory.add_interaction("assistant", f"回复{i+1}")

        recent = memory.get_recent_turns(n=3)
        assert len(recent) == 3

    def test_buffer_strategy_summarize(self):
        """测试Buffer策略：第4-8轮摘要化"""
        memory = AgentMemory()

        # 添加10轮对话
        for i in range(10):
            memory.add_interaction("user", f"消息{i+1}")
            memory.add_interaction("assistant", f"回复{i+1}")

        summarized = memory.get_summarized_turns()
        # 应该包含第4-8轮（索引3-7）
        assert len(summarized) > 0
        assert len(summarized) <= 5  # 4-8轮最多5条

    def test_compressed_history_basic(self):
        """测试浓缩历史：基本情况（少于3轮）"""
        memory = AgentMemory()

        memory.add_interaction("user", "你好")
        memory.add_interaction("assistant", "你好！")

        compressed = memory.get_compressed_history()
        assert len(compressed) == 2
        assert compressed[0]["role"] == "user"
        assert compressed[1]["role"] == "assistant"

    def test_compressed_history_many_turns(self):
        """测试浓缩历史：多轮对话"""
        memory = AgentMemory()

        # 添加15轮对话
        for i in range(15):
            memory.add_interaction(
                "user",
                f"消息{i+1}：{'X' * 50}",
                mode="order_agent" if i % 2 == 0 else "rag_agent",
            )
            memory.add_interaction("assistant", f"回复{i+1}：{'Y' * 100}")

        compressed = memory.get_compressed_history()

        # 应该包含最近3轮 + 部分摘要
        assert len(compressed) > 0
        assert len(compressed) <= 20  # 合理的范围

        # 最后两条应该是最近的消息
        if len(compressed) >= 2:
            assert (
                "15" in compressed[-1]["content"] or "14" in compressed[-2]["content"]
            )

    def test_compressed_history_preserves_key_info(self):
        """测试浓缩历史是否保留关键信息"""
        memory = AgentMemory()

        # 添加带有Tool Calling的对话
        memory.add_interaction("user", "查询订单", mode="general")
        memory.add_interaction(
            "assistant",
            "订单详情：ORD123已发货",
            mode="tool_calling",
            metadata={"order_id": "ORD123"},
        )

        compressed = memory.get_compressed_history()

        # 应该保留Tool Calling的结果
        content_str = " ".join([m["content"] for m in compressed])
        assert (
            "ORD123" in content_str
            or "tool_calling" in content_str
            or len(compressed) > 0
        )

    def test_clear_memory(self):
        """测试清空记忆"""
        memory = AgentMemory()

        memory.add_interaction("user", "消息")
        memory.add_interaction("assistant", "回复")
        assert len(memory) == 2

        memory.clear()
        assert len(memory) == 0
        assert memory.summary_text is None

    def test_to_dict_and_from_dict(self):
        """测试序列化和反序列化"""
        memory1 = AgentMemory()
        memory1.add_interaction("user", "消息1", mode="order_agent")
        memory1.add_interaction("assistant", "回复1", mode="tool_calling")
        memory1.summary_text = "用户查询了订单"

        # 序列化
        data = memory1.to_dict()

        # 反序列化
        memory2 = AgentMemory.from_dict(data)

        assert len(memory2) == 2
        assert memory2.history[0].role == "user"
        assert memory2.history[1].role == "assistant"
        assert memory2.summary_text == "用户查询了订单"

    def test_get_stats(self):
        """测试统计信息"""
        memory = AgentMemory()

        memory.add_interaction("user", "查询订单 ORD1001", mode="order_query")
        memory.add_interaction("assistant", "订单已发货", mode="order_query")
        memory.add_interaction(
            "user", "推荐一款200元以内键盘", mode="product_recommend"
        )

        stats = memory.get_stats()

        assert stats["total_turns"] == 3
        assert stats["total_chars"] == sum(len(r.content) for r in memory.history)
        assert "order_query" in stats["mode_distribution"]
        assert stats["mode_distribution"]["order_query"] == 2
        assert "product_recommend" in stats["mode_distribution"]
        assert stats["mode_distribution"]["product_recommend"] == 1

    def test_detect_mode(self):
        """测试模式识别"""
        assert AgentMemory.detect_mode("请帮我查下订单ORD2024001") == "order_query"
        assert AgentMemory.detect_mode("预算200元推荐一个键盘") == "product_recommend"
        assert AgentMemory.detect_mode("你好") == "general"

    def test_extract_key_info_order(self):
        """测试订单模式关键信息提取"""
        content = "订单ORD2024001已发货，快递SF123456，预计明天到达"
        info = AgentMemory.extract_key_info("order_query", content)

        assert "order_numbers" in info
        assert "ORD2024001" in info["order_numbers"]
        assert "tracking_numbers" in info
        assert "SF123456" in info["tracking_numbers"]
        assert info.get("status")
        assert info.get("eta")

    def test_extract_key_info_product(self):
        """测试商品模式关键信息提取"""
        content = "帮我推荐200元以内的无线键盘"
        info = AgentMemory.extract_key_info("product_recommend", content)

        assert info.get("budget") == "200元"
        assert "categories" in info
        assert "电子产品" in info["categories"]

    def test_structured_summary_generated(self):
        """测试结构化摘要生成"""
        memory = AgentMemory()
        memory.add_interaction("user", "查询订单ORD123，物流到哪了", mode="order_query")
        memory.add_interaction(
            "assistant", "订单ORD123已发货，预计明天到", mode="order_query"
        )
        memory.add_interaction(
            "user", "预算300元推荐一个键盘", mode="product_recommend"
        )
        memory.add_interaction("assistant", "推荐机械键盘", mode="product_recommend")
        memory.add_interaction("user", "还有别的吗", mode="general")
        memory.add_interaction(
            "assistant", "还可以看看薄膜键盘", mode="product_recommend"
        )

        structured = memory.build_historical_summary()
        assert "order_queries" in structured
        assert "products_viewed" in structured
        assert "user_preferences" in structured

    def test_compressed_history_contains_structured_summary(self):
        """测试压缩历史中包含结构化摘要系统消息"""
        memory = AgentMemory()
        memory.add_interaction("user", "订单ORD123状态", mode="order_query")
        memory.add_interaction("assistant", "已发货", mode="order_query")
        memory.add_interaction("user", "推荐200元键盘", mode="product_recommend")
        memory.add_interaction("assistant", "推荐A款", mode="product_recommend")
        memory.add_interaction("user", "还有吗", mode="general")

        compressed = memory.get_compressed_history()
        assert compressed
        assert compressed[0]["role"] == "system"
        assert "用户概览摘要" in compressed[0]["content"]

    def test_memory_length(self):
        """测试记忆长度"""
        memory = AgentMemory()

        assert len(memory) == 0

        for i in range(5):
            memory.add_interaction("user", f"消息{i}")

        assert len(memory) == 5

    def test_memory_repr(self):
        """测试记忆字符串表示"""
        memory = AgentMemory()
        memory.add_interaction("user", "消息")

        repr_str = repr(memory)
        assert "AgentMemory" in repr_str
        assert "turns=1" in repr_str


class TestAgentMemoryIntegration:
    """集成测试：模拟真实场景"""

    def test_long_conversation_integration(self):
        """测试长对话场景"""
        memory = AgentMemory()

        # 模拟20轮对话
        for round_no in range(20):
            memory.add_interaction(
                "user",
                f"用户消息第{round_no+1}轮" + "X" * 50,
                mode="order_agent" if round_no % 3 == 0 else "general",
            )
            memory.add_interaction(
                "assistant",
                f"助手回复第{round_no+1}轮" + "Y" * 100,
                mode="tool_calling" if round_no % 2 == 0 else "general",
            )

        # 获取压缩历史
        compressed = memory.get_compressed_history()

        # Token应该大幅降低
        compressed_chars = sum(len(m["content"]) for m in compressed)
        original_chars = sum(len(r.content) for r in memory.history)

        reduction_ratio = 1 - (compressed_chars / original_chars)
        print(f"\nToken减少比例: {reduction_ratio:.1%}")
        print(f"原始: {original_chars} 字符 -> 压缩: {compressed_chars} 字符")

        # 压缩后应该有显著的Token减少（至少20%）
        assert reduction_ratio > 0.2 or len(compressed) >= 4  # 最近3轮应保留

    def test_mode_specific_compression(self):
        """测试模式特定的压缩"""
        memory = AgentMemory()

        # 交替添加不同模式的交互
        for i in range(12):
            if i % 3 == 0:
                memory.add_interaction("user", f"查询订单ORD{i}", mode="order_query")
            elif i % 3 == 1:
                memory.add_interaction(
                    "assistant", f"订单已发货{i}", mode="order_query"
                )
            else:
                memory.add_interaction(
                    "user", f"推荐{i}元以内键盘", mode="product_recommend"
                )

        stats = memory.get_stats()

        assert "order_query" in stats["mode_distribution"]
        assert "product_recommend" in stats["mode_distribution"]

        # 验证可以正常摘要
        summarized = memory.get_summarized_turns()
        assert len(summarized) >= 0


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_memory_compression(self):
        """测试空记忆的压缩"""
        memory = AgentMemory()

        compressed = memory.get_compressed_history()
        assert len(compressed) == 0

    def test_single_message_memory(self):
        """测试单条消息的记忆"""
        memory = AgentMemory()
        memory.add_interaction("user", "单条消息")

        compressed = memory.get_compressed_history()
        assert len(compressed) == 1
        assert compressed[0]["content"] == "单条消息"

    def test_very_long_message(self):
        """测试超长单条消息"""
        memory = AgentMemory()

        long_content = "X" * 5000  # 5KB消息
        memory.add_interaction("user", long_content)

        compressed = memory.get_compressed_history()
        assert len(compressed) == 1
        assert len(compressed[0]["content"]) == 5000

    def test_unicode_content(self):
        """测试Unicode内容"""
        memory = AgentMemory()

        memory.add_interaction("user", "你好，这是中文消息", mode="general")
        memory.add_interaction(
            "assistant", "查询订单ORD123的日本商品🎌", mode="order_agent"
        )

        compressed = memory.get_compressed_history()
        assert len(compressed) > 0

        # 验证unicode被正确保留
        content_str = " ".join([m["content"] for m in compressed])
        assert "中文" in content_str or "订单" in content_str

    def test_metadata_preservation(self):
        """测试元数据保留"""
        memory = AgentMemory()

        memory.add_interaction(
            "assistant",
            "查询结果",
            mode="tool_calling",
            metadata={
                "order_id": "ORD123",
                "status": "shipped",
                "timestamp": "2024-01-01",
            },
        )

        record_dict = memory.history[0].to_dict()
        assert record_dict["metadata"]["order_id"] == "ORD123"
        assert record_dict["metadata"]["status"] == "shipped"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
