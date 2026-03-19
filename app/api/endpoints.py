from typing import List
from fastapi import APIRouter, HTTPException
from app.api.models import ChatRequest, ChatResponse
from app.services.llm_service import llm_service

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    聊天端点

    处理用户对话请求，调用大模型生成回复。
    """
    try:
        # 构建消息列表
        messages = []

        # 添加系统提示词（如果提供）
        if request.system_prompt:
            messages.append({
                "role": "system",
                "content": request.system_prompt
            })

        # 添加用户消息
        for msg in request.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # 调用大模型
        response = await llm_service.chat_completion(
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        return ChatResponse(
            content=response["content"],
            role=response["role"],
            finish_reason=response.get("finish_reason"),
            usage=response.get("usage")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聊天服务错误: {str(e)}")


@router.get("/chat/history")
async def get_chat_history():
    """获取聊天历史（占位）"""
    return {"message": "聊天历史功能待实现"}
