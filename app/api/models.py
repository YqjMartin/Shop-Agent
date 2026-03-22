from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============ 认证模型 ============

class RegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, description="密码")
    email: Optional[str] = Field(None, description="邮箱")


class LoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """登录响应"""
    access_token: str = Field(..., description="JWT访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    user_id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")


class UserInfo(BaseModel):
    """用户信息"""
    id: int
    username: str
    email: Optional[str] = None


# ============ 聊天模型 ============

class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="消息角色: system, user, assistant")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """聊天请求"""
    messages: List[ChatMessage] = Field(..., description="消息列表")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: Optional[int] = Field(default=None, description="最大token数")
    system_prompt: Optional[str] = Field(default=None, description="系统提示词")
    user_id: Optional[int] = Field(default=None, description="用户ID（可选，用于获取用户上下文）")


class ChatResponse(BaseModel):
    """聊天响应"""
    content: str = Field(..., description="回复内容")
    role: str = Field(default="assistant", description="回复角色")
    finish_reason: Optional[str] = Field(default=None, description="结束原因")
    usage: Optional[Dict[str, Any]] = Field(default=None, description="token使用量")
    tool_used: Optional[bool] = Field(default=False, description="是否使用了工具调用")
    tool_name: Optional[str] = Field(default=None, description="使用的工具名称")
    intent: Optional[str] = Field(default=None, description="识别的用户意图: order_query, product_recommend, general")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    app: str
    debug: bool
