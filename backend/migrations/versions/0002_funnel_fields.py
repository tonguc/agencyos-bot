"""funnel fields on outreach_messages

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-18
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("outreach_messages", sa.Column("reply_text", sa.Text, nullable=True))
    op.add_column("outreach_messages", sa.Column("reply_intent", sa.String(20), nullable=True))
    op.add_column("outreach_messages", sa.Column("reply_confidence", sa.Float, nullable=True))
    op.add_column(
        "outreach_messages",
        sa.Column("followup_stage", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("outreach_messages", "followup_stage")
    op.drop_column("outreach_messages", "reply_confidence")
    op.drop_column("outreach_messages", "reply_intent")
    op.drop_column("outreach_messages", "reply_text")
