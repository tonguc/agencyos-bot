from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditOut(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    general_score: int | None
    ux_score: int | None
    seo_score: int | None
    conversion_score: int | None
    urgency: str | None
    lead_quality: str | None
    killer_insight: str | None
    killer_metric: str | None
    personal_insight: str | None
    hook_type: str | None
    hook_text: str | None
    site_speed: int | None
    site_title: str | None
    has_form: bool | None
    has_tel: bool | None
    has_ssl: bool | None
    result: Any
    created_at: datetime

    model_config = {"from_attributes": True}
