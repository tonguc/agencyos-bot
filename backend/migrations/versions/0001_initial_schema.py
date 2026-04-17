"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-17
"""

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sector", sa.String(100)),
        sa.Column("city", sa.String(100)),
        sa.Column("district", sa.String(100)),
        sa.Column("address", sa.Text),
        sa.Column("phone", sa.String(50)),
        sa.Column("website", sa.String(500)),
        sa.Column("source", sa.String(50), nullable=False, server_default="google_maps"),
        sa.Column("source_data", postgresql.JSONB),
        sa.Column("opportunity_score", sa.Integer),
        sa.Column("priority", sa.String(20)),
        sa.Column("google_rating", sa.Float),
        sa.Column("review_count", sa.Integer),
        sa.Column("status", sa.String(50), nullable=False, server_default="Yeni"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_leads_status", "leads", ["status"])
    op.create_index("ix_leads_user_id", "leads", ["user_id"])

    op.create_table(
        "audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("site_speed", sa.Integer),
        sa.Column("site_title", sa.Text),
        sa.Column("site_meta", sa.Text),
        sa.Column("site_h1", sa.Text),
        sa.Column("has_form", sa.Boolean),
        sa.Column("has_tel", sa.Boolean),
        sa.Column("has_ssl", sa.Boolean),
        sa.Column("result", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("general_score", sa.Integer),
        sa.Column("ux_score", sa.Integer),
        sa.Column("seo_score", sa.Integer),
        sa.Column("conversion_score", sa.Integer),
        sa.Column("urgency", sa.String(20)),
        sa.Column("lead_quality", sa.String(20)),
        sa.Column("killer_insight", sa.Text),
        sa.Column("killer_metric", sa.String(100)),
        sa.Column("personal_insight", sa.Text),
        sa.Column("hook_type", sa.String(50)),
        sa.Column("hook_text", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audits_lead_id", "audits", ["lead_id"])

    op.create_table(
        "outreach_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("audit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audits.id", ondelete="SET NULL"), nullable=True),
        sa.Column("v1", sa.Text),
        sa.Column("v2", sa.Text),
        sa.Column("v3", sa.Text),
        sa.Column("v4", sa.Text),
        sa.Column("recommended", sa.String(10)),
        sa.Column("sent_version", sa.String(10)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("sent_channel", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_outreach_lead_id", "outreach_messages", ["lead_id"])

    op.create_table(
        "proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("audit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audits.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("pdf_path", sa.String(500)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_proposals_lead_id", "proposals", ["lead_id"])

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("progress_pct", sa.Integer, nullable=False, server_default="0"),
        sa.Column("progress_message", sa.Text),
        sa.Column("error_message", sa.Text),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("result", postgresql.JSONB),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_jobs_type", "jobs", ["type"])
    op.create_index("ix_jobs_status", "jobs", ["status"])

    op.create_table(
        "activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event", sa.String(100), nullable=False),
        sa.Column("data", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_activity_lead_id", "activity_logs", ["lead_id"])
    op.create_index("ix_activity_event", "activity_logs", ["event"])
    op.create_index("ix_activity_created_at", "activity_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("activity_logs")
    op.drop_table("jobs")
    op.drop_table("proposals")
    op.drop_table("outreach_messages")
    op.drop_table("audits")
    op.drop_table("leads")
