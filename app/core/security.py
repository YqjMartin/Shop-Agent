"""
安全认证模块

实现 JWT 令牌和密码哈希功能
"""

from datetime import datetime, timedelta
from typing import Optional
import hashlib
import hmac
import base64

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.core.config import settings


# ============ 密码工具 ============

def hash_password(password: str) -> str:
    """对密码进行 SHA256 哈希"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return hash_password(plain_password) == hashed_password


# ============ JWT 工具 ============

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT 访问令牌

    Args:
        data: 要编码的数据（应包含 sub: user_id, username）
        expires_delta: 过期时间 delta

    Returns:
        JWT token 字符串
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = _base64url_encode(to_encode)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码 JWT 令牌

    Args:
        token: JWT token 字符串

    Returns:
        解码后的数据字典，如果过期或无效返回 None
    """
    try:
        payload = _base64url_decode(token)
        # 检查过期时间
        exp = payload.get("exp")
        if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
            return None
        return payload
    except Exception:
        return None


def _base64url_encode(data: dict) -> str:
    """Base64URL 编码"""
    import json

    def json_serial(obj):
        """处理 datetime 等非JSON序列化对象"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    json_bytes = json.dumps(data, separators=(',', ':'), default=json_serial).encode()
    encoded = base64.urlsafe_b64encode(json_bytes).decode()
    # 移除 padding
    return encoded.rstrip('=')


def _base64url_decode(token: str) -> dict:
    """Base64URL 解码"""
    # 添加 padding
    padding = 4 - len(token) % 4
    if padding != 4:
        token += '=' * padding
    decoded = base64.urlsafe_b64decode(token)
    return __import__('json').loads(decoded)


# ============ FastAPI 依赖 ============

security = HTTPBearer()


class TokenData(BaseModel):
    """Token 中的用户数据"""
    user_id: int
    username: str


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    FastAPI 依赖：从 JWT token 获取当前用户 ID

    Raises:
        HTTPException: 如果 token 无效或过期

    Returns:
        TokenData 包含 user_id 和 username
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    username = payload.get("username")

    if user_id is None or username is None:
        raise credentials_exception

    return TokenData(user_id=int(user_id), username=username)