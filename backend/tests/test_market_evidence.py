import httpx
import pytest

from core import market_evidence as market


def test_brand_and_service_are_separate_without_misclassifying_generic_clinic():
    plan = market.query_plan({"isim": "Hilal Veteriner Kliniği", "city": "İstanbul", "district": "Şişli", "sektor": "klinik"})
    assert [q["kind"] for q in plan] == ["brand", "service"]
    assert plan[1]["query"] == "Şişli İstanbul veteriner"
    assert len(market.query_plan({"isim": "ABC Klinik", "sektor": "klinik", "city": "İstanbul"})) == 1


def test_rank_and_ai_reference_match_exact_host_not_substring():
    payload = {"organic_results": [{"position": 1, "link": "https://notexample.com/"}, {"position": 3, "link": "https://www.example.com/page"}],
               "ai_overview": {"references": [{"link": "https://example.com/a"}]},
               "ads": [{"link": "https://example.com.evil.test"}]}
    result = market.parse_observation(payload, "https://example.com")
    assert result["position"] == 3
    assert result["ai_cited"] is True
    assert result["self_ad_observed"] is False


@pytest.mark.parametrize("website", [None, "", "https://facebook.com/business"])
def test_missing_or_shared_domain_does_not_become_not_found(website):
    result = market.parse_observation({"organic_results": [{"position": 1, "link": "https://facebook.com/other"}]}, website)
    assert result["organic_status"] == "unknown_domain"
    assert result["position"] is None
    assert result["self_ad_observed"] is None


def test_ai_unavailable_absent_and_nonmatching_are_distinct():
    assert market.parse_observation({}, "https://example.com")["ai_status"] == "not_returned"
    assert market.parse_observation({"ai_overview": {"page_token": "x"}}, "https://example.com")["ai_status"] == "unavailable"
    assert market.parse_observation({"ai_overview": {"text_blocks": [{"snippet": "text"}]}}, "https://example.com")["ai_status"] == "no_references"
    result = market.parse_observation({"ai_overview": {"references": [{"link": "https://other.test"}]}}, "https://example.com")
    assert result["ai_status"] == "measured" and result["ai_cited"] is False


def test_no_organic_results_is_not_rank_zero_and_scope_is_first_ten():
    result = market.parse_observation({"organic_results": [{"position": 11, "link": "https://example.com"}]}, "https://example.com")
    assert result["position"] is None
    assert result["organic_status"] == "unavailable"


@pytest.mark.asyncio
async def test_no_key_skips_requests(monkeypatch):
    monkeypatch.setattr(market.settings, "SERPAPI_API_KEY", "")
    result = await market.collect_market({"isim": "Test"})
    assert result["status"] == "not_configured"


@pytest.mark.asyncio
async def test_token_followup_and_errors_keep_successful_query(monkeypatch):
    monkeypatch.setattr(market.settings, "SERPAPI_API_KEY", "secret-marker")
    calls = []
    def handle(request):
        calls.append(dict(request.url.params))
        if request.url.params["engine"] == "google_ai_overview":
            return httpx.Response(200, json={"ai_overview": {"references": [{"link": "https://example.com"}]}})
        if len(calls) > 2:
            return httpx.Response(429, json={"error": "secret-marker"})
        return httpx.Response(200, json={"search_metadata": {"status": "Success", "id": "test-id"}, "organic_results": [{"position": 2, "link": "https://example.com"}], "ai_overview": {"page_token": "token"}})
    original = httpx.AsyncClient
    monkeypatch.setattr(market.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    result = await market.collect_market({"isim": "Test Veteriner", "city": "İstanbul", "website": "https://example.com"})
    assert len(calls) == 3
    assert calls[1]["engine"] == "google_ai_overview"
    assert result["queries"][0]["ai_cited"] is True
    assert result["queries"][1]["status"] == "unavailable"
    assert result["queries"][1]["error_code"] == "http_429"
    assert result["status"] == "partial"
    assert "secret-marker" not in str(result) and "page_token" not in str(result)


@pytest.mark.asyncio
async def test_provider_location_error_is_safe_and_actionable(monkeypatch):
    monkeypatch.setattr(market.settings, "SERPAPI_API_KEY", "secret-marker")
    original = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"error": "Invalid location https://example.test?api_key=secret-marker"}))
    monkeypatch.setattr(market.httpx, "AsyncClient", lambda **kw: original(transport=transport, **kw))
    result = await market.collect_market({"isim": "Test"})
    assert result["queries"][0]["error_code"] == "location"
    assert "secret-marker" not in str(result)


def test_payment_has_no_fake_probability_and_reviews_do_not_prove_budget():
    low = market.commercial_evidence({"review_count": 500}, {"queries": []}, {})
    assert low["payment_probability"] is None and low["priority"] == "insufficient"
    high = market.commercial_evidence({}, {"queries": [{"self_ad_observed": True}]}, {"_site_data": {"technical": {"lab": {"lcp_ms": 6000}}}})
    assert high["priority"] == "investment_and_need"
    assert high["payment_probability"] is None and high["budget"] == "unknown"
