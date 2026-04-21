# 电商管理客服项目实践计划

## 项目概述
基于RAG和Agent的极简版电商管理客服系统，面向实习招聘丰富简历。核心功能包括：
- 大模型API接入和对话
- Tool Calling：查询订单物流状态
- RAG：产品推荐（基于向量检索）
- Web API服务（FastAPI）

## 技术栈建议
- **编程语言**: Python 3.9+
- **大模型API**: DeepSeek（OpenAI兼容API）或OpenAI/Claude/通义千问等
- **Web框架**: FastAPI（轻量、异步支持好）
- **向量数据库**: ChromaDB（轻量、易用）或FAISS
- **结构化数据库**: SQLite（开发）/ PostgreSQL（生产）
- **向量嵌入模型**: sentence-transformers（本地）或OpenAI embeddings
- **工具调用框架**: 可选用LangChain，或手动实现
- **前端展示（可选）**: Streamlit或简单的HTML页面

## 项目结构建议
```
shop-agent/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI应用入口
│   ├── api/
│   │   ├── __init__.py
│   │   ├── endpoints.py     # API路由
│   │   └── models.py        # Pydantic模型
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # 配置管理
│   │   └── security.py      # 认证（可选）
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py    # 基础Agent类
│   │   ├── order_agent.py   # 订单查询Agent
│   │   └── rag_agent.py     # RAG产品推荐Agent
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_service.py   # 大模型服务封装
│   │   ├── embedding_service.py  # 向量嵌入服务
│   │   ├── vector_store.py  # 向量数据库操作
│   │   └── order_service.py # 订单数据库操作
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py        # SQLAlchemy模型
│   │   └── crud.py          # 数据库CRUD操作
│   └── schemas/
│       ├── __init__.py
│       └── schemas.py       # 数据模式定义
├── data/
│   ├── products.csv         # 产品数据（用于RAG）
│   └── orders.csv           # 订单数据（示例）
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   └── test_agents.py
├── .env.example             # 环境变量示例
├── requirements.txt
├── Dockerfile（可选）
└── README.md
```

## 实施步骤

### 第一阶段：项目基础搭建（1-2天）
**目标**：建立项目骨架，配置开发环境

#### 任务清单：
1. **初始化项目**
   - [x] 创建Python虚拟环境：`python -m venv venv`
   - [x] 激活虚拟环境
   - [x] 创建项目目录结构（如上所示）

2. **依赖管理**
   - [x] 创建`requirements.txt`文件，包含：
     - fastapi
     - uvicorn
     - python-dotenv
     - openai（或其他大模型SDK）
     - chromadb（或faiss-cpu）
     - sentence-transformers
     - sqlalchemy
     - pydantic
     - httpx
   - [x] 安装依赖：`pip install -r requirements.txt`

3. **配置管理**
   - [x] 创建`.env.example`文件，包含：
     - DEEPSEEK_API_KEY（或其他大模型API密钥）
     - DATABASE_URL
   - [x] 创建`.env`文件（本地开发用，添加到.gitignore）
   - [x] 创建配置模块`app/core/config.py`

4. **FastAPI基础**
   - [x] 创建`app/main.py`，初始化FastAPI应用
   - [x] 添加健康检查端点`/health`

### 第二阶段：大模型集成（1-2天）
**目标**：集成大模型API，实现基础对话功能

#### 任务清单：
1. **大模型服务封装**
   - [x] 创建`app/services/llm_service.py`
   - [x] 实现DeepSeek API调用（OpenAI兼容API）
   - [x] 添加流式响应支持（可选）
   - [x] 添加错误处理和重试机制

2. **基础对话API**
   - [x] 创建`/api/chat`端点
   - [x] 实现简单的对话功能
   - [x] 添加请求/响应模型（Pydantic）

3. **测试对话功能**
   - [x] 使用curl或Postman测试API
   - [x] 验证大模型响应正常

### 第三阶段：Tool Calling实现（2-3天）
**目标**：实现订单查询功能，包括数据库和工具调用

#### 任务清单：
1. **数据库设计**
   - [x] 设计订单表结构（订单ID、用户ID、产品、物流状态等）
   - [x] 创建SQLAlchemy模型`app/database/models.py`
   - [x] 初始化数据库连接

2. **订单服务**
   - [x] 创建`app/services/order_service.py`
   - [x] 实现订单查询函数`get_order_status(order_id)`
   - [x] 实现模糊查询`search_orders_by_product(product_name)`

3. **Tool Calling机制**
   - [x] 研究大模型的Tool Calling格式（OpenAI函数调用）
   - [x] 在`app/agents/order_agent.py`中实现：
     - 工具定义（函数名、参数、描述）
     - 工具调用解析
     - 执行工具并返回结果
   - [x] 集成到对话流程中

4. **测试订单查询**
   - [x] 准备示例订单数据
   - [x] 测试工具调用：查询订单状态功能
   - [x] 测试自然语言查询：搜索商品订单功能

### 第四阶段：RAG实现（2-3天）
**目标**：实现产品推荐功能，基于向量检索

#### 任务清单：
1. **产品数据准备**
   - [x] 收集或生成示例产品数据（名称、描述、类别、价格等）
   - [x] 保存到`data/products.csv`
   - [ ] 设计产品数据库表（可选）

2. **向量嵌入服务**
   - [x] 创建`app/services/embedding_service.py`
   - [x] 选择嵌入模型：使用DeepSeek Embeddings (OpenAI兼容API)
   - [x] 实现文本到向量的转换函数

3. **向量数据库**
   - [x] 创建`app/services/vector_store.py`
   - [x] 初始化ChromaDB/FAISS
   - [x] 实现产品数据导入：读取CSV → 生成嵌入 → 存储向量
   - [x] 实现相似性检索函数`search_similar_products(query, k=5)`

4. **RAG Agent**
   - [x] 创建`app/agents/rag_agent.py`
   - [x] 实现检索增强生成流程：
     1. 用户查询 → 向量检索 → 相关产品
     - [x] 构建提示词，包含产品信息
     - [x] 调用大模型生成推荐
   - [x] 集成到对话API

5. **测试RAG功能**
   - [x] 测试查询："有什么好用的机械键盘？"
   - [x] 验证返回相关产品推荐

### 第五阶段：系统集成与优化（2-3天）
**目标**：整合所有功能，优化用户体验

#### 任务清单：
1. **统一Agent架构**
   - [x] 创建`app/agents/router_agent.py`，统一工具调用和RAG流程
   - [x] 实现意图识别：判断用户问题是订单查询还是产品推荐
   - [x] 实现多轮对话状态管理

2. **用户认证与上下文**
   - [x] 实现用户登录/注册接口（JWT认证）
   - [x] 在对话API中获取当前用户身份
   - [x] Agent根据用户身份查询个人订单/历史

3. **API完善**
   - [x] 统一对话接口，支持自动选择功能
   - [x] 添加请求日志和监控
   - [x] 添加速率限制（可选）

4. **前端界面**
   - [x] 使用Streamlit创建简单聊天界面（streamlit_app.py）
   - [x] 调用后端API实现登录/注册/聊天功能

5. **性能优化**
   - [x] 向量检索缓存（embedding_service.py, vector_store.py）
   - [x] 对话历史管理
   - [x] 错误处理和用户友好提示（main.py 全局异常处理）


## 时间估算
- **总计**：约9-15天（取决于每天投入时间和经验水平）
- **灵活调整**：根据实习时间安排，可先实现核心功能，再逐步完善

## 成功标准
1. ✅ 用户可以通过API进行自然语言对话
2. ✅ 系统能识别订单查询意图，调用工具返回物流状态
3. ✅ 系统能通过向量检索推荐相关产品
4. ✅ 所有功能通过API暴露，可供前端调用
5. ✅ 代码结构清晰，有基本文档和测试

## 后续扩展方向
1. **更多工具**：添加退货申请、库存查询、客服转接等
2. **多模态**：支持图片上传识别产品
3. **知识库更新**：定期更新产品向量库
4. **用户认证**：添加用户登录和权限管理
5. **部署到云服务**：AWS/GCP/Azure部署，添加监控

---

**备注**：本计划为建议性指导，可根据实际情况调整顺序和内容。优先实现核心功能（Tool Calling和RAG），再考虑优化和扩展。
**请根据实际完成情况更新该内容**