# Shop Agent 项目待完善清单

基于对项目全部源码的审查，按优先级和阶段划分如下：

---

## 第一阶段：安全与关键缺陷修复（紧急）

### 1. 密码哈希方式不安全（暂缓）
- **文件**: `app/core/security.py`
- **问题**: 使用 `hashlib.sha256` 做密码哈希，SHA256 是快速哈希，极易被暴力破解和彩虹表攻击。
- **修复**: 改用 `bcrypt` 或 `argon2-cffi`，并加装 salt。`requirements.txt` 需新增对应依赖。
- **状态**: ⏸️ 用户要求暂不修复
- **风险**: 中

### 2. JWT 无签名验证（暂缓）
- **文件**: `app/core/security.py`
- **问题**: `create_access_token` 和 `decode_access_token` 仅做 base64 编解码，**没有签名和验证**。任何人都能伪造 token、篡改 payload。
- **修复**: 使用 `PyJWT` 或 `python-jose` 库实现标准 JWT 签发与验证，用 `jwt_secret_key` 做 HMAC 签名。
- **状态**: ⏸️ 用户要求暂不修复
- **风险**: 高 - 认证机制完全失效

### 3. JWT 密钥有硬编码默认值
- **文件**: `app/core/config.py`
- **问题**: `jwt_secret_key` 默认值为 `"your-secret-key-change-in-production"`，部署时极易遗漏。
- **修复**: 去掉默认值，设为必填项；启动时检测是否为占位值并拒绝启动。
- **状态**: ✅ 已完成
- **改动**：
  - `config.py`: `jwt_secret_key: str`（移除默认值）
  - `main.py`: 新增 `validate_required_settings()`，启动前校验配置

### 4. SiliconFlow API Key 未设为必填
- **文件**: `app/core/config.py`
- **问题**: `siliconflow_api_key` 为 `Optional[str] = None`，但 `embedding_service.py` 初始化时直接用它创建 client，为 None 时会在运行时崩溃。
- **修复**: 将其设为必填字段，或在 embedding_service 中做显式检查并给出清晰错误提示。
- **状态**: ✅ 已完成
- **改动**：`config.py`: `siliconflow_api_key: str`（移除 Optional）

### 5. .env.example 缺少关键配置
- **文件**: `.env.example`
- **问题**: 缺少 `JWT_SECRET_KEY`、`SILICONFLOW_API_KEY`、`APP_NAME` 等必填项。
- **修复**: 补全所有 .env 支持的配置项及说明。
- **状态**: ✅ 已完成
- **改动**：新增 `APP_NAME`、`JWT_SECRET_KEY`、`SILICONFLOW_API_KEY` 配置项及注释

### 32. 缺少启动配置校验
- **文件**: `app/main.py`
- **问题**: 应用启动时不检查必要环境变量，运行时才报错。
- **修复**: 在 lifespan 启动前新增 `validate_required_settings()` 函数，校验 JWT 密钥、SiliconFlow API Key、AI API Key 三项必填配置，缺失或仍为默认值时记录错误日志并抛出 `RuntimeError` 阻止启动。
- **状态**: ✅ 已完成

---

## 第二阶段：代码缺陷与 Bug 修复

### 6. embedding_service 批量嵌入索引映射错误
- **文件**: `app/services/embedding_service.py`
- **问题**: `embed_texts` 方法中，API 返回的 `response.data` 的 `.index` 是原始请求中的索引，而非在 `uncached_texts` 子列表中的索引。当前 `embeddings_dict[idx]` 中的 `idx` 是 enumerate 计数，与 API 返回的 index 不一定对应。
- **修复**: 使用 `response.data[i].embedding` 直接按顺序取，或用 `e.index` 做正确映射。

### 7. llm_service 中 usage 序列化方式过时
- **文件**: `app/services/llm_service.py`
- **问题**: `response.usage.dict()` 是 Pydantic v1 写法。当前项目用 Pydantic v2（`pydantic-settings`），应改为 `response.usage.model_dump()`。
- **修复**: 两处 `.dict()` 改为 `.model_dump()`，或加兼容处理。

### 8. order_agent 仅处理单个 function_call
- **文件**: `app/agents/order_agent.py`
- **问题**: 模型可能返回多个 `tool_calls`，当前只取 `message.tool_calls[0]`，后续调用被丢弃。
- **修复**: 循环处理所有 tool_calls，依次执行并收集结果。

### 9. 工具函数中数据库会话管理不规范
- **文件**: `app/agents/order_agent.py`
- **问题**: 工具函数（`get_order_by_number` 等）手动 `SessionLocal()` + `try/finally/close`，与 FastAPI 的依赖注入体系脱节，且容易遗漏关闭。
- **修复**: 使用 context manager (`with SessionLocal() as db:`) 或将 db session 作为参数传入工具函数。

### 10. get_db 重复定义
- **文件**: `app/api/endpoints.py`、`app/database/__init__.py`
- **问题**: `get_db` 函数在两处各定义了一次，`endpoints.py` 中的版本未被 `order_agent` 等模块使用。
- **修复**: 统一使用 `app/database/__init__.py` 中的 `get_db`，删除 endpoints 中的重复定义。

### 11. 监控端点 Windows 不兼容
- **文件**: `app/api/monitoring.py`
- **问题**: `psutil.disk_usage("/")` 在 Windows 上 "/" 不是合法路径，会抛异常。
- **修复**: 使用跨平台方式如 `psutil.disk_usage(os.path.splitdrive(os.getcwd())[0] + "\\" if os.name == "nt" else "/")`，或直接用 `"."`。

### 12. streamlit_app.py 存在未使用的 import
- **文件**: `streamlit_app.py`
- **问题**: `import json` 和 `from datetime import datetime` 未使用。
- **修复**: 删除未使用的 import。

---

## 第三阶段：架构与设计改进

### 13. 缺少数据库迁移机制
- **问题**: 当前用 `Base.metadata.create_all()` 创建表，无法应对 schema 变更（如加字段、改类型）。
- **修复**: 引入 Alembic 做数据库版本迁移管理。

### 14. 对话历史未持久化
- **文件**: `app/api/endpoints.py` 中 `get_chat_history` 是占位
- **问题**: 聊天历史完全依赖客户端传递，服务端无存储，无法支持历史查询、上下文恢复。
- **修复**: 新增 `Conversation` 和 `Message` 表，存储对话记录；实现 `/chat/history` 端点。

### 15. 限流状态仅存内存
- **文件**: `app/middleware/rate_limit.py`
- **问题**: 限流计数存在进程内存中，多实例部署时失效，重启后清零。
- **修复**: 生产环境改用 Redis 存储；开发阶段可保持内存方案但需文档说明。

### 16. 意图分类增加额外延迟和成本
- **文件**: `app/agents/router_agent.py`
- **问题**: 每次请求都先调一次 LLM 做意图分类，再路由到对应 Agent，多了一次 API 调用，延迟翻倍、成本翻倍。
- **修复方案**:
  - (a) 将意图分类作为 system prompt 的一部分交给路由 Agent 一次完成，用 tool_choice 控制；
  - (b) 用简单规则/关键词预过滤，LLM 只处理模糊情况；
  - (c) 缓存意图分类结果。

### 17. 产品数据双源不一致
- **问题**: `data/products.csv`（30 个真实产品）与 `init_sample_data.py` 中硬编码的 8 个产品是两套数据，SQLite 和 ChromaDB 中的产品不同步。
- **修复**: 统一数据源，`init_sample_data.py` 也从 `products.csv` 读取，或建立同步机制确保 DB 与向量库一致。

### 18. 缺少 API 版本控制
- **文件**: `app/main.py`
- **问题**: 路由前缀为 `/api`，无版本号。未来接口变更会破坏兼容性。
- **修复**: 改为 `/api/v1`，为后续演进留空间。

### 19. 缺少请求 ID / 链路追踪
- **问题**: 日志中无请求级标识，排查问题时无法关联同一请求的多条日志。
- **修复**: 在 RequestLoggingMiddleware 中生成 `request_id`，注入到日志 context 和响应 header 中。

### 20. requirements.txt 无版本锁定
- **文件**: `requirements.txt`
- **问题**: 所有依赖均无版本号，不同环境安装可能得到不兼容版本。
- **修复**: 使用 `pip freeze > requirements.txt` 锁定版本，或至少指定主要依赖的最低兼容版本。

---

## 第四阶段：功能补全

### 21. 测试代码为空
- **文件**: `tests/test_api.py`、`tests/test_agents.py`
- **问题**: 两个测试文件内容为空，没有任何实际测试。
- **修复**: 编写核心测试：
  - API 端点测试（注册、登录、聊天）
  - Agent 逻辑测试（意图分类、工具调用、RAG 检索）
  - Service 层测试（embedding、vector_store、order_service）
  - 可用 `pytest-asyncio` + `httpx.AsyncClient` + mock

### 22. evals 目录为空壳
- **问题**: `evals/data/` 和 `evals/results/` 为空，无任何评测脚本或数据。
- **修复**: 
  - 添加意图分类准确率评测
  - 添加 RAG 检索相关性评测（MRR / Recall@K）
  - 添加端到端对话质量评测
  - 将评测结果写入 `evals/results/`

### 23. 聊天历史端点未实现
- **文件**: `app/api/endpoints.py`
- **问题**: `GET /chat/history` 返回占位消息 "聊天历史功能待实现"。
- **修复**: 实现对话持久化后补全此端点。

### 24. 缺少产品/订单管理 CRUD API
- **问题**: 目前只有查询，没有产品增删改、订单创建/取消等管理接口。
- **修复**: 新增 `/api/products`、`/api/orders` 的 CRUD 端点，至少支持基本的管理操作。

### 25. 缺少流式响应支持
- **文件**: `app/services/llm_service.py`
- **问题**: `stream=True` 参数存在但未实现流式返回逻辑，streamlit 前端也没有流式渲染。
- **修复**: 
  - 后端用 `StreamingResponse` 返回 SSE 流；
  - 前端 Streamlit 用 `st.write_stream` 渲染。

### 26. 缺少 WebSocket 支持
- **问题**: 聊天场景下 HTTP 轮询体验差，应支持 WebSocket 双向通信。
- **修复**: 新增 `/ws/chat` WebSocket 端点，支持实时对话。

---

## 第五阶段：部署与文档

### 27. 缺少 Dockerfile
- **问题**: todo.md 提到但未创建。
- **修复**: 编写 Dockerfile，基于 `python:3.11-slim`，含依赖安装、数据初始化、启动命令。

### 28. CORS 配置过于宽松
- **文件**: `app/main.py`
- **问题**: `allow_origins=["*"]`，生产环境有安全风险。
- **修复**: 从配置读取允许的域名列表，生产环境限制为具体域名。

### 29. 日志配置简陋
- **文件**: `app/main.py`
- **问题**: 仅用 `logging.basicConfig`，无日志轮转、无结构化日志、无级别过滤。
- **修复**: 使用 `logging.handlers.RotatingFileHandler`，或引入 `structlog` 做结构化日志。

### 30. README 内容不完整
- **文件**: `README.md`
- **问题**: 
  - API 端点列表不完整（缺少认证端点、监控端点等）；
  - 缺少项目架构说明；
  - 缺少环境变量说明；
  - 缺少 Streamlit 前端启动方式。
- **修复**: 补全文档内容，与实际代码保持一致。

### 31. 缺少 .env 验证
- **问题**: 应用启动时不检查必要环境变量是否已配置，运行时才报错。
- **修复**: 在 `lifespan` 或 config 模块中加入启动时校验，缺失必填项时给出明确提示并退出。

---

## 附：优先级汇总

| 优先级 | 编号 | 简述 |
|--------|------|------|
| P0-紧急 | 1-5 | 安全漏洞：密码明文哈希、JWT无签名、密钥硬编码 |
| P1-重要 | 6-12 | 代码Bug：嵌入索引映射、单tool_call、DB会话管理、重复定义 |
| P2-改进 | 13-20 | 架构：DB迁移、历史持久化、数据双源、版本控制、日志链路 |
| P3-功能 | 21-26 | 功能：测试、评测、CRUD API、流式响应、WebSocket |
| P4-部署 | 27-31 | 部署：Docker、CORS、日志、文档、启动校验 |
