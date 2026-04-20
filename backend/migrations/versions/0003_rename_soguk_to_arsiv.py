"""rename pipeline status Soguk to Arsiv

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-20
"""

from typing import Sequence, Union
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE leads SET status = 'Arsiv' WHERE status = 'Soguk'")


def downgrade() -> None:
    op.execute("UPDATE leads SET status = 'Soguk' WHERE status = 'Arsiv'")
