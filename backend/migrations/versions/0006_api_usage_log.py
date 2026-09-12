"""api_usage_log table — per-call external API spend tracking

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-23
"""

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_usage_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("tokens_in", sa.Integer),
        sa.Column("tokens_out", sa.Integer),
        sa.Column("units", sa.Float),
        sa.Column("cost_usd", sa.Float, nullable=False, server_default="0"),
        sa.Column("meta", postgresql.JSONB),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
    )
    op.create_index("ix_api_usage_log_provider", "api_usage_log", ["provider"])
    op.create_index("ix_api_usage_log_created_at", "api_usage_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_api_usage_log_created_at", table_name="api_usage_log")
    op.drop_index("ix_api_usage_log_provider", table_name="api_usage_log")
    op.drop_table("api_usage_log")
