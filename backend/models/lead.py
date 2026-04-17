import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.mixins import TimestampMixin, UUIDPrimaryKey

if TYPE_CHECKING:
    from models.audit import Audit
    from models.outreach import OutreachMessage
    from models.proposal import Proposal
    from models.activity_log import ActivityLog


class Lead(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "leads"

    # Future multi-tenant — nullable for MVP single-user
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    district: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(Text)

    # Contact
    phone: Mapped[str | None] = mapped_column(String(50))
    website: Mapped[str | None] = mapped_column(String(500))

    # Source
    source: Mapped[str] = mapped_column(String(50), default="google_maps", nullable=False)
    source_data: Mapped[dict | None] = mapped_column(JSONB)

    # Scoring
    opportunity_score: Mapped[int | None] = mapped_column(Integer)
    priority: Mapped[str | None] = mapped_column(String(20))   # yuksek | orta | dusuk
    google_rating: Mapped[float | None] = mapped_column(Float)
    review_count: Mapped[int | None] = mapped_column(Integer)

    # Pipeline
    status: Mapped[str] = mapped_column(
        String(50),
        default="Yeni",
        nullable=False,
        index=True,
    )

    # Relationships
    audits: Mapped[list["Audit"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    outreach_messages: Mapped[list["OutreachMessage"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    proposals: Mapped[list["Proposal"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    activity_logs: Mapped[list["ActivityLog"]] = relationship(back_populates="lead", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Lead id={str(self.id)[:8]} name={self.name!r} status={self.status}>"
