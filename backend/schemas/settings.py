from __future__ import annotations

from pydantic import BaseModel


class SettingsOut(BaseModel):
    app_env: str
    claude_model: str
    pagespeed_configured: bool
    apify_configured: bool
    playbooks: list[str]


class TestResult(BaseModel):
    ok: bool
    message: str
