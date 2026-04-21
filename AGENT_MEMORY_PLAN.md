# Agent Memory 功能实现计划

## 项目背景

**问题**：当前系统将用户的**完整对话历史**逐字推送到LLM，导致：
- Token消耗随对话轮数线性增长
- 对话超过10轮后，模型处理速度明显下降
- 成本与延迟无法控制
- 后续难以支持用户跨天、跨周的长期对话

**目标**：构建轻量级的**统一记忆层**，压缩长历史同时保留关键信息。

---

## 核心设计原则

| 原则 | 说明 |
|------|------|
| **记忆分层** | 最近N轮完整保留 + 更早的摘要化 + 最老的删除 |
| **时间衰减** | 新交互权重高，旧交互权重低 |
| **模式识别** | 自动检测订单查询、商品推荐等场景，提取关键字段 |
| **最小改动** | 只在后端加层，前端无需改动 |

---

## 分阶段计划

### **阶段 1：基础记忆层（第1周）**

**目标**：完成Buffer策略，支持历史截断

#### 1.1 新建 `app/services/agent_memory.py`

```python
核心类：AgentMemory
- __init__()
- add_interaction(role, content, mode, metadata)
- get_compressed_history(target_length=2000)  # 字符限制
- clear()
- to_dict() / from_dict()

Buffer策略：
- 保留最近 3 轮完整对话
- 第 4-8 轮：只保留 {role, content摘要}
- 第 9+ 轮：删除
- 特殊处理：Tool Calling 结果、RAG 召回结果标记为"关键"
```

#### 1.2 改造 `app/api/endpoints.py` 的聊天接口

修改 `POST /api/chat/auto` 和相关端点：
```python
# 原来的流程
messages = request.messages  # 完整历史

# 改为
memory = AgentMemory.from_dict(cache)  # 从此前的exchange拿出来
messages = memory.get_compressed_history()  # 压缩后的

# 执行Agent...
agent_result = await router_agent.process(...)

# 更新记忆
memory.add_interaction(role="user", content=request.messages[-1]["content"], ...)
memory.add_interaction(role="assistant", content=agent_result["content"], mode="router")
cache = memory.to_dict()  # 返回给前端或存DB
```

#### 1.3 测试& 验证

- 编写 `tests/test_agent_memory.py`
- 测试 Buffer 截断逻辑
- 测试压缩后的历史是否满足意图分类

**Deliverable**：
- [x] `agent_memory.py` 完成
- [x] 聊天接口集成记忆层
- [x] 测试通过，5轮+ 对话不出错

---

### **阶段 2：场景感知记忆（第2周）**

**目标**：根据对话模式，自动提取关键信息到摘要

#### 2.1 增强 `AgentMemory` — 加入模式识别

```python
类方法：
- detect_mode(message, response)  # 检测是 order_query / product_recommend / general
- extract_key_info(mode, response)  # 从response提取关键字段
  
示例：
订单查询 → 提取 {order_number, status, tracking_number, eta}
商品推荐 → 提取 {product_names, category, budget_range, reason}
```

#### 2.2 改进摘要生成

不再简单删除，而是**结构化保存**：

```python
historical_summary = {
    "order_queries": [
        {"order_id": "ORD123", "status": "已发货", "last_ask_time": "5分钟前"},
        {"tracking_id": "SF456", "eta": "明天到达"}
    ],
    "products_viewed": [
        {"name": "无线键盘", "category": "电子产品", "price_range": "100-200"}
    ],
    "user_preferences": {"budget": "200以内", "category": "电子产品"}
}
```

#### 2.3 改造压缩历史生成逻辑

当历史过长时，不是删除，而是转化为：

```
【最近3轮完整对话】
+ 
【用户概览摘要】
- 最近查询的订单：ORD123(已发货), SF456(明天到)
- 浏览的商品类别：无线键盘、充电器
- 用户偏好：200元以内的电子产品
```

**Deliverable**：
- [x] Pattern detection 模块完成
- [x] 摘要生成算法验证
- [x] 集成到 AgentMemory
- [x] 手工测试：20轮对话不丢失关键信息

---

### **阶段 3：LLM 辅助压缩（第3周）**

**目标**：用LLM智能压缩历史，而不是规则截断

#### 3.1 新建 `app/services/summary_service.py`

```python
async def summarize_history(old_turns: List[Dict]) -> str:
    """
    用LLM把第1-N轮对话压成一句话
    
    Prompt:
    用户最近的交互记录如下（已按时间排序）：
    {old_turns}
    
    请生成一个不超过50字的摘要，保留：
    1. 用户查过哪些订单
    2. 询问过哪些商品
    3. 有什么特殊需求或偏好
    
    示例回答：
    用户查询了订单ORD123(已发货)和ORD124(未发货)，浏览了音频设备，预算200元。
    """
    ...
```

#### 3.2 改进 Agent Memory

```python
async def compress_old_history(self):
    """当历史超过阈值时触发LLM压缩"""
    if len(self.history) > HISTORY_LIMIT:
        old = self.history[:COMPRESS_AFTER_N]
        summary = await summary_service.summarize_history(old)
        
        # 删除原始记录，保留摘要
        self.history = self.history[COMPRESS_AFTER_N:]
        self.summary = summary
```

#### 3.3 在最终发给Agent的消息中加入摘要

```python
def get_compressed_history(self):
    messages = []
    
    # 加入摘要（如果存在）
    if self.summary:
        messages.append({
            "role": "system",
            "content": f"【用户历史概览】\n{self.summary}\n\n【最近对话】"
        })
    
    # 加入最近N轮
    messages.extend(self.recent_turns)
    return messages
```

**Deliverable**：
- [ ] `summary_service.py` 完成
- [ ] LLM 压缩端到端测试
- [ ] 对比：规则压缩 vs LLM压缩的效果
- [ ] 性能基准：压缩耗时 < 1s

---

### **阶段 4：持久化与状态管理（第4周）**

**目标**：支持用户跨会话（跨天）访问历史

#### 4.1 扩展数据库模型

```python
# app/database/models.py 中添加

class ChatSession(Base):
    """对话会话"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.now)
    last_activity = Column(DateTime, default=datetime.now)
    memory_state = Column(JSON)  # AgentMemory.to_dict()
    status = Column(String, default="active")  # active/archived

class ChatMessage(Base):
    """单条消息（用于审计和重放）"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id"))
    role = Column(String)
    content = Column(Text)
    mode = Column(String)  # router/order_agent/rag_agent
    created_at = Column(DateTime, default=datetime.now)
```

#### 4.2 改造聊天接口

```python
@router.post("/api/chat/auto")
async def chat_auto(request: ChatRequest, user_id: int = Depends(get_current_user_id)):
    # 尝试载入已有的 session
    session = db.query(ChatSession).filter(
        ChatSession.user_id == user_id,
        ChatSession.status == "active"
    ).first()
    
    if session:
        memory = AgentMemory.from_dict(session.memory_state)
    else:
        session = ChatSession(user_id=user_id, session_id=generate_uuid())
        memory = AgentMemory()
    
    # 执行对话...
    
    # 保存消息和状态
    db.add(ChatMessage(...))
    session.memory_state = memory.to_dict()
    session.last_activity = datetime.now()
    db.commit()
```

#### 4.3 新增接口

```python
# 查看历史会话
@router.get("/api/chat/sessions")

# 恢复某个会话
@router.post("/api/chat/sessions/{session_id}/restore")

# 导出会话
@router.get("/api/chat/sessions/{session_id}/export")
```

**Deliverable**：
- [ ] ChatSession 和 ChatMessage 表创建
- [ ] 数据库迁移脚本
- [ ] 聊天接口支持会话恢复
- [ ] 新增会话管理接口

---

## 实现顺序流程图

```
┌─────────────────────────────────────────────────────────┐
│  阶段1：Buffer策略（基础）                               │
│  - agent_memory.py 核心实现                             │
│  - 聊天接口改造                                        │
│  - 测试验证                                            │
└────────────────┬────────────────────────────────────────┘
                 │ (3-5天)
                 ↓
┌─────────────────────────────────────────────────────────┐
│  阶段2：场景感知（精准度优化）                           │
│  - Pattern detection                                    │
│  - 结构化摘要生成                                       │
│  - 手工测试长对话                                       │
└────────────────┬────────────────────────────────────────┘
                 │ (3-5天)
                 ↓
┌─────────────────────────────────────────────────────────┐
│  阶段3：LLM压缩（质量提升）                              │
│  - summary_service.py                                  │
│  - 异步压缩流程                                        │
│  - 性能测试                                            │
└────────────────┬────────────────────────────────────────┘
                 │ (2-3天)
                 ↓
┌─────────────────────────────────────────────────────────┐
│  阶段4：持久化（生产就绪）                               │
│  - 数据库模型                                          │
│  - 会话管理接口                                        │
│  - 集成测试                                            │
└─────────────────────────────────────────────────────────┘
                 │ (3-5天)
                 ↓
           ✅ 完成！
```

---

## 预期收益

| 指标 | 改进前 | 改进后 | 提升 |
|------|-------|-------|------|
| **10轮对话的Token数** | ~2000 | ~600 | ↓ 70% |
| **30轮对话的Token数** | ~6000 | ~1200 | ↓ 80% |
| **平均响应时间** | 2.5s | 1.5s | ↓ 40% |
| **API成本/100对话** | $0.50 | $0.12 | ↓ 76% |
| **支持连续对话轮数** | ~20 | 无限制 | ✅ |

---

## 风险与缓解

| 风险 | 影响 | 缓解方案 |
|------|------|---------|
| 摘要丢失关键信息 | 模型判断错误 | 保留完整的最近N轮，摘要只覆盖更早期 |
| LLM压缩成本高 | 抵消Token省省 | 异步压缩 + 缓存 + 采样压缩（不是每次） |
| 前端兼容性 | 集成困难 | 后端完全透明，前端无感知改动 |
| 数据库迁移 | 用户数据丢失 | 准备好迁移脚本，阶段4再上线 |

---

## 检查清单

### 阶段1 完成标准
- [x] `agent_memory.py` 代码质量达到生产级
- [x] `POST /api/chat/auto` 成功集成
- [x] 自动化测试覆盖 Buffer 逻辑 (90%+ 覆盖率)
- [x] 手工测试：5轮、10轮、20轮对话都正常
- [x] 文档完整（README 中说明新功能）

### 阶段2 完成标准
- [x] Pattern detection 准确率 > 95%
- [x] 摘要长度稳定在 50-100 字内
- [x] 长对话测试（50轮）无信息丢失
- [x] 性能基准稳定（添加到CI/CD）

### 阶段3 完成标准
- [ ] 压缩耗时 < 1.0s (P99)
- [ ] LLM 摘要 vs 规则摘要 对比测试
- [ ] Token消耗基准再下降10-15%

### 阶段4 完成标准
- [ ] 迁移脚本测试通过
- [ ] 用户数据无丢失
- [ ] 会话恢复功能端到端测试
- [ ] 上线灰度（10% 用户）→ 全量

---

## 文件变更清单

```
新增文件：
  app/services/agent_memory.py           (300-400行)
  app/services/summary_service.py        (150-200行)
  tests/test_agent_memory.py             (200-300行)
  AGENT_MEMORY_PLAN.md                   (本文件)

修改文件：
  app/api/endpoints.py                   (+30-50行)
  app/database/models.py                 (+60-80行)
  app/agents/base_agent.py               (可能微调)
  
可选：
  migrations/versions/[timestamp]_add_chat_session.py
  app/core/config.py                     (新增参数)
```

---

## 下一步

1. **确认计划** — 确认各阶段的范围和优先级
2. **预估投入** — 明确产出物的质量标准
3. **启动阶段1** — 开始实现 agent_memory.py

---

**更新时间**：2026-04-21  
**状态**：✅ 阶段2已完成
