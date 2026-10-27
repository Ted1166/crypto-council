from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    ryo_mcp_url: str = ""
    ryo_transport: str = "streamable_http"
    ryo_api_token: str = ""
    ryo_auth_header: str = "Authorization"
    ryo_auth_scheme: str = "Bearer"
    ryo_timeout_seconds: float = 30.0
    ryo_max_retries: int = 2
    ryo_cache_ttl_seconds: float = 20.0
    ryo_max_concurrency: int = 4

    llm_provider: str = "anthropic"
    llm_model: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_max_tokens: int = 1800
    llm_timeout_seconds: float = 90.0

    database_path: str = "data/council.db"
    cors_origins: str = "http://localhost:5173"
    max_crossexams_per_case: int = 6

    @property
    def ryo_configured(self) -> bool:
        return bool(self.ryo_mcp_url)

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key and self.llm_model)

    @property
    def cors_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
