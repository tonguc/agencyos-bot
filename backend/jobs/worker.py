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
    # Apify default timeout = 200s; ARQ job_timeout > Apify + buffer (40s) ki Apify
    # kendi abort mesajını verip cost'u görelim. ARQ 300 → 240 değişti.
    job_timeout = 240
    # Transient fail (Claude 429/529, network blip, kısa Apify hıçkırığı) için 1 retry.
    # GÜVENLİK: Task'lar idempotent — service'lerde since_dt=job.created_at guard var,
    # retry sırasında zaten yazılmış audit/outreach/proposal'ı bulup Claude/Apify
    # çağrısı yapmadan döner. Körleme retry değil — idempotency korumalı.
    max_tries = 2
    retry_delay = 15  # saniye
