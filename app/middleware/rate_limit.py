"""速率限制中间件"""
import time
from typing import Dict, List
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# 速率限制配置
RATE_LIMIT_REQUESTS = 30  # 每分钟最多请求数
RATE_LIMIT_WINDOW = 60  # 时间窗口（秒）

# 速率限制存储（内存版，生产环境用Redis）
_rate_limit_store: Dict[str, List[float]] = {}


def get_rate_limit_store() -> Dict[str, List[float]]:
    """获取速率限制存储"""
    return _rate_limit_store


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""

    async def dispatch(self, request: Request, call_next):
        # 仅对API路由限流
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # 清理过期记录
        _rate_limit_store[client_ip] = [
            t for t in _rate_limit_store.get(client_ip, [])
            if current_time - t < RATE_LIMIT_WINDOW
        ]

        # 检查是否超过限制
        if len(_rate_limit_store.get(client_ip, [])) >= RATE_LIMIT_REQUESTS:
            import logging
            logging.getLogger("shop_agent").warning(f"速率限制触发: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后再试"}
            )

        # 记录请求
        if client_ip not in _rate_limit_store:
            _rate_limit_store[client_ip] = []
        _rate_limit_store[client_ip].append(current_time)

        return await call_next(request)