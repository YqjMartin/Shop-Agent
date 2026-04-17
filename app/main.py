"""FastAPI应用入口"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.middleware import RequestLoggingMiddleware, RateLimitMiddleware
from app.api.endpoints import router as api_router
from app.api.monitoring import router as monitoring_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def validate_required_settings():
    """启动时校验必填配置项"""
    errors = []
    
    # 校验 JWT 密钥
    jwt_secret = settings.jwt_secret_key
    if not jwt_secret or jwt_secret == "your-secret-key-change-in-production":
        errors.append(
            "JWT_SECRET_KEY 未正确配置或仍为默认值。"
            "请通过环境变量设置一个安全的密钥（至少32位随机字符）。"
        )
    
    # 校验 SiliconFlow API Key
    if not settings.siliconflow_api_key:
        errors.append(
            "SILICONFLOW_API_KEY 未设置。"
            "请在 .env 文件中配置 SiliconFlow API Key 以启用 embedding 功能。"
        )
    
    # 校验 AI API Key
    if not settings.ai_api_key:
        errors.append(
            "AI_API_KEY 未设置。"
            "请在 .env 文件中配置大模型 API Key。"
        )
    
    if errors:
        logger.error("应用启动失败：检测到以下配置问题：")
        for error in errors:
            logger.error(f"  - {error}")
        raise RuntimeError("配置校验失败，请检查环境变量配置。")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动前校验配置
    validate_required_settings()
    
    from app.database import init_db
    from app.database.vector_init import init_vector_store

    # 初始化 SQLite 数据库
    init_db()
    logger.info("SQLite 数据库已初始化")

    # 初始化向量数据库（如果为空则自动初始化）
    await init_vector_store()

    yield
    logger.info("服务已关闭")


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    description="基于RAG和Agent的电商管理客服系统",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有域名访问（生产环境应指定具体域名）
    allow_credentials=True,  # 允许携带 Cookie、Authorization header 等认证信息
    allow_methods=["*"],  # 允许所有 HTTP 方法（GET、POST、PUT、DELETE 等）
    allow_headers=["*"],  # 允许所有 HTTP 头（Content-Type、Authorization 等）
)

# 中间件
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# 注册异常处理器
register_exception_handlers(app)

# 路由
app.include_router(api_router, prefix="/api", tags=["聊天"])
app.include_router(monitoring_router, tags=["监控"])


@app.get("/")
async def root():
    return {"message": "欢迎使用电商管理客服系统", "app": settings.app_name}