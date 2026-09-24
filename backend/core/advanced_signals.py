"""
Advanced Micro-Scoring Signals — 4 yeni kriter.

Bu modül, lead_scorer'a ham sinyal üretir. Skorlama weight'leri
lead_scorer.py'da uygulanır.

Kriterler:
  1. Rekabet Yoğunluğu (competition_density)
  2. Reklam/PPC İsrafı (ppc_waste)
  3. Sosyal Medya Uyuşmazlığı (social_mismatch)
  4. Sektörel E-Ticaret Aciliyeti (ecommerce_urgency)

Not: core/ katmanı framework-agnostic — FastAPI/ARQ/Telegram import yok.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── E-ticaret potansiyeli yüksek sektörler ─────────────────────────
# Bu sektörlerde fiziksel-dükkan-only modeller büyük değer kaybediyor.
HIGH_ECOMMERCE_SECTORS: frozenset[str] = frozenset({
    "guzellik",        # kozmetik, cilt bakımı ürün satışı
    "klinik",          # medikal ürünler, takviye, cihaz
    "kadin_dogum",     # özel ürünler, danışmanlık paketleri
    "oto_servis",      # yedek parça, aksesuar
    "klima_beyaz_esya",# yedek parça, aksesuar
    "ev_hizmetleri",   # malzeme satışı, abonelik
    "restoran",        # online sipariş, catering
    "egitim",          # online kurs, dijital içerik
})


# --------------------------------------------------
# 1. REKABET YOĞUNLUĞU
# --------------------------------------------------

def calc_competition_density(lead: dict, serp: dict) -> dict:
    """Rekabet yoğunluğu sinyali.

    Mantık: Aynı sektörde dijital varlığı mükemmel rakipler varken,
    kendisi geride olan firmalar daha yüksek öncelik almalı.

    Inputs (serp'den):
      - strong_competitor_count  int
      - ad_domains              set
      - organic_domains         list[(domain, pos)]

    Inputs (lead'den):
      - website                 str|None
      - in_organic_top10        bool|None
      - self_ads_visible        bool|None
      - site_durumu             str
      - indexed_pages           int|None
    """
    strong_count = lead.get("strong_competitor_count") or serp.get("strong_competitor_count") or 0
    ad_count = lead.get("competitor_ads_count") or serp.get("competitor_ads_count") or 0

    website = lead.get("website")
    in_top10 = lead.get("in_organic_top10")
    self_ads = lead.get("self_ads_visible")
    site_durumu = lead.get("site_durumu") or "yok"
    indexed = lead.get("indexed_pages")

    signals: list[str] = []
    score = 0  # 0–100

    # Rakip sayısına göre taban puan (0–40)
    if strong_count >= 5:
        score += 40
        signals.append(f"Yoğun rekabet ({strong_count} güçlü rakip)")
    elif strong_count >= 3:
        score += 25
        signals.append(f"Orta rekabet ({strong_count} rakip)")
    elif strong_count >= 1:
        score += 10
        signals.append(f"Düşük rekabet ({strong_count} rakip)")

    # Dijital zayıflık bonusu (0–40) — rakip var ama kendisi geride
    digital_gap = 0
    if not website:
        digital_gap += 20
        signals.append("Website yok (dijital varlık sıfır)")
    elif site_durumu in ("yok", "zayif"):
        digital_gap += 12
        signals.append(f"Site zayıf ({site_durumu})")

    if in_top10 is False:
        digital_gap += 12
        signals.append("Organik aramada yok")
    elif in_top10 is True:
        digital_gap -= 8  # zaten görünür → gap azalır

    if indexed is not None and indexed <= 5:
        digital_gap += 8
        signals.append(f"Çok az index ({indexed})")

    if self_ads is False and ad_count >= 2:
        digital_gap += 8
        signals.append("Rakipler reklam veriyor, kendisi yok")

    score += max(0, digital_gap)

    # Reklam baskı bonusu (0–20)
    if ad_count >= 3:
        score += 20
        signals.append(f"Yoğun reklam baskısı ({ad_count} reklam)")
    elif ad_count >= 1:
        score += 10
        signals.append(f"Reklam baskısı ({ad_count} reklam)")

    score = max(0, min(100, score))

    return {
        "competition_density_score": score,
        "strong_competitor_count": strong_count,
        "signals": signals,
    }


# --------------------------------------------------
# 2. PPC İSRAFI
# --------------------------------------------------

def calc_ppc_waste(lead: dict, audit: dict) -> dict:
    """Bütçesi var ama yanlış harcayan firmaları tespit et.

    Mantık: Google Ads'te görünüyor (kendi domain'i reklamda)
    AMA web sitesi mobile uyumsuz, yavaş, veya landing page yok.

    Inputs:
      - self_ads_visible    bool — SERP'de kendi reklamı var mı?
      - has_viewport        bool — mobile viewport meta tag
      - pagespeed           int|None — mobil performans skoru
      - site_durumu         str — "iyi" | "zayif" | "yok"
      - has_cta             bool — dönüşüm butonu var mı?
      - has_online_booking  bool — online randevu var mı?
    """
    self_ads = lead.get("self_ads_visible") is True
    signals: list[str] = []

    if not self_ads:
        return {"ppc_waste_score": 0, "signals": ["Kendi reklamı tespit edilmedi"]}

    # Reklam veriyor → puanlama başlasın
    score = 30  # taban: reklam veriyor = bütçe var

    # Site kalitesi sorunları (her biri +bonus)
    has_viewport = lead.get("has_viewport")
    if has_viewport is False:
        score += 20
        signals.append("Mobil viewport yok (mobil uyumsuz)")

    pagespeed = audit.get("pagespeed")
    if pagespeed is not None:
        if pagespeed < 30:
            score += 15
            signals.append(f"Mobil performans çok düşük ({pagespeed})")
        elif pagespeed < 50:
            score += 8
            signals.append(f"Mobil performans düşük ({pagespeed})")

    site_durumu = lead.get("site_durumu") or "yok"
    if site_durumu == "zayif":
        score += 12
        signals.append("Site zayıf (CTA/booking yok)")

    has_cta = lead.get("has_cta")
    if has_cta is False:
        score += 10
        signals.append("CTA butonu yok → landing page dönüşümsüz")

    has_booking = lead.get("has_online_booking")
    if has_booking is False:
        score += 8
        signals.append("Online booking yok → para harcıyor ama kaçırıyor")

    ssl = audit.get("ssl")
    if ssl is False:
        score += 5
        signals.append("SSL yok → reklam kalite skoru düşük")

    score = max(0, min(100, score))

    return {
        "ppc_waste_score": score,
        "signals": signals,
    }


# --------------------------------------------------
# 3. SOSYAL MEDYA UYUŞMAZLIĞI
# --------------------------------------------------

def calc_social_mismatch(lead: dict) -> dict:
    """Aktif sosyal medya ama dönüşüm odaklı olmayan web sitesi.

    Mantık: Instagram/Facebook'ta aktif paylaşım yapan firma
    (dijitale bütçe/zaman ayırıyor) ama web sitesi dönüşüm odaklı değil
    → bu firmalar dijitalin farkında ama henüz profesyonel yardım almamış.

    Inputs:
      - instagram_post_90d      int|None
      - instagram_last_post_days int|None
      - facebook_active         bool|None (Maps'ten gelen sinyal)
      - website                 str|None
      - site_durumu             str
      - has_cta                 bool|None
      - has_online_booking      bool|None
      - has_whatsapp            bool|None
    """
    signals: list[str] = []

    # Sosyal medya aktivitesi (0–50)
    social_score = 0
    ig_posts = lead.get("instagram_post_90d")
    ig_last = lead.get("instagram_last_post_days")
    fb_active = lead.get("facebook_active")

    if ig_posts is not None:
        if ig_posts >= 10:
            social_score += 25
            signals.append(f"IG çok aktif ({ig_posts} post/90g)")
        elif ig_posts >= 5:
            social_score += 18
            signals.append(f"IG aktif ({ig_posts} post/90g)")
        elif ig_posts >= 2:
            social_score += 10
            signals.append(f"IG orta aktif ({ig_posts} post/90g)")

    if ig_last is not None and ig_last < 14:
        social_score += 10
        signals.append(f"IG son post {ig_last}g önce (taze)")

    if fb_active is True:
        social_score += 10
        signals.append("Facebook aktif")

    if social_score < 15:
        return {"social_mismatch_score": 0, "signals": ["Sosyal medya aktivitesi düşük"]}

    # Dijital yatırım var ama site dönüşümsüz → uyuşmazlık bonusu
    website = lead.get("website")
    site_durumu = lead.get("site_durumu") or "yok"
    has_cta = lead.get("has_cta")
    has_booking = lead.get("has_online_booking")
    has_whatsapp = lead.get("has_whatsapp")

    mismatch_bonus = 0
    if not website:
        mismatch_bonus += 30
        signals.append("Website yok (sosyal var ama site yok)")
    elif site_durumu == "zayif":
        mismatch_bonus += 20
        signals.append("Site zayıf (sosyal aktif ama site dönüşümsüz)")

    if has_cta is False:
        mismatch_bonus += 10
        signals.append("CTA yok → sosyal trafik boşa gidiyor")

    if has_booking is False:
        mismatch_bonus += 5
        signals.append("Booking yok → sosyal'den gelen kaçıyor")

    if has_whatsapp is False and (ig_posts or 0) >= 5:
        mismatch_bonus += 5
        signals.append("WhatsApp yok → IG'den iletişim kopuk")

    score = min(100, social_score + mismatch_bonus)

    return {
        "social_mismatch_score": score,
        "signals": signals,
    }


# --------------------------------------------------
# 4. SEKTÖREL E-TİCARET ACİLİYETİ
# --------------------------------------------------

def calc_ecommerce_urgency(lead: dict) -> dict:
    """E-ticaret potansiyeli yüksek sektörlerde fiziksel-only firmalar.

    Mantık: Yerel butikler, yedek parçacılar, toptancılar gibi
    e-ticarete çok uygun sektörlerde hala fiziksel dükkan veya
    basit kartvizit site kullananları "En Sıcak Müşteri" yap.

    Inputs:
      - sektor              str
      - website             str|None
      - site_durumu         str
      - has_online_booking  bool|None
      - has_cta             bool|None
      - has_form            bool|None
      - indexed_pages       int|None
      - yorum_sayisi        int
    """
    sektor = lead.get("sektor") or lead.get("sector") or ""
    signals: list[str] = []

    if sektor not in HIGH_ECOMMERCE_SECTORS:
        return {"ecommerce_urgency_score": 0, "signals": ["Sektör e-ticaret aciliyeti kapsamında değil"]}

    website = lead.get("website")
    site_durumu = lead.get("site_durumu") or "yok"
    has_booking = lead.get("has_online_booking")
    has_cta = lead.get("has_cta")
    has_form = lead.get("has_form")
    indexed = lead.get("indexed_pages")
    yorum = lead.get("yorum_sayisi") or 0

    score = 0

    # Sektör bonusu (taban)
    score += 25
    signals.append(f"E-ticaret potansiyeli yüksek sektör ({sektor})")

    # Fiziksel-only sinyalleri (her biri +bonus)
    if not website:
        score += 35
        signals.append("Website yok (fiziksel-only)")
    elif site_durumu == "zayif":
        score += 20
        signals.append("Kartvizit site (dönüşüm yok)")

    if has_booking is False:
        score += 10
        signals.append("Online satış/booking yok")

    if has_cta is False and website:
        score += 8
        signals.append("CTA yok → ürün/hizmet satışı yok")

    if has_form is False and website:
        score += 5
        signals.append("Form yok → sipariş/talep altyapısı yok")

    if indexed is not None and indexed <= 5:
        score += 10
        signals.append(f"Çok az index ({indexed}) → dijital ayak izi minimal")

    # Maps'te güçlü ama dijitale geçmemiş → en sıcak profil
    if yorum >= 20 and not website:
        score += 15
        signals.append(f"Maps'te güçlü ({yorum} yorum) ama website yok → en sıcak profil")
    elif yorum >= 10 and site_durumu in ("yok", "zayif"):
        score += 8
        signals.append(f"Maps'te aktif ({yorum} yorum) ama site zayıf")

    score = max(0, min(100, score))

    return {
        "ecommerce_urgency_score": score,
        "signals": signals,
    }


# --------------------------------------------------
# AGGREGATE
# --------------------------------------------------

def compute_advanced_signals(
    lead: dict,
    audit: dict,
    serp: dict | None = None,
) -> dict:
    """Tüm 4 kriteri hesapla ve tek bir dict olarak döndür.

    Serp verisi yoksa (search modunda SERP atlanıyorsa) rekabet ve PPC
    sinyalleri doğal olarak 0 kalır — sosyal ve e-ticaret kendi başına çalışır.
    """
    serp = serp or {}

    competition = calc_competition_density(lead, serp)
    ppc = calc_ppc_waste(lead, audit)
    social = calc_social_mismatch(lead)
    ecom = calc_ecommerce_urgency(lead)

    all_signals = (
        competition["signals"]
        + ppc["signals"]
        + social["signals"]
        + ecom["signals"]
    )

    return {
        "competition_density": competition,
        "ppc_waste": ppc,
        "social_mismatch": social,
        "ecommerce_urgency": ecom,
        "advanced_score_breakdown": [
            f"Rekabet: {competition['competition_density_score']}",
            f"PPC İsraf: {ppc['ppc_waste_score']}",
            f"Sosyal Uyuşmazlık: {social['social_mismatch_score']}",
            f"E-Ticaret Aciliyet: {ecom['ecommerce_urgency_score']}",
        ],
        "all_signals": all_signals,
    }