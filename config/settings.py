from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from .env and environment variables."""

    # LLM API
    llm_api_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"
    llm_max_tokens: int = 2000
    llm_temperature: float = 0.7

    # Server
    host: str = "127.0.0.1"
    port: int = 8080

    # Database
    database_url: str = "sqlite:///data/wechat.db"

    # Logging
    log_level: str = "INFO"
    log_dir: str = "data/logs"

    # Paths (resolved relative to project root)
    @property
    def project_root(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @property
    def data_dir(self) -> str:
        d = os.path.join(self.project_root, "data")
        os.makedirs(d, exist_ok=True)
        return d

    @property
    def templates_dir(self) -> str:
        return os.path.join(self.project_root, "templates")

    @property
    def logs_dir(self) -> str:
        d = os.path.join(self.project_root, self.log_dir)
        os.makedirs(d, exist_ok=True)
        return d

    @property
    def skills_dir(self) -> str:
        return os.path.join(self.project_root, "agent", "skills", "builtin")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
