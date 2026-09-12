"""Integration test: phone/name dedup + migration 0004/0005 constraint'leri.

DB gerektirir — Postgres yoksa pytest.skip.
"""

import pytest
import uuid

from sqlalchemy.exc import IntegrityError

from database import AsyncSessionFactory
from repositories.lead import LeadRepository


async def test_find_by_phones_returns_existing(db_engine, clean_db):
    async with AsyncSessionFactory() as db:
        repo = LeadRepository(db)
        await repo.create(
            name="A", sector="klinik", city="İstanbul", phone="0216 123 4567",
        )
        await repo.create(
            name="B", sector="klinik", city="İstanbul", phone="0216 987 6543",
        )
        await db.commit()

        found = await repo.find_by_phones(["0216 123 4567", "0216 000 0000"])
        assert "0216 123 4567" in found
        assert "0216 000 0000" not in found


async def test_find_phoneless_dupe_keys_matches_same_city(db_engine, clean_db):
    async with AsyncSessionFactory() as db:
        repo = LeadRepository(db)
        # Telefonsuz lead Istanbul'da
        await repo.create(
            name="Demir Nakliyat", sector="nakliyat", city="İstanbul", phone=None,
        )
        # Telefonsuz lead Ankara'da (ayni isim, farkli sehir)
        await repo.create(
            name="Demir Nakliyat", sector="nakliyat", city="Ankara", phone=None,
        )
        # Telefonlu lead Istanbul'da (ayni isim)
        await repo.create(
            name="Demir Nakliyat", sector="nakliyat", city="İstanbul",
            phone="0216 111 2222",
        )
        await db.commit()

        # Istanbul'da telefonsuz "demir nakliyat" zaten var
        keys = await repo.find_phoneless_dupe_keys(["demir nakliyat"], "İstanbul")
        assert "demir nakliyat" in keys

        # Ankara icin ayri sorgu — telefonsuz demir nakliyat Ankara'da da var
        keys_ankara = await repo.find_phoneless_dupe_keys(["demir nakliyat"], "Ankara")
        assert "demir nakliyat" in keys_ankara

        # Telefonlu olan sayilmamali — yalnizca phone IS NULL
        # (zaten farkli telefon, dedup path'i telefon kullanirdi)

        # Bilinmeyen isim bos set
        empty = await repo.find_phoneless_dupe_keys(["olmayan isim"], "İstanbul")
        assert empty == set()


async def test_find_phoneless_dupe_keys_case_insensitive(db_engine, clean_db):
    async with AsyncSessionFactory() as db:
        repo = LeadRepository(db)
        await repo.create(
            name="DEMIR Nakliyat", sector="nakliyat", city="İstanbul", phone=None,
        )
        await db.commit()

        # Lowercase query ile eslemeli (LOWER() kullaniliyor)
        keys = await repo.find_phoneless_dupe_keys(["demir nakliyat"], "İstanbul")
        assert "demir nakliyat" in keys


async def test_migration_0004_blocks_phoneless_duplicate(db_engine, clean_db):
    """Migration 0004 partial unique index: ayni (LOWER(name), city) icin
    phone IS NULL ikinci insert IntegrityError atmali."""
    async with AsyncSessionFactory() as db:
        repo = LeadRepository(db)
        await repo.create(
            name="Test Firma Unique", sector="klinik", city="İstanbul", phone=None,
        )
        await db.commit()

    # Ikinci insert — ayni sehir, ayni isim (farkli case), phone NULL
    with pytest.raises(IntegrityError):
        async with AsyncSessionFactory() as db:
            repo = LeadRepository(db)
            await repo.create(
                name="TEST FIRMA UNIQUE", sector="klinik", city="İstanbul", phone=None,
            )
            await db.commit()


async def test_migration_0004_allows_phoneless_different_city(db_engine, clean_db):
    """Farkli sehirde ayni isim phoneless OK (index sadece ayni (name, city) icin)."""
    async with AsyncSessionFactory() as db:
        repo = LeadRepository(db)
        await repo.create(
            name="Test Firma Diff City", sector="klinik", city="İstanbul", phone=None,
        )
        await db.commit()

    # Ankara'da ayni isim — OK olmali
    async with AsyncSessionFactory() as db:
        repo = LeadRepository(db)
        await repo.create(
            name="Test Firma Diff City", sector="klinik", city="Ankara", phone=None,
        )
        await db.commit()

    # Her ikisi de DB'de
    async with AsyncSessionFactory() as db:
        repo = LeadRepository(db)
        leads, total = await repo.filter(
            search="Test Firma Diff City", limit=10,
        )
        assert total == 2


async def test_migration_0004_allows_same_name_with_phones(db_engine, clean_db):
    """Ayni isim + sehir ama FARKLI telefonlar OK (index phone IS NULL kosullu)."""
    async with AsyncSessionFactory() as db:
        repo = LeadRepository(db)
        await repo.create(
            name="Same Name Phoned", sector="klinik", city="İstanbul",
            phone="0216 111 1111",
        )
        await repo.create(
            name="Same Name Phoned", sector="klinik", city="İstanbul",
            phone="0216 222 2222",
        )
        await db.commit()


async def test_migration_0005_blocks_invalid_status(db_engine, clean_db):
    """Migration 0005 CHECK constraint: invalid status INSERT/UPDATE fail."""
    async with AsyncSessionFactory() as db:
        repo = LeadRepository(db)
        # Gecerli status OK
        await repo.create(
            name="Status Test A", sector="klinik", city="İstanbul", status="Yeni",
        )
        await db.commit()

    # Invalid status -> IntegrityError (CHECK)
    with pytest.raises(IntegrityError):
        async with AsyncSessionFactory() as db:
            repo = LeadRepository(db)
            await repo.create(
                name="Status Test B", sector="klinik", city="İstanbul",
                status="Mesaj Gönderiliyor",  # typo — CHECK reddeder
            )
            await db.commit()


async def test_migration_0005_all_valid_statuses_accepted(db_engine, clean_db):
    """Pipeline'daki tum gecerli statuler DB tarafindan kabul edilmeli."""
    valid = [
        "Yeni", "Audit", "Mesaj", "Cevap", "Demo", "Teklif", "Kapandi", "Arsiv",
    ]
    async with AsyncSessionFactory() as db:
        repo = LeadRepository(db)
        for i, s in enumerate(valid):
            await repo.create(
                name=f"Valid Status {i}", sector="klinik", city="İstanbul", status=s,
            )
        await db.commit()
