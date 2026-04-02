from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_key: str = ""
    azure_openai_chat_deployment: str = "gpt-4o-mini"
    azure_openai_embed_deployment: str = "text-embedding-3-small"

    # Azure Document Intelligence
    azure_di_endpoint: str = ""
    azure_di_key: str = ""

    # Auth
    secret_key: str = "change-this-in-production"
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    # App
    app_env: str = "development"
    debug: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()