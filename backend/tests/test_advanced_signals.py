"""Tests for the 4 advanced micro-scoring signals."""
import pytest
from core.advanced_signals import (
    calc_competition_density,
    calc_ppc_waste,
    calc_social_mismatch,
    calc_ecommerce_urgency,
    compute_advanced_signals,
    HIGH_ECOMMERCE_SECTORS,
)


# ── Competition Density ──────────────────────────────────────────────

class TestCompetitionDensity:
    def test_no_competition(self):
        lead = {"website": "https://example.com", "in_organic_top10": True, "site_durumu": "iyi"}
        serp = {"strong_competitor_count": 0, "competitor_ads_count": 0}
        result = calc_competition_density(lead, serp)
        assert result["competition_density_score"] == 0
        assert result["strong_competitor_count"] == 0

    def test_high_competition_weak_lead(self):
        lead = {"website": None, "in_organic_top10": False, "site_durumu": "yok"}
        serp = {"strong_competitor_count": 6, "competitor_ads_count": 4}
        result = calc_competition_density(lead, serp)
        assert result["competition_density_score"] >= 80
        assert any("Yoğun rekabet" in s for s in result["signals"])

    def test_medium_competition(self):
        lead = {"website": "https://example.com", "in_organic_top10": False, "site_durumu": "zayif", "indexed_pages": 3}
        serp = {"strong_competitor_count": 3, "competitor_ads_count": 2}
        result = calc_competition_density(lead, serp)
        assert 40 <= result["competition_density_score"] <= 100

    def test_lead_already_strong_reduces_gap(self):
        lead = {"website": "https://example.com", "in_organic_top10": True, "self_ads_visible": True, "site_durumu": "iyi"}
        serp = {"strong_competitor_count": 4, "competitor_ads_count": 3}
        result = calc_competition_density(lead, serp)
        # Lead is strong → digital gap is small → score lower than weak lead
        assert result["competition_density_score"] < 70


# ── PPC Waste ────────────────────────────────────────────────────────

class TestPPCWaste:
    def test_no_ads_no_waste(self):
        lead = {"self_ads_visible": False}
        audit = {}
        result = calc_ppc_waste(lead, audit)
        assert result["ppc_waste_score"] == 0

    def test_ads_with_bad_site(self):
        lead = {
            "self_ads_visible": True,
            "has_viewport": False,
            "site_durumu": "zayif",
            "has_cta": False,
            "has_online_booking": False,
        }
        audit = {"pagespeed": 25, "ssl": False}
        result = calc_ppc_waste(lead, audit)
        assert result["ppc_waste_score"] >= 80
        assert any("Mobil viewport" in s for s in result["signals"])

    def test_ads_with_good_site(self):
        lead = {
            "self_ads_visible": True,
            "has_viewport": True,
            "site_durumu": "iyi",
            "has_cta": True,
            "has_online_booking": True,
        }
        audit = {"pagespeed": 80, "ssl": True}
        result = calc_ppc_waste(lead, audit)
        # Ads running but site is good → low waste
        assert result["ppc_waste_score"] <= 40


# ── Social Mismatch ──────────────────────────────────────────────────

class TestSocialMismatch:
    def test_inactive_social(self):
        lead = {"instagram_post_90d": 0}
        result = calc_social_mismatch(lead)
        assert result["social_mismatch_score"] == 0

    def test_active_social_no_website(self):
        lead = {
            "instagram_post_90d": 15,
            "instagram_last_post_days": 5,
            "website": None,
            "site_durumu": "yok",
            "has_cta": False,
            "has_online_booking": False,
            "has_whatsapp": False,
        }
        result = calc_social_mismatch(lead)
        assert result["social_mismatch_score"] >= 60
        assert any("Website yok" in s for s in result["signals"])

    def test_active_social_good_site(self):
        lead = {
            "instagram_post_90d": 12,
            "instagram_last_post_days": 3,
            "website": "https://example.com",
            "site_durumu": "iyi",
            "has_cta": True,
            "has_online_booking": True,
            "has_whatsapp": True,
        }
        result = calc_social_mismatch(lead)
        # Social active but site is good → mismatch bonus is 0
        assert result["social_mismatch_score"] <= 45


# ── E-commerce Urgency ───────────────────────────────────────────────

class TestEcommerceUrgency:
    def test_non_ecommerce_sector(self):
        lead = {"sektor": "avukat", "website": None}
        result = calc_ecommerce_urgency(lead)
        assert result["ecommerce_urgency_score"] == 0

    def test_ecommerce_sector_no_website(self):
        lead = {
            "sektor": "guzellik",
            "website": None,
            "site_durumu": "yok",
            "has_online_booking": False,
            "has_cta": False,
            "has_form": False,
            "yorum_sayisi": 25,
        }
        result = calc_ecommerce_urgency(lead)
        assert result["ecommerce_urgency_score"] >= 80
        assert any("Website yok" in s for s in result["signals"])
        assert any("Maps'te güçlü" in s for s in result["signals"])

    def test_ecommerce_sector_decent_site(self):
        lead = {
            "sektor": "guzellik",
            "website": "https://example.com",
            "site_durumu": "iyi",
            "has_online_booking": True,
            "has_cta": True,
            "has_form": True,
            "indexed_pages": 50,
            "yorum_sayisi": 30,
        }
        result = calc_ecommerce_urgency(lead)
        # Good site → urgency is low (only base sector bonus)
        assert result["ecommerce_urgency_score"] <= 30

    def test_high_ecommerce_sectors_defined(self):
        assert "guzellik" in HIGH_ECOMMERCE_SECTORS
        assert "oto_servis" in HIGH_ECOMMERCE_SECTORS
        assert "restoran" in HIGH_ECOMMERCE_SECTORS


# ── Aggregate ────────────────────────────────────────────────────────

class TestComputeAdvancedSignals:
    def test_returns_all_4_scores(self):
        lead = {"sektor": "guzellik", "self_ads_visible": True, "instagram_post_90d": 8}
        audit = {"pagespeed": 30}
        serp = {"strong_competitor_count": 3, "competitor_ads_count": 2}
        result = compute_advanced_signals(lead, audit, serp)
        assert "competition_density" in result
        assert "ppc_waste" in result
        assert "social_mismatch" in result
        assert "ecommerce_urgency" in result
        assert "advanced_score_breakdown" in result
        assert len(result["advanced_score_breakdown"]) == 4

    def test_no_serp_data(self):
        lead = {"sektor": "guzellik", "instagram_post_90d": 5, "website": "https://example.com", "site_durumu": "iyi"}
        audit = {}
        result = compute_advanced_signals(lead, audit, None)
        # Competition and PPC should be 0 without SERP data (no competitor info)
        assert result["competition_density"]["competition_density_score"] == 0
        assert result["ppc_waste"]["ppc_waste_score"] == 0
        # Social and ecom should still work
        assert result["social_mismatch"]["social_mismatch_score"] > 0
        assert result["ecommerce_urgency"]["ecommerce_urgency_score"] > 0