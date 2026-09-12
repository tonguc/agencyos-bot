"""phoneless lead unique index — partial unique on LOWER(name)+city WHERE phone IS NULL

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-23

Tamamlayici: services/lead_service.collect_and_save phoneless dedup
(commit 82b45a3) race condition'a karsi tam korunmus degil. Bu partial
unique index DB-katmaninda duplicate'i imkansiz kilar.

ÖNEMLİ — UPGRADE SAFETY:
  Mevcut DB'de phoneless duplicate varsa (ayni LOWER(name) + city, phone IS NULL),
  bu migration FAIL eder ve transaction rollback olur. PROD DOWN OLMAZ ama
  upgrade tamamlanmaz. Asagidaki diagnostic query ile once temizlik yapin:

    SELECT LOWER(name) AS name_lc, city, COUNT(*) AS dup_count, ARRAY_AGG(id) AS ids
    FROM leads WHERE phone IS NULL
    GROUP BY LOWER(name), city HAVING COUNT(*) > 1;

  Temizlik (en yenisini tut, eski duplicate'leri sil — ORTAK PRATIK):
    WITH dups AS (
      SELECT id, ROW_NUMBER() OVER (
        PARTITION BY LOWER(name), city ORDER BY created_at DESC
      ) AS rn
      FROM leads WHERE phone IS NULL
    )
    DELETE FROM leads WHERE id IN (SELECT id FROM dups WHERE rn > 1);
"""

from typing import Sequence, Union
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Partial unique index: yalniz phone IS NULL kayitlar icin (LOWER(name), city)
    # benzersizligi zorunlu kilar. Telefonlu lead'ler bu kisitlamadan etkilenmez.
    op.execute(
        "CREATE UNIQUE INDEX leads_phoneless_name_city_uniq "
        "ON leads (LOWER(name), city) WHERE phone IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS leads_phoneless_name_city_uniq")
