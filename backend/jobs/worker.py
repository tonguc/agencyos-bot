"""
ARQ worker entry point.

Run with:
    arq jobs.worker.WorkerSettings
"""

import logging

from arq.connections import RedisSettings

from config import settings
from jobs.tasks.audit import run_audit_job
from jobs.tasks.collect import run_collect_job
from jobs.tasks.outreach import run_outreach_job
from jobs.tasks.proposal import run_proposal_job

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    logger.info("ARQ worker başladı")


async def shutdown(ctx: dict) -> None:
    logger.info("ARQ worker durdu")


class WorkerSettings:
    functions = [run_audit_job, run_outreach_job, run_proposal_job, run_collect_job]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 300  # 5 minutes max per job
