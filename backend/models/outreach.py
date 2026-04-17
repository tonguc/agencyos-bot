import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
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
