import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 应用配置
    app_name: str = "Shop Agent"
    debug: bool = True
    log_level: str = "info"
    
    # AI配置 (OpenAI兼容)
    ai_api_key: str
    ai_base_url: str = "https://api.deepseek.com"
    ai_model: str = "deepseek-chat"
    
    # 数据库配置
    database_url: str = "sqlite:///./shop_agent.db"
    
    # 向量数据库配置
    chroma_db_path: str = "./chroma_db"
    # faiss_index_path: Optional[str] = None
    
    # 可选缓存配置
    redis_url: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
