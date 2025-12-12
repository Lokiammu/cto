from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Application
    app_env: str = "development"
    app_name: str = "FastAPI Backend"
    debug: bool = True
    api_version: str = "v1"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "ecommerce_db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # JWT
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    
    # WebSocket
    websocket_timeout_minutes: int = 30
    
    # LangChain
    openai_api_key: str = ""
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    
    # Sentry
    sentry_dsn: str = ""
    
    # Background Tasks
    enable_background_tasks: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
