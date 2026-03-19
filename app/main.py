from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.endpoints import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    yield
    # 关闭时清理资源
    from app.services.llm_service import llm_service
    await llm_service.close()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    description="基于RAG和Agent的电商管理客服系统",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API路由
app.include_router(api_router, prefix="/api", tags=["聊天"])


@app.get("/")
async def root():
    """根路径"""
    return {"message": "欢迎使用电商管理客服系统", "app": settings.app_name}


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "debug": settings.debug
    }
