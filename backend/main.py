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
from api.router import api_router
from api.routes import health

setup_logging(level=settings.LOG_LEVEL, log_file=settings.LOG_FILE)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AgencyOS API başlıyor | env=%s", settings.APP_ENV)
    app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_dsn))
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

app.add_middleware(APIKeyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(api_router)
