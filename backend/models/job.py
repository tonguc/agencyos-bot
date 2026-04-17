from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.mixins import UUIDPrimaryKey


class Job(UUIDPrimaryKey, Base):
    """Background task tracking — UI polls this for live status."""

    __tablename__ = "jobs"

    # Task type
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # collect_leads | generate_audit | generate_outreach | generate_proposal

    # Status lifecycle: pending → running → completed | failed
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
    )

    # Progress (for UI progress bar)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress_message: Mapped[str | None] = mapped_column(Text)

    # Error details on failure
    error_message: Mapped[str | None] = mapped_column(Text)

    # Input / output
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONB)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Job id={str(self.id)[:8]} type={self.type} status={self.status} {self.progress_pct}%>"
