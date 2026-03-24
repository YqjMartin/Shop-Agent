"""请求日志中间件"""
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("shop_agent")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"

        # 记录请求
        logger.info(f"请求开始: {request.method} {request.url.path} - {client_ip}")

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # 记录响应
            logger.info(
                f"请求完成: {request.method} {request.url.path} - "
                f"状态:{response.status_code} - 耗时:{duration:.3f}s"
            )
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"请求异常: {request.method} {request.url.path} - "
                f"错误:{str(e)} - 耗时:{duration:.3f}s"
            )
            raise