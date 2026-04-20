"""
Lead Scorer V3 — 8 test senaryosu (spec'ten).

Case 1: Aynı raw sinyal iki layer'da görünmemeli
Case 2: website_exists False → conversion'da etkili, fit/intent'te tekrar puanlanmaz
Case 3: traffic high + conversion low → gap bonus üretsin
Case 4: pattern bonus raw sinyal yerine layer condition kullansın
Case 5: confidence düşükse final yüksek olsa bile segment REVIEW olsun
Case 6: 400+ yorum, 4.7+, strong website → REJECTED
Case 7: 50+ yorum, aktif IG, site yok, booking yok → HOT/WARM çıkabilsin, explain net
Case 8: Zombie işletme → REJECTED
"""
import pytest

from core.lead_scorer import (
    SIGNAL_OWNERSHIP,
    calculate_final_score,
    calc_conversion_score,
    calc_gap_bonus,
    calc_pattern_bonus,
    calc_traffic_score,
    validate_no_double_counting,
)

# ── Fixtures ─────────────────────────────────────────────────────────────────

CLINIC_PLAYBOOK = {"preferred_sectors": ["klinik"], "blog_weight": 1.0}


def _lead(**kwargs) -> dict:
    """Minimum geçerli lead + overrides."""
    defaults: dict = {
        "isim":        "Test Klinik",
        "telefon":     "05551234567",
        "yorum_sayisi": 25,
        "puan":        4.2,
        "website":     None,
        "son_yorum_gun": 20,
        "sektor":      "klinik",
    }
    defaults.update(kwargs)
    return defaults


# ── Case 1: Signal ownership — hiç tekrar yok ────────────────────────────────

def test_signal_ownership_no_duplicates():
    """SIGNAL_OWNERSHIP tablosunda aynı raw alan iki layer'da görünmemeli."""
    seen: dict[str, str] = {}
    duplicates: list[str] = []

    for layer, signals in SIGNAL_OWNERSHIP.items():
        for sig in signals:
            if sig in seen:
                duplicates.append(f"{sig} ({seen[sig]} + {layer})")
            else:
                seen[sig] = layer

    assert duplicates == [], f"Duplicate signals: {duplicates}"


def test_validate_no_double_counting_passes():
    """validate_no_double_counting tabloyu temiz bulmalı."""
    result = validate_no_double_counting()
    assert result["valid"] is True
    assert result["duplicates"] == []


# ── Case 2: website=False → sadece conversion katmanını etkiler ──────────────

def test_website_false_hits_conversion_not_fit_or_intent():
    """website=None conversion'da -22 üretir; fit ve intent tablolarında 'website' yoktur."""
    assert "website" not in SIGNAL_OWNERSHIP["fit"]
    assert "website" not in SIGNAL_OWNERSHIP["intent"]
    assert "website" not in SIGNAL_OWNERSHIP["traffic"]
    assert "website" in SIGNAL_OWNERSHIP["conversion"]


def test_website_false_lowers_conversion_score():
    lead = _lead(
        website=None,
        has_online_booking=False,
        has_cta=False,
        has_whatsapp=False,
        has_trust_signals=False,
    )
    score, explain = calc_conversion_score(lead, {})
    assert score < 30, f"website=None olduğunda conversion düşük olmalı, got {score}"
    assert any("website" in e.lower() for e in explain)


# ── Case 3: high traffic + low conversion → gap bonus ────────────────────────

def test_gap_bonus_fires_on_large_gap():
    bonus, gap, explain = calc_gap_bonus(traffic_score=70, conversion_score=20)
    assert gap == 50
    assert bonus == 15
    assert explain  # açıklama dolu


def test_gap_bonus_zero_on_small_gap():
    bonus, gap, _ = calc_gap_bonus(traffic_score=45, conversion_score=42)
    assert bonus == 0


def test_gap_bonus_tiers():
    assert calc_gap_bonus(80, 35)[0] == 15   # gap=45 ≥40 → 15
    assert calc_gap_bonus(70, 40)[0] == 10   # gap=30 ≥25 → 10
    assert calc_gap_bonus(70, 45)[0] == 10   # gap=25 ≥25 → 10
    assert calc_gap_bonus(60, 50)[0] == 5    # gap=10 ≥10 → 5
    assert calc_gap_bonus(55, 50)[0] == 0    # gap=5  <10 → 0


# ── Case 4: pattern bonus layer condition kullanır, raw sinyal puanlamaz ─────

def test_pattern_bonus_uses_layer_conditions():
    """P1: traffic>=60 AND conversion<=35 → +10 (layer çıktısı, raw sinyal değil)."""
    lead = _lead(website="https://test.com")  # website var, P2 tetiklenmez
    bonus, explain = calc_pattern_bonus(
        lead,
        traffic_score=65,
        conversion_score=30,
        intent_score=50,
    )
    assert bonus >= 10
    assert any("trafik" in e or "dönüşüm" in e for e in explain)
    # Explain'de raw alan adı görünmemeli
    forbidden_raw = ["yorum_sayisi", "review_count", "instagram_post_90d", "puan"]
    for e in explain:
        for raw in forbidden_raw:
            assert raw not in e, f"Raw sinyal '{raw}' explain'de görünmemeli: {e}"


def test_pattern_max_2_active():
    """4 pattern koşulu sağlansa bile max 2 aktif olur, toplam ≤ 15."""
    lead = _lead(website=None, has_cta=False, has_blog=True)
    bonus, explain = calc_pattern_bonus(
        lead,
        traffic_score=70,
        conversion_score=25,
        intent_score=60,
        playbook=CLINIC_PLAYBOOK,
    )
    active_count = sum(1 for e in explain if e.startswith("+"))
    assert active_count <= 2
    assert bonus <= 15


# ── Case 5: low confidence → REVIEW, final yüksek olsa bile ─────────────────

def test_low_confidence_forces_review_segment():
    """Minimal veri → confidence < 0.50 → REVIEW."""
    lead = {
        "isim":    "Minimal Klinik",
        "telefon": "0555",
        # yorum_sayisi eksik → confidence düşer
        # son_yorum_gun eksik → confidence düşer
        # has_online_booking eksik → confidence düşer
        # review_last_30d eksik → confidence düşer
        "website": None,
        "sektor":  "klinik",
    }
    result = calculate_final_score(lead, {}, CLINIC_PLAYBOOK)
    assert result["segment"] == "REVIEW", (
        f"Segment REVIEW bekliyordu, got {result['segment']} "
        f"(confidence={result['confidence']})"
    )
    assert result["confidence"] < 0.50


# ── Case 6: 400+ yorum + 4.7+ + iyi site → REJECTED ────────────────────────

def test_already_strong_is_rejected():
    lead = _lead(
        yorum_sayisi=420,
        puan=4.8,
        website="https://mukemmel-klinik.com",
        site_durumu="iyi",
        son_yorum_gun=5,
    )
    result = calculate_final_score(lead, {}, CLINIC_PLAYBOOK)
    assert result["status"] == "rejected"
    assert "güçlü" in result["reason"].lower()


# ── Case 7: 50+ yorum + IG aktif + site yok → HOT veya WARM ─────────────────

def test_high_traffic_no_conversion_can_score_high():
    """
    50+ yorum, IG aktif, site yok, booking yok →
    traffic yüksek, conversion düşük, gap bonus + pattern bonus tetiklenir.
    Yeterli confidence varsa HOT, yoksa WARM beklenir.
    """
    lead = _lead(
        yorum_sayisi=75,
        puan=4.5,
        instagram_post_90d=30,        # ≥24 → aktif
        review_last_30d=8,
        review_last_90d=20,
        son_yorum_gun=10,
        gmb_photo_count=25,
        gmb_has_description=True,
        gmb_has_qa=True,
        website=None,
        has_online_booking=False,
        has_cta=False,
        has_whatsapp=False,
        has_trust_signals=False,
        oncelikli_ilce=True,
        decision_maker_reachable=True,
    )
    result = calculate_final_score(lead, {}, CLINIC_PLAYBOOK)

    assert result["status"] == "ok", result.get("reason")
    assert result["traffic_score"] >= 50, f"Traffic düşük: {result['traffic_score']}"
    assert result["conversion_score"] < 30, f"Conversion yüksek: {result['conversion_score']}"
    assert result["gap_bonus"] > 0, "Gap bonus tetiklenmedi"
    assert result["final_score"] >= 65, f"Final score düşük: {result['final_score']}"
    assert result["segment"] in ("HOT", "WARM"), f"Segment: {result['segment']}"

    # Explain okunabilir olmalı
    bd = result["score_breakdown"]
    assert any("review" in e.lower() or "yorum" in e.lower() for e in bd), (
        "score_breakdown'da yorum/review açıklaması yok"
    )
    assert any("website" in e.lower() or "site" in e.lower() for e in bd), (
        "score_breakdown'da site açıklaması yok"
    )


# ── Case 8: Zombie işletme → REJECTED ────────────────────────────────────────

def test_zombie_lead_rejected():
    """Son yorumu 366+ gün → zombie → REJECTED."""
    lead = _lead(
        yorum_sayisi=40,
        puan=4.0,
        son_yorum_gun=400,
        website="https://eski-klinik.com",
    )
    result = calculate_final_score(lead, {}, CLINIC_PLAYBOOK)
    assert result["status"] == "rejected"
    assert "zombie" in result["reason"].lower()


# ── Bonus: output formatı backward compat ────────────────────────────────────

def test_output_contains_legacy_keys():
    """Mevcut search_service.py ve UI'ın kullandığı alanlar var olmalı."""
    lead = _lead(
        yorum_sayisi=30,
        puan=4.0,
        son_yorum_gun=15,
        review_last_30d=3,
        review_last_90d=8,
        gmb_has_description=True,
        gmb_has_qa=True,
        has_online_booking=False,
    )
    result = calculate_final_score(lead, {}, CLINIC_PLAYBOOK)

    legacy_keys = [
        "status", "segment", "final_score", "confidence",
        "opportunity_score", "opportunity", "intent_score", "buyer_intent",
        "priority", "reason_summary", "decision_reason",
        "score_breakdown", "score_layers", "signals",
    ]
    for key in legacy_keys:
        assert key in result, f"Legacy key eksik: {key}"
