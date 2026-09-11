from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_ENV: str = "development"
    AGENCYOS_API_KEY: str = "changeme"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://agencyos:agencyos@localhost:5432/agencyos"

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    @property
    def redis_dsn(self) -> str:
        url = self.REDIS_URL.strip()
        if not url:
            raise ValueError("REDIS_URL boş olamaz")
        return url if url.startswith(("redis://", "rediss://", "unix://")) else "redis://" + url

    # External APIs
    CLAUDE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    APIFY_API_TOKEN: str = ""
    PAGESPEED_API_KEY: str = ""
    SERPAPI_API_KEY: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "agencyos.log"

    # Lead filtering
    ICP_STRICT_MODE: bool = False

    # Claude model
    CLAUDE_MODEL: str = "claude-sonnet-4-6"

    # Playbooks directory (relative to backend/)
    PLAYBOOKS_DIR: str = "playbooks"

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
