from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class JobOut(BaseModel):
    id: uuid.UUID
    type: str
    status: str
    progress_pct: int
    progress_message: str | None
    error_message: str | None
    payload: Any
    result: Any
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
