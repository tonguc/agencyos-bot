"""Pytest shared fixtures.

Unit test'ler DB gerektirmez — cogunlukla pure fonksiyonlar.
Integration test'ler db_engine fixture'ini kullanir; Postgres yoksa
otomatik skip.
"""

import os

# Test sirasinda prod'a kari 'changeme' check'i bypass edilmeli
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("AGENCYOS_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("CLAUDE_API_KEY", "")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("APIFY_API_TOKEN", "")


# ── Integration test fixtures ─────────────────────────────────────────
import pytest
import pytest_asyncio


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Postgres test DB'ye baglan; baglanamazsa tum integration testleri skip et.

    CI'da postgres service + alembic upgrade head zaten calistirilmis olmali
    (bkz .github/workflows/ci.yml). Lokalde integration test calistirmak
    icin: docker run + DATABASE_URL + alembic upgrade head manuel yapilmali.
    """
    from sqlalchemy import text
    from database import engine

    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        pytest.skip(f"DB unavailable (integration tests skipped): {e}")
        return  # unreachable — pytest.skip raises
    yield engine


@pytest_asyncio.fixture(autouse=False)
async def clean_db(db_engine):
    """Test sonrasi tablolari truncate eder — test'ler arasi izolasyon.

    Sadece integration test'lerde autouse=False; test'ler bu fixture'i
    explicit olarak request etmeli. Tablolar sirasi FK'lara gore.
    """
    from sqlalchemy import text
    yield
    async with db_engine.begin() as conn:
        # CASCADE = cocuk tablolari da temizle
        await conn.execute(text(
            "TRUNCATE leads, audits, outreach_messages, proposals, "
            "jobs, activity_log, api_usage_log RESTART IDENTITY CASCADE"
        ))
