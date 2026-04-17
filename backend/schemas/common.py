from __future__ import annotations

from typing import Any
import uuid

from pydantic import BaseModel


class JobResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    result: Any = None
