from unittest.mock import Mock

import pytest
import requests

from config import settings
from core.lead_collector import (
    _filter_by_query_relevance, _filter_by_location, _run_serpapi_maps, enrich_lead,
)
from core.icp_filter import filter_leads
from core.playbook import load_playbook_for_sector


def test_doctor_names_and_specialties_survive_without_literal_doktor():
    rows = [
        {"isim": "Op. Dr. Osman Nuri Akbulut", "kategori": "Urologist"},
        {"isim": "Ayşe Örnek", "kategori": "General practitioner"},
        {"isim": "Özel Sağlık", "kategori": "Physician"},
        {"isim": "Mehmet Örnek", "kategori": "Cardiologist"},
    ]
    assert _filter_by_query_relevance(rows, "doktor") == rows
    assert _filter_by_query_relevance([{"isim": "Mobilya", "kategori": "Furniture store"}], "doktor") == []
    assert _filter_by_query_relevance(rows, "dermatolog") == []


def test_unverified_location_and_physician_notes_survive_icp():
    row = enrich_lead({"title": "Op. Dr. Osman Nuri Akbulut", "address": "Atatürk Caddesi", "reviewsCount": 10000})
    assert _filter_by_location([row], "Beylikdüzü") == [row]
    filter_leads([row], load_playbook_for_sector("klinik"))
    assert any("Konum doğrulanmalı" in n for n in row["qualification_notes"])
    assert any("satın alma yetkisi" in n for n in row["qualification_notes"])
    assert any("Hedef profil" in n for n in row["qualification_notes"])
    matching = {"adres": "Beylikdüzü İstanbul"}
    assert _filter_by_location([matching], "Beylikdüzü") == [matching]
    assert not matching.get("qualification_notes")


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{"error": "secret-provider-detail"}, [], {"local_results": "invalid"}])
async def test_provider_error_is_not_zero_results(monkeypatch, payload):
    monkeypatch.setattr(settings, "SERPAPI_API_KEY", "test-key")
    response = Mock()
    response.json.return_value = payload
    monkeypatch.setattr("core.lead_collector.requests.get", Mock(return_value=response))
    with pytest.raises(RuntimeError) as exc:
        await _run_serpapi_maps("doktor", "İstanbul", "Beylikdüzü", 20, "klinik")
    assert "secret-provider-detail" not in str(exc.value)


@pytest.mark.asyncio
async def test_http_error_sanitized_and_real_empty_preserved(monkeypatch):
    monkeypatch.setattr(settings, "SERPAPI_API_KEY", "test-key")
    monkeypatch.setattr("core.lead_collector.requests.get", Mock(side_effect=requests.HTTPError("api_key=test-key")))
    with pytest.raises(RuntimeError) as exc:
        await _run_serpapi_maps("doktor", "İstanbul", "Beylikdüzü", 20, "klinik")
    assert "test-key" not in str(exc.value)
    response = Mock()
    response.json.return_value = {"local_results": []}
    monkeypatch.setattr("core.lead_collector.requests.get", Mock(return_value=response))
    assert await _run_serpapi_maps("doktor", "İstanbul", "Beylikdüzü", 20, "klinik") == []


@pytest.mark.asyncio
async def test_missing_provider_key_is_explicit(monkeypatch):
    monkeypatch.setattr(settings, "SERPAPI_API_KEY", "")
    with pytest.raises(RuntimeError, match="yapılandırılmamış"):
        await _run_serpapi_maps("doktor", "İstanbul", "Beylikdüzü", 20, "klinik")


@pytest.mark.asyncio
async def test_single_place_response_is_not_lost(monkeypatch):
    monkeypatch.setattr(settings, "SERPAPI_API_KEY", "test-key")
    response = Mock()
    response.json.return_value = {"place_results": {"title": "Dr. Örnek", "type": ["Doctor", "Physician"], "address": "Beylikdüzü"}}
    request = Mock(return_value=response)
    monkeypatch.setattr("core.lead_collector.requests.get", request)
    rows = await _run_serpapi_maps("doktor", "İstanbul", "Beylikdüzü", 20, "klinik")
    assert len(rows) == 1 and rows[0]["kategori"] == "Doctor, Physician"
    assert request.call_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("second_results", [[], [{"title": "Dr. Örnek", "type": "Doctor", "address": "Beylikdüzü"}]])
async def test_empty_doctor_search_has_one_transparent_same_location_fallback(monkeypatch, second_results):
    monkeypatch.setattr(settings, "SERPAPI_API_KEY", "test-key")
    first, second = Mock(), Mock()
    first.json.return_value = {"local_results": []}
    second.json.return_value = {"local_results": second_results}
    request = Mock(side_effect=[first, second])
    monkeypatch.setattr("core.lead_collector.requests.get", request)
    rows = await _run_serpapi_maps("doktor", "İstanbul", "Beylikdüzü", 20, "klinik")
    assert request.call_count == 2
    assert request.call_args.kwargs["params"]["q"] == "hekim Beylikdüzü İstanbul"
    assert len(rows) == len(second_results)
    if rows:
        assert any("hekim sorgusuyla" in n for n in rows[0]["qualification_notes"])
