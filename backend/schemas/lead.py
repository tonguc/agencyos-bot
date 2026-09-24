from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, field_validator


# Pipeline statuses — repositories/lead.py:PIPELINE_STATUSES ile sync
LeadStatus = Literal[
    "Yeni", "Audit", "Mesaj", "Cevap", "Demo", "Teklif", "Kapandi", "Arsiv"
]
LeadPriority = Literal["yuksek", "orta", "dusuk"]


class LeadCreate(BaseModel):
    name: str
    sector: str
    city: str
    district: str = ""
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    google_rating: float | None = None
    review_count: int | None = None
    # Arama/collect'ten gelen zengin sinyaller (site_durumu, review velocity,
    # SERP alanları ...). Audit sırasında lead_to_core_dict bunu merge eder.
    source_data: dict[str, Any] | None = None


class LeadUpdate(BaseModel):
    # Sadece geçerli pipeline statüleri kabul edilir; "Mesaj Gönderiliyor"
    # gibi typo'lar 422 döner. (DB'deki mevcut serbest-form kayıtlar etkilenmez —
    # sadece API yazma yolunu kısıtlıyoruz; backend service'leri bypass eder.)
    status: LeadStatus | None = None
    priority: LeadPriority | None = None
    name: str | None = None
    phone: str | None = None
    website: str | None = None
    address: str | None = None
    notes: str | None = None


class LeadOut(BaseModel):
    id: uuid.UUID
    name: str
    sector: str
    city: str
    district: str | None
    address: str | None
    phone: str | None
    website: str | None
    google_rating: float | None
    review_count: int | None
    status: str
    priority: str | None
    opportunity_score: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadListOut(BaseModel):
    items: list[LeadOut]
    total: int
    limit: int
    offset: int


class PipelineOut(BaseModel):
    counts: dict[str, int]
    score_tiers: dict[str, int]


class ScrapeRequest(BaseModel):
    sector: str
    city: str
    district: str = ""
    limit: int = 20

    @field_validator("limit")
    @classmethod
    def cap_limit(cls, v: int) -> int:
        return min(v, 100)
