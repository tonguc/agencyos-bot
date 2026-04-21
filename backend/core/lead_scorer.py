"""
Lead Scorer V3 — satış-öncelikli, pure-score routing.

Formül:
  combined = 0.75 × Opportunity + 0.25 × Intent
  boosted  = combined × Pattern_Multiplier        (1.00–1.15)
  final    = min(100, boosted × Fit_Multiplier)   (Fit: 0.85–1.10)

Sonra satış floor'u uygulanır:
  website yok + telefon var + yorum<30 → min 70 (güçlü fırsat)
  website yok + telefon var + fit≥0.95 → min 65 (kontrollü floor)

Katmanlar:
  HARD FILTER        → kurumsal/zincir, kalıcı kapalı, zaten güçlü
  OPPORTUNITY 0-100  → Maps + Website (+40) + SEO + keyword coverage + Audit eksikleri
  INTENT      0-100  → Maps aktivite + Sosyal + Dijital yatırım
  FIT_MUL     .85-1.10 → ICP çarpanı
  PATTERN_MUL 1.00-1.15 → sinyal kombinasyonları, max %15 boost

Routing (sadece skora göre, confidence routing yok):
  REVIEW  → zombie risk | final<55
  HOT     → final≥70
  WARM    → 55 ≤ final < 70
"""

from __future__ import annotations

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


# --------------------------------------------------
# CONSTANTS
# --------------------------------------------------

# Bilinen zincir/kurumsal markalar (Türkiye). Hard filter listesi.
CHAIN_BRANDS = [
    "hastane", "devlet hastane", "eğitim ve araştırma",
    "acibadem", "acıbadem", "medipol", "memorial", "medical park",
    "medicana", "liv hospital", "florence nightingale",
    "amerikan hastanesi", "yeditepe hastane", "echomar", "kent hospital",
    "medstar", "özel hospital", "dünyagöz", "anadolu sağlık",
    "maltepe üniversitesi", "üniversite hastane", "universite hastane",
    "group", "holding",
]

SEGMENT_TO_PRIORITY = {
    "HOT":    "yuksek",
    "WARM":   "orta",
    "LOW":    "dusuk",
    "REVIEW": "orta",
}

DEFAULT_FEATURE_WEIGHTS = {
    "blog_signal": 1.0,
    "content_depth_signal": 1.0,
    "linkedin_signal": 1.0,
    "youtube_signal": 1.0,
    "instagram_signal": 1.0,
    "online_booking_signal": 1.0,
    "ads_signal": 1.0,
    "trust_signal": 1.0,
}


# --------------------------------------------------
# 1. HARD FILTER
# --------------------------------------------------

def hard_filter(lead: dict, playbook: dict) -> Tuple[bool, str]:
    """Direkt ELENDİ. (True, reason) | (False, '')"""
    isim = (lead.get("isim") or "").lower()

    for brand in CHAIN_BRANDS:
        if brand in isim:
            return True, f"kurumsal / zincir ({brand})"

    if lead.get("permanently_closed"):
        return True, "kalıcı olarak kapalı"

    yorum = lead.get("yorum_sayisi") or 0
    puan = lead.get("puan") or 0
    website = lead.get("website")
    site_durumu = lead.get("site_durumu", "zayif")
    if yorum > 400 and puan > 4.7 and website and site_durumu == "iyi":
        return True, "zaten güçlü"

    return False, ""


# --------------------------------------------------
# 2. OPPORTUNITY (0–100, baz: 40)
# --------------------------------------------------

def calc_opportunity(lead: dict, audit: dict) -> tuple[int, list[str]]:
    """
    Sadece Maps + Website + SEO + Audit eksikliklerini ölçer.
    Conversion (CTA/WhatsApp/booking), sosyal, reklam sinyalleri burada YOK —
    onlar Intent veya Pattern'e aittir.
    """
    score = 40
    signals: list[str] = []

    def add(delta: int, label: str) -> None:
        nonlocal score
        score += delta
        if delta != 0:
            signals.append(f"{label} → {'+' if delta > 0 else ''}{delta}")

    # A. Maps / Profil sağlığı
    yorum = lead.get("yorum_sayisi") or 0
    puan = lead.get("puan") or 0
    telefon = lead.get("telefon")

    if not telefon:
        add(-5, "Telefon yok (ulaşım güçleşir)")

    if yorum < 10:
        add(15, f"Yorum az ({yorum})")
    elif yorum <= 30:
        add(8, f"Yorum az-orta ({yorum})")
    elif yorum > 100:
        add(-8, f"Yorum çok ({yorum})")

    if 3.8 <= puan <= 4.2:
        add(10, f"Puan orta ({puan})")
    elif 0 < puan < 3.8:
        add(14, f"Puan düşük ({puan})")  # düşük puan = itibar yönetimi fırsatı
    elif puan > 4.6:
        add(-10, f"Puan yüksek ({puan})")

    # Kombinasyon: az yorum + vasat puan → dijital büyüme fırsatı
    # (her sinyal tek tek orta güçte; ikisi birden = net boşluk)
    if yorum < 30 and 0 < puan <= 4.2:
        add(8, f"Az yorum + vasat puan ({yorum} yorum, {puan:.1f}★)")

    # B. Website gücü
    website = lead.get("website")
    site_durumu = lead.get("site_durumu")
    if not website:
        add(40, "Website yok")
        if telefon:
            # Telefon var + site yok = en temiz satış fırsatı (sabit boost)
            add(10, "Telefon var + site yok (direkt fırsat)")
    elif site_durumu == "zayif":
        add(12, "Site zayıf")
    elif site_durumu == "orta":
        add(4, "Site orta")
    elif site_durumu == "iyi":
        add(-6, "Site iyi")

    # C. SEO / SERP görünürlüğü
    if website:
        if lead.get("in_organic_top10") is False:
            add(15, "Organik aramada görünmüyor")
        elif lead.get("in_organic_top10") is True:
            add(-8, "Organik aramada görünüyor")

        indexed = lead.get("indexed_pages")
        if indexed is not None:
            if indexed == 0:
                add(18, "Google'da hiç sayfa indexlenmemiş")
            elif indexed <= 5:
                add(10, f"Çok az sayfa indexlenmiş ({indexed})")
            elif indexed <= 20:
                add(4, f"Az sayfa indexlenmiş ({indexed})")
            elif indexed >= 200:
                add(-6, f"Güçlü SEO varlığı ({indexed} sayfa)")

    if lead.get("has_ai_overview") is True:
        if lead.get("in_ai_overview") is False:
            add(10, "AI Overview var, listede değil")
        else:
            add(-5, "AI Overview'da görünüyor")

    # C2. High-intent keyword coverage (search-time; 3 sorgu: lokal + acil + fiyat)
    # Hiç görünmüyorsa = tam satış fırsatı. Hepsinde görünüyorsa = zaten güçlü.
    # keyword_coverage_score=None → bu alan hiç set edilmemiş (full collect vs.), atla.
    coverage = lead.get("keyword_coverage_score")
    if coverage is not None and website:
        if coverage == 0:
            add(10, "High-intent aramada yok (0/3)")
        elif coverage == 1:
            add(5, "High-intent coverage düşük (1/3)")
        elif coverage >= 3:
            add(-5, "High-intent aramalarda görünüyor (3/3)")

    # D. Audit
    audit_skor = audit.get("genel_skor")
    if audit_skor is not None:
        if audit_skor < 35:
            add(12, f"Audit çok zayıf ({audit_skor})")
        elif audit_skor <= 55:
            add(6, f"Audit zayıf ({audit_skor})")
        elif audit_skor > 75:
            add(-8, f"Audit güçlü ({audit_skor})")

    # D2. Mobil PageSpeed — lead dict'ten (search-time) veya audit dict'ten (full audit)
    # İki kaynaktan en güveniliri: lead'den geliyorsa gerçek PSI verisi, audit'ten tahmini.
    pagespeed = lead.get("mobile_speed_score") or audit.get("pagespeed")
    if pagespeed is not None:
        if pagespeed < 30:
            add(12, f"Mobil çok yavaş ({pagespeed}/100)")
        elif pagespeed < 50:
            add(7, f"Mobil yavaş ({pagespeed}/100)")
        elif pagespeed < 70:
            add(3, f"Mobil orta ({pagespeed}/100)")
        elif pagespeed > 85:
            add(-4, f"Mobil hızlı ({pagespeed}/100)")

    if audit.get("ssl") is False:
        add(6, "SSL yok")

    # E2. Site analiz edilmedi (search-time varsayım)
    # Türkiye'de küçük işletme sitesi var ≠ iyi site.
    # SERP/index verisi yoksa "mediocre" varsayımı yaparız (+5).
    # Tam analiz sonrası in_organic_top10/indexed_pages dolar → bu bonus kalkar,
    # yerine gerçek SEO sinyalleri (±8–18) devreye girer.
    if website and lead.get("in_organic_top10") is None and lead.get("indexed_pages") is None:
        add(5, "Site analiz edilmedi (mediocre varsayım)")

    # E. Site eskimesi (opportunity açısından — hafif ağırlık)
    # Intent tarafında daha güçlü, burada sadece "çürüme" sinyali.
    update_days = lead.get("last_website_update_days")
    update_conf = lead.get("website_update_confidence") or 0.0
    site_durumu = lead.get("site_durumu")

    if website and update_days is not None and update_conf >= 0.4:
        # site_durumu = iyi ise zaten güçlü — staleness bonus'unu cap'le
        site_iyi = site_durumu == "iyi"
        if update_days > 365:
            add(3 if site_iyi else 8, f"Site çok eski ({update_days}g)")
        elif update_days > 180:
            add(2 if site_iyi else 5, f"Site eski ({update_days}g)")
        elif update_days > 90:
            add(1 if site_iyi else 2, f"Site yaşlanmış ({update_days}g)")

    # F. Instagram × Site kombinasyonu
    # Instagram var + site zayıf = organik trafik geliyor, web'de kaybolup gidiyor.
    # has_instagram=None → site analizi yapılmamış, sinyal yok.
    has_ig = lead.get("has_instagram")
    site_durumu_now = lead.get("site_durumu")
    if has_ig is True and site_durumu_now in ("zayif", "yok"):
        add(8, "Instagram var, site zayıf (dönüşüm açığı)")

    return max(0, min(score, 100)), signals


# --------------------------------------------------
# 3. INTENT (0–100, baz: 50)
# --------------------------------------------------

def calc_intent(lead: dict, audit: dict) -> tuple[int, list[str]]:
    """Aktivite + satın alma sinyalleri. Opp ile çakışmaz."""
    score = 50
    signals: list[str] = []

    def add(delta: int, label: str) -> None:
        nonlocal score
        score += delta
        if delta != 0:
            signals.append(f"{label} → {'+' if delta > 0 else ''}{delta}")

    # A. Google Maps aktivitesi
    son_yorum = lead.get("son_yorum_gun")
    if son_yorum is not None:
        if son_yorum < 30:
            add(15, f"Son yorum yakın ({son_yorum}g)")
        elif son_yorum < 90:
            add(8, f"Son yorum orta ({son_yorum}g)")
        elif son_yorum > 180:
            add(-15, f"Son yorum eski ({son_yorum}g)")

    rev_30 = lead.get("review_last_30d")
    if rev_30 is not None:
        if rev_30 >= 5:
            add(12, f"Son 30g yorum: {rev_30}")
        elif rev_30 >= 2:
            add(6, f"Son 30g yorum: {rev_30}")

    rev_90 = lead.get("review_last_90d")
    if rev_90 is not None and rev_90 >= 10:
        add(8, f"Son 90g yorum: {rev_90}")

    # B. Sosyal aktivite
    post_90 = lead.get("instagram_post_90d")
    if post_90 is not None:
        if post_90 == 0:
            add(-6, "IG 90g post: 0")
        elif post_90 <= 3:
            add(-2, f"IG 90g post: {post_90}")
        elif post_90 <= 10:
            add(4, f"IG 90g post: {post_90}")
        else:
            add(6, f"IG 90g post: {post_90}")

    last_post = lead.get("instagram_last_post_days")
    if last_post is not None:
        if last_post < 14:
            add(4, f"IG son post: {last_post}g")
        elif last_post < 60:
            add(2, f"IG son post: {last_post}g")
        elif last_post > 60:
            add(-4, f"IG son post: {last_post}g")

    if lead.get("linkedin_active_30d") is True:
        add(8, "LinkedIn aktif (30g)")

    yt_180 = lead.get("youtube_video_180d")
    if yt_180 is not None:
        if 3 <= yt_180 <= 6:
            add(3, f"YouTube 180g video: {yt_180}")
        elif yt_180 > 6:
            add(4, f"YouTube 180g video: {yt_180}")

    # C. Dijital yatırım — site güncelleme tazeliği (intent için ana sinyal)
    update_days = lead.get("last_website_update_days")
    update_conf = lead.get("website_update_confidence") or 0.0

    if update_days is not None and update_conf >= 0.4:
        if update_days < 30:
            add(10, f"Site çok taze ({update_days}g)")
        elif update_days < 60:
            add(6, f"Site güncel ({update_days}g)")
        elif update_days < 90:
            add(2, f"Site normal ({update_days}g)")
        elif update_days <= 180:
            pass  # nötr
        elif update_days <= 365:
            add(-4, f"Site bakımsız ({update_days}g)")
        else:
            add(-8, f"Site terk edilmiş ({update_days}g)")

    if lead.get("market_ads_pressure") is True:
        add(4, "Sektörde reklam baskısı")

    competitor_ads = lead.get("competitor_ads_count")
    if competitor_ads is not None and competitor_ads >= 2:
        add(6, f"Rakip aktif reklam ({competitor_ads})")

    return max(0, min(score, 100)), signals


# --------------------------------------------------
# 4. FIT MULTIPLIER (0.85–1.10) — SADECE ICP
# --------------------------------------------------

def calc_fit_multiplier(lead: dict, playbook: dict) -> tuple[float, list[str]]:
    """ICP uyumu. Başka sinyal yok — double count önlemi."""
    mul = 1.00
    signals: list[str] = []

    sektor = lead.get("sektor") or lead.get("sector") or ""
    preferred = playbook.get("preferred_sectors", [])

    if preferred and sektor and sektor in preferred:
        mul += 0.05
        signals.append("Hedef sektör")
    elif preferred and sektor and sektor not in preferred:
        mul -= 0.04
        signals.append(f"Hedef dışı sektör ({sektor})")

    if lead.get("oncelikli_ilce"):
        mul += 0.05
        signals.append("Öncelikli ilçe")

    if lead.get("playbook_tip_ok") is True:
        mul += 0.03
        signals.append("İşletme tipi uygun")

    if lead.get("decision_maker_reachable") is True:
        mul += 0.02
        signals.append("Karar verici ulaşılabilir")

    yorum = lead.get("yorum_sayisi") or 0
    if yorum < 5:
        mul -= 0.05
        signals.append(f"Çok küçük ({yorum} yorum, churn riski)")

    if lead.get("kurumsal_yapi_yavas") is True:
        mul -= 0.05
        signals.append("Yavaş satış döngüsü (kurumsal)")

    return max(0.85, min(1.10, mul)), signals


# --------------------------------------------------
# 5. PATTERN MULTIPLIER (1.00–1.15) — ÇARPAN, additive DEĞİL
# --------------------------------------------------

def calc_pattern_multiplier(lead: dict, audit: dict, playbook: dict) -> tuple[float, list[str]]:
    """Güçlü sinyal kombinasyonları + sektör spesifik. Toplam max %15 boost."""
    boost = 0.0
    signals: list[str] = []

    def fire(delta: float, label: str) -> None:
        nonlocal boost
        boost += delta
        signals.append(f"+{int(delta*100)}% {label}")

    website = lead.get("website")
    site_durumu = lead.get("site_durumu")
    telefon = lead.get("telefon")
    yorum = lead.get("yorum_sayisi") or 0
    puan = lead.get("puan") or 0

    post_90 = lead.get("instagram_post_90d")
    has_booking = lead.get("has_online_booking")
    has_cta = lead.get("has_cta")
    rev_30 = lead.get("review_last_30d")
    competitor_ads = lead.get("competitor_ads_count")
    self_ads = lead.get("self_ads_visible")

    # IG aktif + booking yok → para geliyor, yakalama aracı yok
    if post_90 is not None and post_90 > 5 and has_booking is False:
        fire(0.06, "IG aktif + booking yok")

    # Maps güçlü + site zayıf → organik trafik var, dönüşüm kırık
    if yorum > 20 and puan >= 4.0 and (not website or site_durumu == "zayif"):
        fire(0.05, "Maps güçlü + site zayıf")

    # Taze yorum + CTA yok → trafik var, CTA eksikliği kayıp
    if rev_30 is not None and rev_30 >= 3 and has_cta is False:
        fire(0.04, "Taze yorum + CTA yok")

    # Rakip reklam basıyor + kendisi yok → açık pazar
    if competitor_ads is not None and competitor_ads >= 2 and self_ads is False:
        fire(0.04, "Rakip reklam + self yok")

    # Telefon + website yok sinyali opportunity katmanında sabit +10 olarak işleniyor
    # (pattern multiplier'da çift sayımı önlemek için burada yok).

    # ── Sektör-spesifik ──────────────────────────────
    sub_cli = lead.get("clinic_subsector")
    if sub_cli == "aesthetic" and lead.get("has_before_after") is False:
        fire(0.04, "Estetik + before/after yok")
    if sub_cli == "trust" and lead.get("has_doctor_profile") is False:
        fire(0.03, "Klinik + doktor profili yok")

    sub_sector = lead.get("sub_sector")
    if sub_sector in ("litigation", "corporate") and lead.get("has_legal_articles") is False:
        fire(0.03, "Avukat + içerik yok")
    if sub_sector in ("luxury", "local") and lead.get("has_property_listings") is False:
        fire(0.04, "Emlak + online ilan yok")
    if sub_sector in ("tesisat", "elektrik") and lead.get("has_call_button") is False:
        fire(0.03, f"{sub_sector} + arama butonu yok")
    if sub_sector == "tadilat" and lead.get("has_before_after") is False:
        fire(0.04, "Tadilat + öncesi-sonrası yok")

    # Cap at 15%
    boost = min(0.15, boost)
    return 1.0 + boost, signals


# --------------------------------------------------
# 6. CONFIDENCE (0.0–1.0) — 40/40/20
# --------------------------------------------------

def calc_confidence(lead: dict, audit: dict) -> float:
    """Veri bütünlüğü. Routing kararını etkiler, skoru etkilemez.

    Website yoksa o field'a bağımlı sinyaller paydadan düşülür —
    yokluğu zaten fırsat sinyali; confidence penalty olmamalı.
    """
    has_website = bool(lead.get("website"))

    # website artık CORE'da değil: site_durumu/URL'nin yokluğu negatif sinyal
    # değil, satış fırsatı. Yokluğunu iki kez cezalandırmayız.
    CORE = ["yorum_sayisi", "puan", "son_yorum_gun", "telefon"]

    # has_cta / has_online_booking sadece site olunca anlamlı.
    SITE_ONLY_ENRICH = {"has_cta", "has_online_booking"}
    ALL_ENRICH = [
        "instagram_post_90d", "review_last_30d", "has_cta",
        "has_online_booking", "has_whatsapp",
        "gmb_photo_count", "competitor_ads_count",
        "in_organic_top10",
    ]
    ENRICH = [f for f in ALL_ENRICH if has_website or f not in SITE_ONLY_ENRICH]

    # pagespeed sadece site olunca anlamlı.
    AUDIT_F = ["genel_skor", "ssl"] + (["pagespeed"] if has_website else [])

    c = sum(1 for f in CORE   if lead.get(f)  is not None) / len(CORE)
    e = sum(1 for f in ENRICH if lead.get(f)  is not None) / len(ENRICH)
    a = sum(1 for f in AUDIT_F if audit.get(f) is not None) / len(AUDIT_F)

    return round(0.40 * c + 0.40 * e + 0.20 * a, 2)


# --------------------------------------------------
# 7. ÇELİŞKİ DETEKTÖRÜ
# --------------------------------------------------

def detect_contradictions(lead: dict, audit: dict, opp: int, intent: int) -> list[str]:
    flags: list[str] = []
    yorum = lead.get("yorum_sayisi") or 0
    puan = lead.get("puan") or 0
    website = lead.get("website")
    competitor_ads = lead.get("competitor_ads_count") or 0
    gmb_photos = lead.get("gmb_photo_count")
    gmb_desc = lead.get("gmb_has_description")

    if opp > 70 and intent < 45:
        flags.append("Büyük gap var ama alıcı sinyali yok — zombie risk")

    if yorum > 80 and puan > 4.3 and not website:
        flags.append("Güçlü Maps ama website yok — scraper doğrulansın")

    if intent > 75 and opp < 25:
        flags.append("Yüksek aktivite + küçük açık — düşük değer")

    if puan > 4.7 and opp > 65:
        flags.append("Puan çok yüksek + yüksek gap — sinyal çakışması")

    if competitor_ads >= 2 and not website:
        flags.append("Rakip reklam var ama site yok — landing sorunu")

    if yorum > 50 and gmb_photos is not None and gmb_photos < 2 and gmb_desc is False:
        flags.append("Çok yorum + sıfır GMB derinliği — fake/eksik şüphesi")

    # Terk edilmiş site + ölü Maps + sosyal ölü → fırsat değil, zombie
    update_days = lead.get("last_website_update_days")
    update_conf = lead.get("website_update_confidence") or 0.0
    son_yorum   = lead.get("son_yorum_gun")
    ig_post_90  = lead.get("instagram_post_90d")
    ig_inactive = ig_post_90 is not None and ig_post_90 == 0
    maps_olu    = son_yorum is not None and son_yorum > 180

    if (update_days is not None and update_conf >= 0.4
            and update_days > 365 and maps_olu and ig_inactive):
        flags.append("Site+Maps+IG üçü de ölü — terk edilmiş şüphesi")

    return flags


# --------------------------------------------------
# 8. ROUTING
# --------------------------------------------------

def route_decision(
    final: float,
    intent: int,
    confidence: float,
    contradictions: list[str],
) -> tuple[str, str, str]:
    """Pure-score routing. Confidence sadece zombie flag'i için kullanılır,
    tek başına karar vermez (veri kalitesi ≠ fırsat yokluğu).

    Eşikler:
      HOT    → final ≥ 70
      WARM   → 55 ≤ final < 70
      REVIEW → final < 55 | zombie risk
    """
    if any("zombie" in c for c in contradictions):
        return "REVIEW", "manual_review", "Alıcı sinyali yok — zombie risk"

    if final >= 70:
        return "HOT", "generate_full_audit", "Güçlü fırsat — tam audit"

    if final >= 55:
        return "WARM", "generate_light_audit", "Orta fırsat — hafif audit"

    return "REVIEW", "manual_review", f"Sinyal zayıf — audit ile doğrula (final={final:.0f})"


# --------------------------------------------------
# 9. FINAL SCORE
# --------------------------------------------------

def calculate_final_score(
    lead: dict,
    audit: dict,
    playbook: dict,
    skip_hard_filter: bool = False,
) -> dict:
    """
    V3: Satış-öncelikli skorlama.

    final = min(100, (0.75·Opp + 0.25·Intent) × Pattern_Mul × Fit_Mul)

    Ağırlık 0.75/0.25 → dijital boşluk (fırsat) birincil sinyal.
    Satış floor'u → website yok + telefon var olan lead'ler kaçmasın.

    skip_hard_filter=True → kullanıcı lead'i seçmiş (audit / manual add).
    """
    if not skip_hard_filter:
        is_blocked, reason = hard_filter(lead, playbook)
        if is_blocked:
            return {"status": "rejected", "reason": reason}

    opp,      opp_signals  = calc_opportunity(lead, audit)
    intent,   int_signals  = calc_intent(lead, audit)
    fit_mul,  fit_signals  = calc_fit_multiplier(lead, playbook)
    pat_mul,  pat_signals  = calc_pattern_multiplier(lead, audit, playbook)
    confidence             = calc_confidence(lead, audit)

    combined = 0.75 * opp + 0.25 * intent
    final    = round(min(100.0, max(0.0, combined * pat_mul * fit_mul)), 1)

    # ── Satış floor'u: kaçan lead'i minimize et ─────────────────────────────
    # Website yok + telefon var = doğrudan satış fırsatı.
    # +40 opportunity bonusu intent/multiplier erozyonuyla 70 altına düşebiliyor.
    # Kontrollü floor ile FIRSAT bandında tutuyoruz.
    website = lead.get("website")
    telefon = lead.get("telefon")
    yorum   = lead.get("yorum_sayisi") or 0
    floor   = 0.0
    if not website and telefon:
        if yorum < 30:
            # Küçük/bilinmez firma + site yok → en temiz satış fırsatı
            floor = 70.0
        elif fit_mul >= 0.95:
            # Fit uyumu bozulmamışsa en azından güçlü ADAY bandında kalsın
            floor = 65.0
    if floor and final < floor:
        opp_signals.append(f"Satış floor'u uygulandı → {floor:.0f}")
        final = floor

    contradictions              = detect_contradictions(lead, audit, opp, intent)
    segment, action, reason_sum = route_decision(final, intent, confidence, contradictions)

    score_breakdown = list(opp_signals) + list(int_signals) + list(fit_signals) + list(pat_signals)

    return {
        "status":              "ok",
        "opportunity_score":   opp,
        "opportunity":         opp,               # legacy alias
        "intent_score":        intent,
        "buyer_intent":        intent,            # legacy alias
        "fit_multiplier":      round(fit_mul, 3),
        "pattern_multiplier":  round(pat_mul, 3),
        "pattern_boost":       round((pat_mul - 1.0) * 100, 1),  # legacy: % boost
        "confidence":          confidence,
        "data_confidence":     confidence,        # legacy alias
        "contradictions":      contradictions,
        "final_score":         final,
        "segment":             segment,
        "action":              action,
        "priority":            SEGMENT_TO_PRIORITY[segment],
        "reason_summary":      reason_sum,
        "decision_reason":     reason_sum,
        "signals": {
            "opportunity": opp_signals,
            "intent":      int_signals,
            "fit":         fit_signals,
            "pattern":     pat_signals,
        },
        "score_breakdown": score_breakdown,
        "score_layers": {
            "opportunity":        opp,
            "intent":             intent,
            "combined":           round(combined, 1),
            "fit_multiplier":     round(fit_mul, 3),
            "pattern_multiplier": round(pat_mul, 3),
            "final":              final,
        },
    }
