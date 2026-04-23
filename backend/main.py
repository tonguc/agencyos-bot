import logging
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import engine
from logging_config import setup_logging
from middleware.auth import APIKeyMiddleware
from middleware.request_id import RequestIDMiddleware
from api.router import api_router
from api.routes import health

setup_logging(level=settings.LOG_LEVEL, log_file=settings.LOG_FILE)
logger = logging.getLogger(__name__)


_WEAK_API_KEYS = {"", "changeme"}


def _check_production_secrets() -> None:
    """Reddet: production'da default/boş API key ile çalışma."""
    if settings.APP_ENV != "production":
        if settings.AGENCYOS_API_KEY in _WEAK_API_KEYS:
            logger.warning(
                "AGENCYOS_API_KEY zayıf (%r) — dev ortamında kabul ediliyor, "
                "production'da reddedilir.",
                settings.AGENCYOS_API_KEY,
            )
        return
    if settings.AGENCYOS_API_KEY in _WEAK_API_KEYS:
        raise RuntimeError(
            "AGENCYOS_API_KEY production'da boş veya 'changeme' olamaz. "
            "Güçlü bir değer belirleyip yeniden başlatın."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _check_production_secrets()
    logger.info("AgencyOS API başlıyor | env=%s", settings.APP_ENV)
    redis_url = settings.REDIS_URL
    if not redis_url.startswith(("redis://", "rediss://", "unix://")):
        redis_url = "redis://" + redis_url
    app.state.arq_pool = await create_pool(RedisSettings.from_dsn(redis_url))
    yield
    await app.state.arq_pool.aclose()
    await engine.dispose()
    logger.info("AgencyOS API durdu.")


app = FastAPI(
    title="AgencyOS API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# RequestIDMiddleware ONCE APIKey — her istege req=... atanip
# auth failure'lari da log'da takip edilebilir.
app.add_middleware(APIKeyMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(api_router)
