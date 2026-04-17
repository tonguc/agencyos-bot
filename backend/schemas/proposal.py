from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ProposalOut(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    audit_id: uuid.UUID | None
    pdf_path: str | None
    content: Any
    created_at: datetime

    model_config = {"from_attributes": True}
