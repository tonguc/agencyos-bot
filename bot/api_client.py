"""
Thin async wrapper around the AgencyOS FastAPI.
All bot handlers use this — zero direct core/DB imports in bot/.
"""

import asyncio
import logging
import os

import httpx

logger = logging.getLogger(__name__)

_BASE = os.getenv("AGENCYOS_API_URL", "http://localhost:8000")
_KEY = os.getenv("AGENCYOS_API_KEY", "changeme")
_HEADERS = {"X-API-Key": _KEY, "Content-Type": "application/json"}

_POLL_INTERVAL = 2.0   # seconds between job status checks
_POLL_TIMEOUT = 300    # max seconds to wait for a job


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=_BASE, headers=_HEADERS, timeout=30)


# ── helpers ────────────────────────────────────────────────────────────

async def _get(path: str) -> dict | None:
    async with _client() as c:
        try:
            r = await c.get(path)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            logger.error("GET %s hatasi: %s", path, e)
            raise


async def _post(path: str, body: dict | None = None) -> dict:
    async with _client() as c:
        r = await c.post(path, json=body or {})
        r.raise_for_status()
        return r.json()


async def _patch(path: str, body: dict) -> dict:
    async with _client() as c:
        r = await c.patch(path, json=body)
        r.raise_for_status()
        return r.json()


async def poll_job(job_id: str) -> dict:
    """Poll /api/jobs/{id} until status is completed or failed."""
    deadline = asyncio.get_event_loop().time() + _POLL_TIMEOUT
    while True:
        job = await _get(f"/api/jobs/{job_id}")
        if not job:
            raise RuntimeError(f"Job bulunamadi: {job_id}")
        status = job["status"]
        if status in ("completed", "failed"):
            return job
        if asyncio.get_event_loop().time() > deadline:
            raise TimeoutError(f"Job zaman asimi: {job_id}")
        await asyncio.sleep(_POLL_INTERVAL)


# ── leads ──────────────────────────────────────────────────────────────

async def list_leads(status: str | None = None, limit: int = 10) -> dict:
    q = f"?limit={limit}" + (f"&status={status}" if status else "")
    return await _get(f"/api/leads{q}") or {"items": [], "total": 0}


async def get_lead(lead_id: str) -> dict | None:
    return await _get(f"/api/leads/{lead_id}")


async def pipeline_counts() -> dict:
    data = await _get("/api/leads/pipeline")
    return (data or {}).get("counts", {})


# ── jobs via triggers ──────────────────────────────────────────────────

async def trigger_scrape(sector: str, city: str, district: str, limit: int) -> dict:
    return await _post("/api/scrape", {"sector": sector, "city": city, "district": district, "limit": limit})


async def trigger_audit(lead_id: str) -> dict:
    return await _post(f"/api/leads/{lead_id}/audit")


async def trigger_outreach(lead_id: str) -> dict:
    return await _post(f"/api/leads/{lead_id}/outreach")


async def trigger_proposal(lead_id: str) -> dict:
    return await _post(f"/api/leads/{lead_id}/proposal")


# ── get results ────────────────────────────────────────────────────────

async def get_audit(lead_id: str) -> dict | None:
    return await _get(f"/api/leads/{lead_id}/audit")


async def get_outreach(lead_id: str) -> dict | None:
    return await _get(f"/api/leads/{lead_id}/outreach")


async def get_proposal(lead_id: str) -> dict | None:
    return await _get(f"/api/leads/{lead_id}/proposal")


async def mark_sent(lead_id: str, outreach_id: str, version: str, channel: str = "whatsapp") -> dict:
    return await _patch(
        f"/api/leads/{lead_id}/outreach/{outreach_id}/send",
        {"version": version, "channel": channel},
    )


async def get_followup(lead_id: str) -> str:
    data = await _post(f"/api/leads/{lead_id}/followup")
    return data.get("text", "")


async def download_pdf(proposal_id: str) -> bytes:
    async with _client() as c:
        r = await c.get(f"/api/proposals/{proposal_id}/pdf", timeout=60)
        r.raise_for_status()
        return r.content
