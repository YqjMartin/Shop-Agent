"""向量嵌入服务 - 使用 OpenAI 兼容 API (SiliconFlow)"""

import hashlib
import logging
import time
from collections import OrderedDict
from typing import List, Optional
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """内存嵌入缓存（OrderedDict 实现 O(1) LRU）"""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        初始化缓存

        Args:
            max_size: 最大缓存条目数
            ttl_seconds: 缓存过期时间（秒）
        """
        self._cache: OrderedDict[str, tuple[List[float], float]] = OrderedDict()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds

    def _hash(self, text: str) -> str:
        """生成文本哈希"""
        return hashlib.sha256(text.encode()).hexdigest()

    def get(self, text: str) -> Optional[List[float]]:
        """获取缓存的嵌入"""
        key = self._hash(text)
        if key in self._cache:
            embedding, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl_seconds:
                # 移到末尾表示最近使用
                self._cache.move_to_end(key)
                return embedding
            else:
                del self._cache[key]
        return None

    def set(self, text: str, embedding: List[float]) -> None:
        """设置缓存"""
        key = self._hash(text)
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._max_size:
                # 淘汰最旧的（头部）
                self._cache.popitem(last=False)
        self._cache[key] = (embedding, time.time())

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()

    def size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)


class EmbeddingService:
    """向量嵌入服务，使用 SiliconFlow Embeddings (OpenAI 兼容)"""

    def __init__(self, model: str = "BAAI/bge-large-zh-v1.5"):
        """
        初始化嵌入服务

        Args:
            model: 嵌入模型名称
        """
        self.client = AsyncOpenAI(
            api_key=settings.siliconflow_api_key,
            base_url="https://api.siliconflow.cn/v1",
        )
        self.model = model
        self.cache = EmbeddingCache(max_size=500, ttl_seconds=3600)

    async def embed_text(self, text: str) -> List[float]:
        """
        将单个文本转换为向量（带缓存）

        Args:
            text: 输入文本

        Returns:
            向量列表
        """
        cached = self.cache.get(text)
        if cached is not None:
            logger.debug(f"嵌入缓存命中: {text[:30]}...")
            return cached

        try:
            response = await self.client.embeddings.create(model=self.model, input=text)
            embedding = response.data[0].embedding
            self.cache.set(text, embedding)
            return embedding
        except Exception as e:
            logger.error(f"生成嵌入失败: {e}")
            raise

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量将文本转换为向量

        Args:
            texts: 输入文本列表

        Returns:
            向量列表的列表
        """
        result = []
        uncached_texts = []
        uncached_indices = []

        for i, text in enumerate(texts):
            cached = self.cache.get(text)
            if cached is not None:
                result.append(cached)
            else:
                result.append(None)
                uncached_texts.append(text)
                uncached_indices.append(i)

        if uncached_texts:
            try:
                response = await self.client.embeddings.create(
                    model=self.model, input=uncached_texts
                )
                # API 返回顺序与请求顺序一致，直接按索引对应
                for idx, embedding_data in enumerate(response.data):
                    i = uncached_indices[idx]
                    result[i] = embedding_data.embedding
                    self.cache.set(texts[i], embedding_data.embedding)
            except Exception as e:
                logger.error(f"批量生成嵌入失败: {e}")
                raise

        return result


# 全局实例
embedding_service = EmbeddingService()
