from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_ENV: str = "development"
    AGENCYOS_API_KEY: str = "changeme"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://agencyos:agencyos@localhost:5432/agencyos"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # External APIs
    CLAUDE_API_KEY: str = ""
    APIFY_API_TOKEN: str = ""
    PAGESPEED_API_KEY: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "agencyos.log"

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
