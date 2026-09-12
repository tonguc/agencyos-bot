import json
from unittest.mock import AsyncMock

import pytest
from core import audit_generator as generator
from core import sales_output_generator as sales
from core.prompts import build_audit_prompt
from core.hook_engine import select_and_generate_hook, _generate_money_hook


@pytest.mark.asyncio
async def test_missing_url_message_does_not_invent_person_location_or_loss(monkeypatch):
    def forbidden(**kwargs):
        raise AssertionError("Missing URL needs no generated claims")
    monkeypatch.setattr(sales.anthropic, "AsyncAnthropic", forbidden)
    result = await sales.generate_sales_output(
        {"isim": "Diş Hekimi Sibel Söğüt Muayenehanesi, Dizdariye, Hamam Sk. No:3", "sektor": "klinik"},
        {"killer_insight": {"bulgu": "SSL yok; hastalar rakiplere gidiyor"}},
        {"sektor": "clinic_general"},
    )
    for key in ("short_message", "full_message"):
        text = result[key]
        assert "Sibel Söğüt" in text
        assert "clinic_general" not in text
        assert "Merhaba Diş" not in text
        assert "Hamam" not in text
        assert "SSL" not in text
        assert "rakip" not in text
        assert "bir site" in text or "bir web sitesi" in text
    assert result["_valid"]


@pytest.mark.asyncio
async def test_missing_url_overrides_unsupported_generated_findings(monkeypatch):
    monkeypatch.setattr(generator, "fetch_site_data", AsyncMock(return_value={"url": "", "hata": True}))
    monkeypatch.setattr(generator, "build_audit_prompt", lambda *args: "test")
    bad = {"genel_skor": 40, "skorlar": {"ux": 30, "seo": 40, "donusum": 50},
           "killer_insight": {"bulgu": "SSL ve telefon yok; ayda 50 hasta kaybı", "rakam": "50"},
           "ux_hatalar": [{"sorun": "SSL yok"}]}
    monkeypatch.setattr(generator, "claude_api_call", AsyncMock(return_value=json.dumps(bad)))
    result = await generator.generate_audit({}, {})
    assert result["killer_insight"]["rakam"] == ""
    assert result["ux_hatalar"] == result["seo_aciklar"] == []
    assert "bulunamadı" in result["killer_insight"]["bulgu"]
    assert "rakamsiz" not in str(result.get("_validation_warnings", []))
    assert result["genel_skor"] == 40  # scoring unchanged


def test_missing_site_prompt_marks_checks_unknown():
    prompt = build_audit_prompt({}, {"display_name": "Klinik"}, {"url": "", "hata": True})
    assert "Tel link: değerlendirilemedi" in prompt
    assert "SSL: False" not in prompt
    assert "en az 2" not in prompt
    assert "RAKAM ZORUNLULUĞU" not in prompt


@pytest.mark.asyncio
async def test_hooks_do_not_infer_customer_loss_from_review_count():
    hook = await select_and_generate_hook({}, {}, {})
    assert "web sitesi var mı" in hook["hook"]
    for count in (3, 30, 300):
        text = await _generate_money_hook({"yorum_sayisi": count}, {}, {})
        assert "%" not in text
        assert "hasta" not in text
        assert "65" not in text
