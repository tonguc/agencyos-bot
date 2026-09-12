"""Exercise pipeline queries on a fresh PostgreSQL AsyncSession."""
from api.routes.leads import pipeline_counts
from database import AsyncSessionFactory
from repositories.lead import LeadRepository


async def test_pipeline_counts_with_fresh_session(db_engine, clean_db):
    async with AsyncSessionFactory() as db:
        await LeadRepository(db).create(name="Pipeline regression", city="Test", status="Yeni", opportunity_score=75)
        await db.commit()
    # A fresh session forces connection provisioning; parallel queries fail here.
    async with AsyncSessionFactory() as db:
        result = await pipeline_counts(db=db)
        assert result.counts["Yeni"] == 1
        assert result.score_tiers == {"sicak": 1, "ilik": 0, "soguk": 0}
