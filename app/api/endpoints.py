from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.models import (
    ChatRequest,
    ChatResponse,
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserInfo,
)
from app.services.llm_service import llm_service
from app.services.agent_memory import AgentMemory
from app.agents.order_agent import order_agent
from app.agents.rag_agent import rag_agent
from app.agents.router_agent import router_agent
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user_id,
    TokenData,
)
from app.database import SessionLocal, get_db
from app.database.models import User

router = APIRouter()


def _extract_user_message_and_history(request: ChatRequest) -> tuple[str, list]:
    """提取最后一条用户消息，并返回不含该消息的历史记录。"""
    user_message = None
    user_index = None
    for idx in range(len(request.messages) - 1, -1, -1):
        msg = request.messages[idx]
        if msg.role == "user":
            user_message = msg.content
            user_index = idx
            break

    if not user_message:
        raise HTTPException(status_code=400, detail="未找到用户消息")

    history_messages = request.messages
    if user_index is not None:
        history_messages = (
            request.messages[:user_index] + request.messages[user_index + 1 :]
        )

    return user_message, history_messages


# ============ 认证端点 ============


@router.post("/auth/register", response_model=TokenResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    用户注册接口

    注册新用户并返回 JWT 令牌。
    """
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 创建新用户
    hashed_pwd = hash_password(request.password)
    new_user = User(
        username=request.username, email=request.email, hashed_password=hashed_pwd
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 生成 JWT 令牌
    access_token = create_access_token(
        data={"sub": str(new_user.id), "username": new_user.username}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=new_user.id,
        username=new_user.username,
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录接口

    验证凭据并返回 JWT 令牌。
    """
    # 查找用户
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 验证密码
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 生成 JWT 令牌
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
    )


@router.get("/auth/me", response_model=UserInfo)
async def get_current_user_info(current_user: TokenData = Depends(get_current_user_id)):
    """
    获取当前登录用户信息

    需要在请求头中携带 Bearer token。
    """
    return UserInfo(id=current_user.user_id, username=current_user.username)


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
            messages.append({"role": "system", "content": request.system_prompt})

        # 添加用户消息
        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})

        # 调用大模型
        response = await llm_service.chat_completion(
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        return ChatResponse(
            content=response["content"],
            role=response["role"],
            finish_reason=response.get("finish_reason"),
            usage=response.get("usage"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聊天服务错误: {str(e)}")


@router.post("/chat/order", response_model=ChatResponse)
async def chat_order(request: ChatRequest):
    """
    订单查询聊天端点

    处理用户订单相关对话请求，使用Tool Calling自动查询订单状态。
    支持：订单号查询、快递单号查询、商品名称搜索、用户订单历史查询。

    集成 AgentMemory 层进行历史压缩。
    """
    try:
        user_message, history_messages = _extract_user_message_and_history(request)

        # ========== 步骤1：初始化记忆并加载历史 ==========
        memory = AgentMemory()

        # 将前端发送的完整历史加载到记忆中
        for msg in history_messages:
            if msg.role in ["user", "assistant"]:
                mode = AgentMemory.detect_mode(msg.content)
                memory.add_interaction(role=msg.role, content=msg.content, mode=mode)

        # ========== 步骤2：获取压缩后的历史 ==========
        compressed_history = memory.get_compressed_history()

        # ========== 步骤3：调用OrderAgent处理 ==========
        result = await order_agent.process(
            user_message,
            compressed_history,  # 使用压缩后的历史
            user_id=request.user_id,
        )

        # ========== 步骤4：记录Agent的响应到记忆 ==========
        memory.add_interaction(
            role="assistant", content=result["content"], mode="order_query"
        )

        # ========== 步骤5：返回结果 ==========
        stats = memory.get_stats()

        return ChatResponse(
            content=result["content"],
            role="assistant",
            finish_reason="stop",
            tool_used=result.get("tool_used", False),
            tool_name=result.get("tool_name"),
            metadata={
                "memory_turns": stats["total_turns"],
                "memory_chars": stats["total_chars"],
                "compressed_history_length": len(compressed_history),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"订单查询服务错误: {str(e)}")


@router.get("/chat/history")
async def get_chat_history():
    """获取聊天历史（占位）"""
    return {"message": "聊天历史功能待实现"}


@router.post("/chat/auto", response_model=ChatResponse)
async def chat_auto(request: ChatRequest):
    """
    智能聊天端点（统一入口）

    自动识别用户意图并路由到相应的Agent：
    - 订单查询意图 -> OrderAgent
    - 产品推荐意图 -> RAGAgent
    - 其他 -> 基础对话

    集成 AgentMemory 层进行历史压缩：
    - 保留最近 3 轮完整对话
    - 更早的对话摘要化处理
    """
    try:
        user_message, history_messages = _extract_user_message_and_history(request)

        # ========== 步骤1：初始化记忆并加载历史 ==========
        memory = AgentMemory()

        # 将前端发送的完整历史加载到记忆中
        for msg in history_messages:
            if msg.role in ["user", "assistant"]:
                mode = AgentMemory.detect_mode(msg.content)
                memory.add_interaction(role=msg.role, content=msg.content, mode=mode)

        # ========== 步骤2：获取压缩后的历史用于意图分类 ==========
        compressed_history = memory.get_compressed_history()

        # ========== 步骤3：调用Router Agent自动路由 ==========
        result = await router_agent.process(
            user_message,
            compressed_history,  # 使用压缩后的历史
            user_id=request.user_id,
        )

        # ========== 步骤4：记录Agent的响应到记忆 ==========
        intent = result.get("intent", "general")
        memory.add_interaction(role="assistant", content=result["content"], mode=intent)

        # ========== 步骤5：返回结果，同时返回压缩统计信息用于调试 ==========
        stats = memory.get_stats()

        return ChatResponse(
            content=result["content"],
            role="assistant",
            finish_reason="stop",
            tool_used=result.get("tool_used", False),
            tool_name=result.get("tool_name"),
            intent=result.get("intent"),
            # 附加调试信息
            metadata={
                "memory_turns": stats["total_turns"],
                "memory_chars": stats["total_chars"],
                "compressed_history_length": len(compressed_history),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"智能聊天服务错误: {str(e)}")


@router.post("/chat/product", response_model=ChatResponse)
async def chat_product(request: ChatRequest):
    """
    产品推荐聊天端点

    处理用户产品相关对话请求，使用RAG检索相关产品并生成推荐。

    集成 AgentMemory 层进行历史压缩。
    """
    try:
        user_message, history_messages = _extract_user_message_and_history(request)

        # ========== 步骤1：初始化记忆并加载历史 ==========
        memory = AgentMemory()

        # 将前端发送的完整历史加载到记忆中
        for msg in history_messages:
            if msg.role in ["user", "assistant"]:
                mode = AgentMemory.detect_mode(msg.content)
                memory.add_interaction(role=msg.role, content=msg.content, mode=mode)

        # ========== 步骤2：获取压缩后的历史 ==========
        compressed_history = memory.get_compressed_history()

        # ========== 步骤3：调用RAG Agent处理 ==========
        result = await rag_agent.process(
            user_message, history=compressed_history  # 使用压缩后的历史
        )

        # ========== 步骤4：记录Agent的响应到记忆 ==========
        memory.add_interaction(
            role="assistant", content=result["content"], mode="product_recommend"
        )

        # ========== 步骤5：返回结果 ==========
        stats = memory.get_stats()

        return ChatResponse(
            content=result["content"],
            role="assistant",
            finish_reason="stop",
            tool_used=result.get("tool_used", False),
            tool_name=result.get("tool_name"),
            metadata={
                "memory_turns": stats["total_turns"],
                "memory_chars": stats["total_chars"],
                "compressed_history_length": len(compressed_history),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"产品推荐服务错误: {str(e)}")
