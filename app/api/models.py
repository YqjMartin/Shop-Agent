from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


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


class ChatResponse(BaseModel):
    """聊天响应"""
    content: str = Field(..., description="回复内容")
    role: str = Field(default="assistant", description="回复角色")
    finish_reason: Optional[str] = Field(default=None, description="结束原因")
    usage: Optional[Dict[str, Any]] = Field(default=None, description="token使用量")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    app: str
    debug: bool
