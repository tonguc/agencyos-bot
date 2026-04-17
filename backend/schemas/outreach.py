from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class OutreachOut(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    v1: str | None
    v2: str | None
    v3: str | None
    v4: str | None
    recommended: str | None
    sent_version: str | None
    sent_at: datetime | None
    sent_channel: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MarkSentRequest(BaseModel):
    version: str
    channel: str = "whatsapp"
