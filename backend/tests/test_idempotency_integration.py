"""Integration test: route-level + task-level idempotency guard.

DB gerektirir — db_engine fixture (conftest) Postgres yoksa skip eder.
Test kapsamı:
  - JobRepository.find_active_for_lead (733a7be route-level guard)
  - AuditRepository.get_latest_for_lead with since_dt (0f23611 task-level)
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta

from database import AsyncSessionFactory
from repositories.job import JobRepository
from repositories.lead import LeadRepository
from repositories.audit import AuditRepository


async def test_find_active_returns_pending_job(db_engine, clean_db):
    async with AsyncSessionFactory() as db:
        lead = await LeadRepository(db).create(
            name="Test Klinik 1", sector="klinik", city="İstanbul",
        )
        job = await JobRepository(db).create(
            type="generate_audit",
            payload={"lead_id": str(lead.id)},
        )
        await db.commit()

        found = await JobRepository(db).find_active_for_lead(lead.id, "generate_audit")
        assert found is not None
        assert found.id == job.id


async def test_find_active_returns_running_job(db_engine, clean_db):
    async with AsyncSessionFactory() as db:
        lead = await LeadRepository(db).create(
            name="Test Klinik 2", sector="klinik", city="İstanbul",
        )
        job = await JobRepository(db).create(
            type="generate_audit",
            payload={"lead_id": str(lead.id)},
        )
        await JobRepository(db).mark_running(job, "running...")
        await db.commit()

        found = await JobRepository(db).find_active_for_lead(lead.id, "generate_audit")
        assert found is not None
        assert found.status == "running"


async def test_find_active_excludes_completed_jobs(db_engine, clean_db):
    async with AsyncSessionFactory() as db:
        lead = await LeadRepository(db).create(
            name="Test Klinik 3", sector="klinik", city="İstanbul",
        )
        job = await JobRepository(db).create(
            type="generate_audit",
            payload={"lead_id": str(lead.id)},
        )
        await JobRepository(db).mark_completed(job, {"audit_id": "xyz"})
        await db.commit()

        found = await JobRepository(db).find_active_for_lead(lead.id, "generate_audit")
        assert found is None   # completed -> idempotent skip etmez, yeni job olusturabiliriz


async def test_find_active_excludes_failed_jobs(db_engine, clean_db):
    async with AsyncSessionFactory() as db:
        lead = await LeadRepository(db).create(
            name="Test Klinik 4", sector="klinik", city="İstanbul",
        )
        job = await JobRepository(db).create(
            type="generate_audit",
            payload={"lead_id": str(lead.id)},
        )
        await JobRepository(db).mark_failed(job, "Claude timeout")
        await db.commit()

        found = await JobRepository(db).find_active_for_lead(lead.id, "generate_audit")
        assert found is None


async def test_find_active_isolates_by_type(db_engine, clean_db):
    async with AsyncSessionFactory() as db:
        lead = await LeadRepository(db).create(
            name="Test Klinik 5", sector="klinik", city="İstanbul",
        )
        # Audit job pending, outreach sorgusu audit'i dondurmemeli
        await JobRepository(db).create(
            type="generate_audit",
            payload={"lead_id": str(lead.id)},
        )
        await db.commit()

        outreach_active = await JobRepository(db).find_active_for_lead(
            lead.id, "generate_outreach"
        )
        assert outreach_active is None

        audit_active = await JobRepository(db).find_active_for_lead(
            lead.id, "generate_audit"
        )
        assert audit_active is not None


async def test_find_active_isolates_by_lead(db_engine, clean_db):
    async with AsyncSessionFactory() as db:
        lead1 = await LeadRepository(db).create(
            name="A", sector="klinik", city="İstanbul",
        )
        lead2 = await LeadRepository(db).create(
            name="B", sector="klinik", city="İstanbul",
        )
        await JobRepository(db).create(
            type="generate_audit",
            payload={"lead_id": str(lead1.id)},
        )
        await db.commit()

        lead2_active = await JobRepository(db).find_active_for_lead(
            lead2.id, "generate_audit"
        )
        assert lead2_active is None


async def test_audit_since_dt_returns_only_newer(db_engine, clean_db):
    """Task-level idempotency: run_audit retry sirasinda since_dt=job.created_at
    gecerek zaten yazilmis audit'i bulur, Claude cagrisi yapmaz."""
    async with AsyncSessionFactory() as db:
        lead = await LeadRepository(db).create(
            name="Test Klinik 6", sector="klinik", city="İstanbul",
        )
        await db.commit()

        # Eski audit (1 saat once)
        old_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        # Yeni audit (simdi)
        new_audit = await AuditRepository(db).create(
            lead_id=lead.id,
            general_score=70,
            result={"ilk_izlenim": {"ne_yapiyor": "test"}},
        )
        await db.commit()

        # since_dt: old_cutoff -> yeni audit bulunur
        found = await AuditRepository(db).get_latest_for_lead(
            lead.id, since_dt=old_cutoff,
        )
        assert found is not None
        assert found.id == new_audit.id

        # since_dt: simdiden daha yeni -> bulunmaz
        future = datetime.now(timezone.utc) + timedelta(minutes=5)
        not_found = await AuditRepository(db).get_latest_for_lead(
            lead.id, since_dt=future,
        )
        assert not_found is None
