import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.mixins import UUIDPrimaryKey

if TYPE_CHECKING:
    from models.lead import Lead


class Audit(UUIDPrimaryKey, Base):
    __tablename__ = "audits"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Raw site data
    site_speed: Mapped[int | None] = mapped_column(Integer)
    site_title: Mapped[str | None] = mapped_column(Text)
    site_meta: Mapped[str | None] = mapped_column(Text)
    site_h1: Mapped[str | None] = mapped_column(Text)
    has_form: Mapped[bool | None] = mapped_column(Boolean)
    has_tel: Mapped[bool | None] = mapped_column(Boolean)
    has_ssl: Mapped[bool | None] = mapped_column(Boolean)

    # Full Claude output — source of truth
    result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Denormalized fast-access fields (no need to parse JSONB for listings)
    general_score: Mapped[int | None] = mapped_column(Integer)
    ux_score: Mapped[int | None] = mapped_column(Integer)
    seo_score: Mapped[int | None] = mapped_column(Integer)
    conversion_score: Mapped[int | None] = mapped_column(Integer)
    urgency: Mapped[str | None] = mapped_column(String(20))        # dusuk | orta | yuksek
    lead_quality: Mapped[str | None] = mapped_column(String(20))   # soguk | ilik | sicak
    killer_insight: Mapped[str | None] = mapped_column(Text)
    killer_metric: Mapped[str | None] = mapped_column(String(100))
    personal_insight: Mapped[str | None] = mapped_column(Text)

    # Hook
    hook_type: Mapped[str | None] = mapped_column(String(50))
    hook_text: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    lead: Mapped["Lead"] = relationship(back_populates="audits")

    def __repr__(self) -> str:
        return f"<Audit id={str(self.id)[:8]} lead={str(self.lead_id)[:8]} score={self.general_score}>"
