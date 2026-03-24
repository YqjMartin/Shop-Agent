"""全局异常处理模块"""
import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append(f"{field}: {error['msg']}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "请求参数验证失败",
            "details": errors,
            "status_code": 422,
        },
    )


async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.exception(f"未处理的异常: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "服务器内部错误，请稍后重试",
            "status_code": 500,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """注册所有异常处理器到应用"""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
