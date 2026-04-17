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


# Canonical event names — extend as needed
class ActivityEvent:
    LEAD_CREATED = "lead_created"
    LEAD_STATUS_CHANGED = "lead_status_changed"
    AUDIT_COMPLETED = "audit_completed"
    OUTREACH_GENERATED = "outreach_generated"
    MESSAGE_SENT = "message_sent"
    PROPOSAL_GENERATED = "proposal_generated"
    PROPOSAL_SENT = "proposal_sent"
    FOLLOWUP_GENERATED = "followup_generated"
    JOB_FAILED = "job_failed"


class ActivityLog(UUIDPrimaryKey, Base):
    """Immutable event log — append only, never update."""

    __tablename__ = "activity_logs"

    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    event: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    lead: Mapped["Lead | None"] = relationship(back_populates="activity_logs")

    def __repr__(self) -> str:
        return f"<ActivityLog id={str(self.id)[:8]} event={self.event}>"
