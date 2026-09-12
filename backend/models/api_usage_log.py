from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.mixins import UUIDPrimaryKey


class ApiUsageLog(UUIDPrimaryKey, Base):
    """Per-call external API usage log — daily spend + budget alarm icin.

    Provider-specific birim:
      claude  → tokens_in / tokens_out
      openai  → units (TTS char count, STT minute*100)
      apify   → units (compute units veya per-place tahmini)
      serpapi → units (search count)
      pagespeed → units (request count)
    """

    __tablename__ = "api_usage_log"

    provider: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    units: Mapped[float | None] = mapped_column(Float)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    meta: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<ApiUsageLog {self.provider} ${self.cost_usd:.4f}>"
