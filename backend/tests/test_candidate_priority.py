from unittest.mock import AsyncMock

import pytest
from core.icp_filter import filter_leads
from core.lead_collector import enrich_lead
from core.lead_scorer import calculate_final_score
from core.playbook import load_playbook_for_sector
from services import search_service


def candidate(name="Central Klinik", **overrides):
    return {"isim": name, "yorum_sayisi": 800, "puan": 4.9,
            "website": "https://example.com", "telefon": "+902121111111", "site_durumu": "iyi", **overrides}


def test_hospital_high_reviews_and_good_site_remain_candidates():
    lead = candidate("Büyükçekmece Kürtaj Hastanesi | Central Klinik")
    playbook = load_playbook_for_sector("klinik")
    result = filter_leads([lead], playbook)
    assert result["nitelikli"] == [lead]
    assert result["elendi"] == []
    score = calculate_final_score(lead, {}, playbook)
    assert score["status"] == "ok"
    assert score["final_score"] == calculate_final_score(lead, {}, playbook, skip_hard_filter=True)["final_score"]
    assert lead["qualification_notes"]


def test_opening_hours_closure_does_not_mean_permanent():
    assert enrich_lead({"title": "Test", "isClosed": True})["permanently_closed"] is False
    assert enrich_lead({"title": "Test", "permanentlyClosed": True})["permanently_closed"] is True


@pytest.mark.asyncio
async def test_search_keeps_every_candidate_and_orders_closed_last(monkeypatch):
    leads = [candidate("Hastane"), candidate("Kapalı", permanently_closed=True), candidate("Yeni Klinik", website=None, yorum_sayisi=5)]
    monkeypatch.setattr(search_service, "collect_by_query", AsyncMock(return_value=leads))
    monkeypatch.setattr(search_service, "parse_search_query", lambda q: {"sector": "klinik", "search_string": q, "city": "İstanbul", "district": "Büyükçekmece", "sub_sector_hint": None})
    result = await search_service.run_search("Büyükçekmece klinik")
    assert result["summary"]["total"] == 3
    assert result["filter_stats"]["elenen"] == 0
    assert result["results"][-1]["name"] == "Kapalı"
    assert result["results"][-1]["score"] == 0
    assert "doğrula" in result["results"][-1]["reason"]
    assert all(row["reason"] and row["score_breakdown"] for row in result["results"])
    assert result["results"][0]["score"] >= result["results"][1]["score"]
