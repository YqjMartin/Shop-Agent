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

    # SiliconFlow 配置 (用于 embeddings) - 必填
    siliconflow_api_key: str
    
    # 数据库配置
    database_url: str = "sqlite:///./data/shop_agent.db"

    # 向量数据库配置
    chroma_db_path: str = "./data/chroma_db"

    # JWT配置 - 必填，生产环境必须更换
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
