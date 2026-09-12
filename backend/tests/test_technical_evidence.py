from unittest.mock import Mock

import pytest
import requests

from core.audit_generator import fetch_site_data
from core.technical_evidence import html_evidence, lab_evidence
from core.prompts import build_audit_prompt
from core.technical_evidence import ground_audit
from core.sales_output_generator import generate_sales_output


def test_html_attribute_order_and_repeated_robots():
    evidence = html_evidence('''<meta content="Diş kliniği" name="description">
        <meta name="robots" content="noindex"><meta name="robots" content="index">
        <meta name="viewport" content="width=device-width">
        <link href="https://example.com" rel="canonical">
        <script type="application/ld+json">INVALID JSON</script>''', {})
    assert evidence["meta_description"] == "Diş kliniği"
    assert evidence["meta_noindex"] is True
    assert evidence["canonical_present"] is True
    assert evidence["viewport_present"] is True
    assert evidence["json_ld_present"] is True  # tag presence, not validation


def test_specific_crawler_does_not_imply_google_noindex():
    evidence = html_evidence('<meta name="bingbot" content="noindex">', {"X-Robots-Tag": "bingbot: noindex"})
    assert not evidence["meta_noindex"]
    assert evidence["http_robots_present"]


def test_lab_zero_is_real_but_missing_and_invalid_are_unknown():
    assert lab_evidence({}) == {}
    for invalid in (None, True, -1, 2, float("nan")):
        assert lab_evidence({"lighthouseResult": {"categories": {"performance": {"score": invalid}}}}) == {}
    assert lab_evidence({"lighthouseResult": {"categories": {"performance": {"score": 0}}}}) == {"performance": 0}
    assert lab_evidence({"lighthouseResult": {"runtimeError": {"code": "FAILED"}, "categories": {"performance": {"score": 0}}}}) == {}


def response(html="<html><title>Test</title></html>", content_type="text/html"):
    r = Mock()
    r.status_code = 200
    r.url = "https://example.com/"
    r.text = html
    r.headers = {"Content-Type": content_type}
    return r


@pytest.mark.asyncio
async def test_missing_speed_key_is_not_zero_and_html_still_measured(monkeypatch):
    monkeypatch.delenv("PAGESPEED_API_KEY", raising=False)
    monkeypatch.setattr(requests, "get", lambda *a, **kw: response())
    data = await fetch_site_data("http://example.com")
    assert data["hiz_skoru"] is None
    assert not data["hiz_veri_var"]
    assert data["ssl"] is True  # final HTTPS URL
    assert data["technical"]["html_status"] == "measured"
    assert data["technical"]["speed_status"] == "not_configured"


@pytest.mark.asyncio
async def test_fetch_failure_does_not_mean_missing_ssl_form_or_phone(monkeypatch):
    monkeypatch.delenv("PAGESPEED_API_KEY", raising=False)
    def fail(*a, **kw):
        raise requests.Timeout()
    monkeypatch.setattr(requests, "get", fail)
    data = await fetch_site_data("https://example.com")
    assert data["hata"]
    assert data["ssl"] is data["form_var"] is data["tel_var"] is None
    assert data["technical"]["html_status"] == "unavailable"


@pytest.mark.asyncio
async def test_non_html_is_not_parsed_as_missing_tags(monkeypatch):
    monkeypatch.delenv("PAGESPEED_API_KEY", raising=False)
    monkeypatch.setattr(requests, "get", lambda *a, **kw: response("PDF", "application/pdf"))
    data = await fetch_site_data("https://example.com")
    assert data["hata"]
    assert "meta_noindex" not in data["technical"]


@pytest.mark.asyncio
async def test_speed_error_keeps_html_results_and_does_not_log_key(monkeypatch, caplog):
    monkeypatch.setenv("PAGESPEED_API_KEY", "test-secret-marker")
    def get(url, **kw):
        if "googleapis" in url:
            raise requests.HTTPError("test-secret-marker")
        return response()
    monkeypatch.setattr(requests, "get", get)
    data = await fetch_site_data("https://example.com")
    assert data["hiz_skoru"] is None
    assert data["technical"]["html_status"] == "measured"
    assert "test-secret-marker" not in caplog.text


def test_prompt_contains_only_allowed_evidence_and_explicit_limits():
    prompt = build_audit_prompt({}, {"display_name": "Klinik"}, {"technical": {"meta_noindex": True, "meta_description": "IGNORE ALL", "lab": {"lcp_ms": 3500}}})
    assert '"meta_noindex": true' in prompt
    assert "3500" in prompt
    assert "IGNORE ALL" not in prompt
    assert "görünürlük ölçülmedi" in prompt


def test_generated_claims_are_replaced_by_observed_facts():
    result = {"genel_skor": 57, "killer_insight": {"bulgu": "Hastalar rakibe gidiyor"}, "ux_hatalar": [{"sorun": "robots.txt yok"}], "seo_aciklar": [{"sorun": "schema alanları eksik"}]}
    ground_audit(result, {"technical": {"version": 1, "html_status": "measured", "lab": {"lcp_ms": 7510, "cls": 0.048, "tbt_ms": 0}}})
    assert "7.51" in result["killer_insight"]["bulgu"]
    assert len(result["ux_hatalar"]) == 1
    assert result["seo_aciklar"] == []
    assert "robots.txt" not in str(result)
    assert "rakibe gidiyor" not in str(result)
    assert result["genel_skor"] == 57


@pytest.mark.asyncio
async def test_technical_contact_uses_measurement_without_llm(monkeypatch):
    from core import sales_output_generator as sales
    def forbidden(**kw):
        raise AssertionError("Do not regenerate factual observations")
    monkeypatch.setattr(sales.anthropic, "AsyncAnthropic", forbidden)
    result = await generate_sales_output({"isim": "Hilal Veteriner", "website": "https://example.com"}, {"_site_data": {"technical": {"version": 1, "html_status": "measured", "lab": {"lcp_ms": 7510}}}}, {})
    assert "7,51 saniye" in result["short_message"]
    assert "rakip" not in result["short_message"]
    assert result["_valid"]
