"""Pytest shared fixtures.

Stratejimiz: unit-first. DB gerektiren integration testler ayri (CI'da
Postgres olmadan calistirilmaz). Bu conftest test env'i izole tutar:
  - config kritik env var'lari test icin set eder
  - side effect olmayan pure fonksiyonlar test edilir
"""

import os

# Test sirasinda prod'a kari 'changeme' check'i bypass edilmeli
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("AGENCYOS_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("CLAUDE_API_KEY", "")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("APIFY_API_TOKEN", "")
