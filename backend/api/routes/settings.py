import asyncio
import os

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.playbook import list_playbooks, list_top_level_sectors
from database import get_db
from repositories.api_usage import ApiUsageRepository
from schemas.settings import SettingsOut, TestResult, ServiceUsage, UsageOut, SpendOut

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
async def get_settings():
    return SettingsOut(
        app_env=settings.APP_ENV,
        claude_model=settings.CLAUDE_MODEL,
        pagespeed_configured=bool(settings.PAGESPEED_API_KEY),
        apify_configured=bool(settings.APIFY_API_TOKEN),
        playbooks=list_top_level_sectors(),
    )


@router.post("/test/claude", response_model=TestResult)
async def test_claude():
    try:
        from core.utils import claude_api_call
        resp = await claude_api_call("Merhaba, bu bir test.", max_tokens=10)
        return TestResult(ok=True, message=f"OK: {resp[:50]}")
    except Exception as e:
        return TestResult(ok=False, message=str(e))


@router.post("/test/apify", response_model=TestResult)
async def test_apify():
    token = settings.APIFY_API_TOKEN
    if not token:
        return TestResult(ok=False, message="APIFY_API_TOKEN ayarli degil")
    try:
        import requests
        r = requests.get(
            "https://api.apify.com/v2/users/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        r.raise_for_status()
        return TestResult(ok=True, message=f"Apify OK: {r.json().get('username', 'user')}")
    except Exception as e:
        return TestResult(ok=False, message=str(e))


@router.get("/usage", response_model=UsageOut)
async def get_usage():
    claude_usage, openai_usage, apify_usage = await asyncio.gather(
        _check_claude(),
        _check_openai(),
        _check_apify(),
    )
    return UsageOut(claude=claude_usage, openai=openai_usage, apify=apify_usage)


async def _check_claude() -> ServiceUsage:
    key = settings.CLAUDE_API_KEY
    if not key:
        return ServiceUsage(ok=False, label="Claude", detail="API key tanımlı değil",
                            dashboard_url="https://console.anthropic.com")
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                json={"model": "claude-haiku-4-5-20251001", "max_tokens": 1,
                      "messages": [{"role": "user", "content": "hi"}]},
            )
        if r.status_code in (200, 400):   # 400 = content policy etc, key is valid
            return ServiceUsage(ok=True, label="Claude",
                                detail="Bağlantı OK — bakiye console.anthropic.com'da",
                                dashboard_url="https://console.anthropic.com/settings/billing")
        return ServiceUsage(ok=False, label="Claude", detail=f"HTTP {r.status_code}",
                            dashboard_url="https://console.anthropic.com")
    except Exception as e:
        return ServiceUsage(ok=False, label="Claude", detail=str(e)[:80])


async def _check_openai() -> ServiceUsage:
    key = settings.OPENAI_API_KEY
    if not key:
        return ServiceUsage(ok=False, label="OpenAI", detail="API key tanımlı değil",
                            dashboard_url="https://platform.openai.com/usage")
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                "https://api.openai.com/v1/dashboard/billing/credit_grants",
                headers={"Authorization": f"Bearer {key}"},
            )
        if r.status_code == 200:
            data = r.json()
            total = data.get("total_granted", 0)
            used = data.get("total_used", 0)
            remaining = data.get("total_available", total - used)
            return ServiceUsage(ok=True, label="OpenAI",
                                detail=f"Kalan: ${remaining:.2f} / ${total:.2f}",
                                dashboard_url="https://platform.openai.com/usage")
        # Newer billing system — just verify key works
        async with httpx.AsyncClient(timeout=8) as client:
            r2 = await client.get("https://api.openai.com/v1/models",
                                  headers={"Authorization": f"Bearer {key}"})
        ok = r2.status_code == 200
        return ServiceUsage(ok=ok, label="OpenAI",
                            detail="Bağlantı OK — bakiye platform.openai.com'da" if ok else f"HTTP {r2.status_code}",
                            dashboard_url="https://platform.openai.com/usage")
    except Exception as e:
        return ServiceUsage(ok=False, label="OpenAI", detail=str(e)[:80])


async def _check_apify() -> ServiceUsage:
    key = settings.APIFY_API_TOKEN
    if not key:
        return ServiceUsage(ok=False, label="Apify", detail="API token tanımlı değil",
                            dashboard_url="https://console.apify.com/billing")
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                "https://api.apify.com/v2/users/me",
                headers={"Authorization": f"Bearer {key}"},
            )
        if r.status_code != 200:
            return ServiceUsage(ok=False, label="Apify", detail=f"HTTP {r.status_code}",
                                dashboard_url="https://console.apify.com/billing")
        data = r.json().get("data", {})
        plan = data.get("plan", {})
        used = plan.get("monthlyUsageCreditsUsd", 0)
        limit = plan.get("maxMonthlyUsageCreditsUsd", 0)
        username = data.get("username", "")
        detail = f"{username} · Bu ay: ${used:.2f} / ${limit:.2f}" if limit else f"{username} · Bağlantı OK"
        return ServiceUsage(ok=True, label="Apify", detail=detail,
                            dashboard_url="https://console.apify.com/billing")
    except Exception as e:
        return ServiceUsage(ok=False, label="Apify", detail=str(e)[:80])


@router.get("/spend", response_model=SpendOut)
async def get_spend(db: AsyncSession = Depends(get_db)):
    """Son 24 saat external API spend'i (cost_tracker hook'larindan birikmis)."""
    today = await ApiUsageRepository(db).daily_spend()
    total = round(sum(today.values()), 4)
    budget = settings.DAILY_BUDGET_USD
    used_pct = round(total / budget * 100.0, 1) if budget > 0 else None
    return SpendOut(
        today={p: round(v, 4) for p, v in today.items()},
        total=total,
        budget_usd=budget,
        used_pct=used_pct,
    )


@router.get("/playbooks")
async def get_playbooks():
    return {"playbooks": list_playbooks()}
