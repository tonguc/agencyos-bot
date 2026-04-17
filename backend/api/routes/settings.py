import os

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.playbook import list_playbooks
from database import get_db
from schemas.settings import SettingsOut, TestResult

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
async def get_settings():
    return SettingsOut(
        app_env=settings.APP_ENV,
        claude_model=settings.CLAUDE_MODEL,
        pagespeed_configured=bool(settings.PAGESPEED_API_KEY),
        apify_configured=bool(settings.APIFY_API_TOKEN),
        playbooks=list_playbooks(),
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


@router.get("/playbooks")
async def get_playbooks():
    return {"playbooks": list_playbooks()}
