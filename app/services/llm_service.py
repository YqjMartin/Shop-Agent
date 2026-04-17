import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """大模型服务，使用DeepSeek (OpenAI兼容API)"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url,
        )
        self.model = settings.ai_model  # 模型名称
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """调用DeepSeek聊天补全"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                **kwargs
            )

            if stream:
                return response
            else:
                return {
                    "content": response.choices[0].message.content,
                    "role": response.choices[0].message.role,
                    "finish_reason": response.choices[0].finish_reason,
                    "usage": response.usage.model_dump() if response.usage else None,
                }

        except Exception as e:
            logger.error(f"DeepSeek API调用失败: {e}")
            raise
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """生成文本响应"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.chat_completion(messages, **kwargs)
        return response["content"]

    async def chat_completion_with_functions(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        function_call: str = "auto",
        **kwargs
    ) -> Dict[str, Any]:
        """带函数调用的聊天补全"""
        try:
            # 使用 tools 参数 (OpenAI 最新格式)
            tool_choice = {"type": "function", "function": {"name": function_call}} if function_call != "auto" else function_call
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=functions,
                tool_choice=tool_choice,
                **kwargs
            )

            message = response.choices[0].message
            result = {
                "content": message.content,
                "role": message.role,
                "finish_reason": response.choices[0].finish_reason,
                "usage": response.usage.model_dump() if response.usage else None,
            }

            # 检查是否有函数调用 (tool_calls)
            if message.tool_calls:
                result["function_call"] = {
                    "name": message.tool_calls[0].function.name,
                    "arguments": message.tool_calls[0].function.arguments
                }

            return result

        except Exception as e:
            logger.error(f"函数调用API失败: {e}")
            raise


# 全局LLM服务实例
llm_service = LLMService()
