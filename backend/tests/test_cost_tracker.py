"""Pricing saf fonksiyon testleri — fiyat degisince fail etmesi lazim.

core/pricing.py DB/HTTP side effect icermez — unit test icin ideal.
"""

from core.pricing import (
    claude_cost, apify_cost, openai_tts_cost, openai_stt_cost,
    CLAUDE_PRICES,
)


def test_claude_sonnet_pricing():
    cost = claude_cost(1_000_000, 1_000_000, "claude-sonnet-4-6")
    assert cost == 18.0


def test_claude_opus_pricing():
    cost = claude_cost(1_000_000, 1_000_000, "claude-opus-4-7")
    assert cost == 90.0


def test_claude_haiku_pricing():
    cost = claude_cost(1_000_000, 1_000_000, "claude-haiku-4-5-20251001")
    assert cost == 4.8


def test_claude_unknown_model_falls_back_to_sonnet():
    cost = claude_cost(1_000_000, 1_000_000, "unknown-model-xyz")
    assert cost == 18.0


def test_claude_small_call():
    cost = claude_cost(2000, 400, "claude-sonnet-4-6")
    expected = (2000 * 3.0 + 400 * 15.0) / 1_000_000
    assert abs(cost - expected) < 1e-9


def test_claude_prices_table_has_expected_models():
    assert "claude-sonnet-4-6" in CLAUDE_PRICES
    assert "claude-opus-4-7" in CLAUDE_PRICES
    assert "claude-haiku-4-5-20251001" in CLAUDE_PRICES


def test_openai_tts_cost():
    # 10M char @ $15/M = $150
    assert openai_tts_cost(10_000_000) == 150.0
    # 1000 char tipik TTS cagrisi
    cost = openai_tts_cost(1000)
    assert abs(cost - 0.015) < 1e-9


def test_openai_stt_cost():
    # 60 saniye (1 dakika) @ $0.006 = $0.006
    cost = openai_stt_cost(60.0)
    assert abs(cost - 0.006) < 1e-9


def test_apify_cost_places_only():
    assert abs(apify_cost(100) - 0.35) < 1e-9


def test_apify_cost_with_reviews():
    # 20 yer + 20*10 yorum (max_reviews=10)
    cost = apify_cost(20, 200)
    expected = 20 * 0.0035 + 200 * 0.001
    assert abs(cost - expected) < 1e-9
