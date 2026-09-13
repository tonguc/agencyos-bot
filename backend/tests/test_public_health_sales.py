from unittest.mock import AsyncMock

import pytest

from core.sales_eligibility import public_health_sales_note
from core.lead_scorer import calculate_final_score
from core.playbook import load_playbook_for_sector
from services.search_service import _normalize_lead
from api.routes import search


@pytest.mark.parametrize("address", ["Mimar Sinan, Devlet Hastanesi, Büyükçekmece", "Samsun Eğitim ve Araştırma Hastanesi", "Samsun Eğitim Araştırma Hastanesi", "Ankara Şehir Hastanesi"])
def test_public_record_stays_visible_but_never_gets_sales_floor(address):
    lead = {"isim": "Op. Dr. Örnek", "adres": address, "telefon": "123", "website": None, "yorum_sayisi": 5}
    for skip in (False, True):
        score = calculate_final_score(lead, {}, load_playbook_for_sector("klinik"), skip_hard_filter=skip)
        assert score["status"] == "ok"
        assert score["final_score"] == 0 and score["action"] == "outside_active_sales"
        row = _normalize_lead(lead, score)
        assert row["outside_active_sales"] and row["segment"] == "low"
        assert "görev statüsü doğrulaması değildir" in row["reason"]


@pytest.mark.parametrize("address", ["Özel Kolan Hastanesi", "Acıbadem Hastanesi", "Devlet Hastanesi Caddesi No:3", "Devlet Hastanesi karşısı", "Özel Muayenehane", "Üniversite Caddesi"])
def test_private_and_landmark_records_are_not_public_employment(address):
    assert public_health_sales_note({"isim": "Dr. Örnek", "adres": address}) is None


def test_nonmedical_business_is_not_classified_from_hospital_address():
    assert public_health_sales_note({"isim": "Çiçekçi", "kategori": "Florist", "adres": "Devlet Hastanesi"}) is None


@pytest.mark.asyncio
async def test_stored_high_score_cannot_reactivate_public_record(monkeypatch):
    row = _normalize_lead({"isim": "Dr. Örnek", "adres": "Devlet Hastanesi", "telefon": "123"}, None)
    repo = AsyncMock()
    repo.find_scores_by_phones.return_value = {"123": {"id": "existing", "opportunity_score": 90, "priority": "yuksek"}}
    monkeypatch.setattr(search, "LeadRepository", lambda db: repo)
    await search._enrich_lead_ids([row], None)
    assert row["lead_id"] == "existing"
    assert row["score"] == 0 and row["segment"] == "low" and row["priority"] == "dusuk"
