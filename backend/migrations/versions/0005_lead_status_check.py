"""leads.status CHECK constraint — pipeline statulerine kisitla

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-23

Tamamlayici: schemas/lead.py LeadUpdate.status simdi Literal[...] (commit
075642b) — REST PATCH gecersiz status'u 422'ile reddediyor. Ama service
katmani LeadRepository.update direkt setattr yapiyor; servisler buna
guvenmiyor. DB-level CHECK constraint defansif son kale.

ÖNEMLİ — UPGRADE SAFETY:
  Mevcut DB'de invalid status (typo, eski "Soguk" — migration 0003 ile
  rename edildi ama yine de) varsa, bu migration FAIL eder. Diagnostic:

    SELECT DISTINCT status, COUNT(*) AS cnt FROM leads
    WHERE status NOT IN ('Yeni','Audit','Mesaj','Cevap','Demo','Teklif','Kapandi','Arsiv')
    GROUP BY status;

  Temizlik (manuel — hangi status'a mapleneceginize karar verin):
    UPDATE leads SET status = 'Yeni' WHERE status = '<gecersiz>';
"""

from typing import Sequence, Union
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


VALID_STATUSES = (
    "Yeni", "Audit", "Mesaj", "Cevap", "Demo", "Teklif", "Kapandi", "Arsiv",
)


def upgrade() -> None:
    statuses_sql = ", ".join(f"'{s}'" for s in VALID_STATUSES)
    op.execute(
        f"ALTER TABLE leads ADD CONSTRAINT chk_lead_status "
        f"CHECK (status IN ({statuses_sql}))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE leads DROP CONSTRAINT IF EXISTS chk_lead_status")
