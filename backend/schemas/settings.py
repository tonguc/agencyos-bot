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


class ServiceUsage(BaseModel):
    ok: bool
    label: str
    detail: str | None = None       # balance / usage string
    dashboard_url: str | None = None


class UsageOut(BaseModel):
    claude: ServiceUsage
    openai: ServiceUsage
    apify: ServiceUsage


class SpendOut(BaseModel):
    """Son 24 saatlik spend, provider bazinda + budget durumu."""
    today: dict[str, float]   # {"claude": 1.20, "apify": 0.50, ...}
    total: float
    budget_usd: float          # 0 ise sınır yok (alarm devre dışı)
    used_pct: float | None     # budget>0 ise total/budget*100; yoksa None
