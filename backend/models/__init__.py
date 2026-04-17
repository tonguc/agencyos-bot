# Import all models so Base.metadata is fully populated for Alembic autogenerate
from models.lead import Lead
from models.audit import Audit
from models.outreach import OutreachMessage
from models.proposal import Proposal
from models.job import Job
from models.activity_log import ActivityLog, ActivityEvent

__all__ = [
    "Lead",
    "Audit",
    "OutreachMessage",
    "Proposal",
    "Job",
    "ActivityLog",
    "ActivityEvent",
]
