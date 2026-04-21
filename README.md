# Shop Agent - 电商管理客服系统

基于RAG和Agent的极简版电商管理客服系统

## 功能特性

- **大模型对话**: 集成DeepSeek大模型API (OpenAI兼容)
- **Tool Calling**: 订单查询物流状态
- **RAG产品推荐**: 基于向量检索的产品推荐
- **AgentMemory（阶段1+2）**: 对话历史压缩（最近3轮完整 + 历史摘要），并支持模式识别与结构化用户记忆
- **Web API**: FastAPI提供RESTful接口

## 项目结构

```
shop-agent/
├── app/                    # 应用代码
│   ├── api/               # API路由和模型
│   ├── agents/            # Agent实现
│   ├── services/          # 业务服务
│   ├── database/          # 数据库模型和操作
│   ├── core/              # 核心配置
│   └── schemas/           # 数据模式定义
├── data/                  # 示例数据
├── tests/                 # 测试代码
├── .env.example           # 环境变量模板
├── requirements.txt       # Python依赖
└── README.md              # 项目说明
```

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd shop-agent

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 复制环境变量配置
cp .env.example .env
# 编辑.env文件，填入你的API密钥
```

### 2. 运行应用

```bash
# 启动FastAPI服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 访问API文档

启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API端点

- `POST /api/chat`: 对话接口
- `POST /api/chat/auto`: 统一路由对话（已接入AgentMemory压缩）
- `POST /api/chat/order`: 订单查询对话（已接入AgentMemory压缩）
- `POST /api/chat/product`: 产品推荐对话（已接入AgentMemory压缩）
- `GET /health`: 健康检查

## 测试

```bash
# Windows (PowerShell) 使用项目虚拟环境运行第一阶段单测
.\.venv\Scripts\python.exe -m pytest tests/test_agent_memory.py -q
```

## 开发计划

详细开发计划请参考 [todo.md](todo.md)

## 技术栈

- **Python 3.9+**
- **FastAPI** - Web框架
- **DeepSeek API** - 大模型接入 (OpenAI兼容)
- **ChromaDB/FAISS** - 向量数据库
- **SQLAlchemy** - ORM
- **Pydantic** - 数据验证

