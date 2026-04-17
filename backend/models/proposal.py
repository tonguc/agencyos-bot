import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.mixins import UUIDPrimaryKey

if TYPE_CHECKING:
    from models.lead import Lead
    from models.audit import Audit


class Proposal(UUIDPrimaryKey, Base):
    __tablename__ = "proposals"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    audit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audits.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Claude-generated narrative sections
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # PDF storage — local path for MVP, S3 key for later
    pdf_path: Mapped[str | None] = mapped_column(String(500))

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    lead: Mapped["Lead"] = relationship(back_populates="proposals")
    audit: Mapped["Audit | None"] = relationship()

    def __repr__(self) -> str:
        return f"<Proposal id={str(self.id)[:8]} lead={str(self.lead_id)[:8]}>"
