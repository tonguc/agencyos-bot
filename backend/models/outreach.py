import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.mixins import UUIDPrimaryKey

if TYPE_CHECKING:
    from models.lead import Lead
    from models.audit import Audit


class OutreachMessage(UUIDPrimaryKey, Base):
    __tablename__ = "outreach_messages"

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

    # Generated versions
    v1: Mapped[str | None] = mapped_column(Text)
    v2: Mapped[str | None] = mapped_column(Text)
    v3: Mapped[str | None] = mapped_column(Text)
    v4: Mapped[str | None] = mapped_column(Text)
    recommended: Mapped[str | None] = mapped_column(String(10))  # v1|v2|v3|v4

    # Send tracking
    sent_version: Mapped[str | None] = mapped_column(String(10))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_channel: Mapped[str | None] = mapped_column(String(50))  # whatsapp | email | manual

    # Reply tracking
    reply_text: Mapped[str | None] = mapped_column(Text)
    reply_intent: Mapped[str | None] = mapped_column(String(20))  # positive|curious|price|not_now|reject
    reply_confidence: Mapped[float | None] = mapped_column(Float)

    # Follow-up stage: 0=none sent, 1=day2, 2=day4, 3=day7
    followup_stage: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    lead: Mapped["Lead"] = relationship(back_populates="outreach_messages")
    audit: Mapped["Audit | None"] = relationship()

    def __repr__(self) -> str:
        return f"<OutreachMessage id={str(self.id)[:8]} lead={str(self.lead_id)[:8]} sent={self.sent_version}>"
