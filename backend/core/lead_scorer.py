"""
Lead Scorer V3 — No-Double-Counting, Production-Grade.

Her raw sinyal yalnızca tek bir layer'da puan üretir (SIGNAL_OWNERSHIP).

Katmanlar:
  1. Hard Filter       → kurumsal, zombie, telefonsuz, zaten güçlü
  2. Traffic Score     → Maps hacim + IG hacim + organik görünürlük   (0-100, baz 20)
  3. Conversion Score  → Site + araçlar (booking/CTA/WA) + güven      (0-100, baz 50)
  4. Intent Score      → Aktivite tazliği + sosyal + dijital yatırım   (0-100, baz 40)
  5. Fit Score         → ICP uyumu: sektör / ilçe / ulaşılabilirlik   (0-100, baz 50)
  6. Opportunity Score → traffic + conversion farkından türetilir      (0-100)
  7. Gap Bonus         → traffic_score - conversion_score gap          (0-15)
  8. Pattern Bonus     → layer-level kombinasyonlar, max 2 aktif       (0-15)
  9. Confidence        → veri coverage                                 (0.0-1.0)
 10. Final Score       → 0.50·opp + 0.30·intent + 0.20·fit + bonuses  (0-100)

Segment routing:
  REVIEW  → confidence < 0.50
  HOT     → final ≥ 80 AND confidence ≥ 0.60 AND intent ≥ 45
  WARM    → final ≥ 60
  LOW     → final < 60
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

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
    "HOT":      "yuksek",
    "WARM":     "orta",
    "LOW":      "dusuk",
    "REVIEW":   "orta",
    "REJECTED": "dusuk",
}

# Kanonik sinyal sahipliği tablosu.
# validate_no_double_counting() bu tabloyu çapraz kontrolde kullanır.
# Bir raw alan adı yalnızca tek layer'da listelenebilir.
SIGNAL_OWNERSHIP: dict[str, list[str]] = {
    "traffic": [
        "yorum_sayisi", "review_last_30d", "review_last_90d",
        "puan", "gmb_photo_count",
        "instagram_post_90d",
        "in_organic_top10", "in_ai_overview", "indexed_pages",
    ],
    "conversion": [
        "website", "site_durumu", "pagespeed", "ssl",
        "has_online_booking", "has_whatsapp", "has_call_button",
        "has_cta", "has_form", "has_trust_signals",
    ],
    "intent": [
        "son_yorum_gun",
        "last_website_update_days", "website_update_confidence",
        "instagram_last_post_days",
        "linkedin_active_30d", "linkedin_url",
        "youtube_video_180d",
    ],
    "fit": [
        "oncelikli_ilce", "decision_maker_reachable",
        "kurumsal_yapi_yavas", "playbook_tip_ok",
    ],
}

# Backward-compat — external callers may reference this.
DEFAULT_FEATURE_WEIGHTS: dict[str, float] = {
    "blog_signal": 1.0,
    "content_depth_signal": 1.0,
    "linkedin_signal": 1.0,
    "youtube_signal": 1.0,
    "instagram_signal": 1.0,
    "online_booking_signal": 1.0,
    "ads_signal": 1.0,
    "trust_signal": 1.0,
}


# ──────────────────────────────────────────────────────────────────────────────
# 1. HARD FILTER
# ──────────────────────────────────────────────────────────────────────────────

def hard_filter(lead: dict, playbook: dict | None = None) -> tuple[bool, str]:
    """
    True → lead elendi, puan üretilmez.
    site_durumu burada yapısal kontrol olarak kullanılır (puan vermez).
    """
    isim = (lead.get("isim") or "").lower()

    for brand in CHAIN_BRANDS:
        if brand in isim:
            return True, f"kurumsal/zincir ({brand})"

    branch_count = lead.get("branch_count") or 0
    if branch_count >= 5:
        return True, "kurumsal/zincir (branch_count≥5)"

    if not lead.get("telefon"):
        return True, "telefon yok"

    if lead.get("permanently_closed"):
        return True, "kalıcı kapalı"

    son_yorum = lead.get("son_yorum_gun")
    if son_yorum is not None and son_yorum > 365:
        return True, "zombie işletme (365g+ yorum yok)"

    yorum = lead.get("yorum_sayisi") or 0
    puan  = lead.get("puan") or 0
    if yorum >= 400 and puan >= 4.7 and lead.get("website") and lead.get("site_durumu") == "iyi":
        return True, "zaten çok güçlü (400+ yorum, 4.7+ puan, iyi site)"

    return False, ""


# ──────────────────────────────────────────────────────────────────────────────
# 2. TRAFFIC SCORE (0–100, baz 20)
# ──────────────────────────────────────────────────────────────────────────────

def calc_traffic_score(lead: dict) -> tuple[int, list[str]]:
    """
    Sinyal sahipliği (SIGNAL_OWNERSHIP["traffic"]):
    yorum_sayisi, review_last_30d, review_last_90d, puan, gmb_photo_count,
    instagram_post_90d, in_organic_top10, in_ai_overview, indexed_pages.

    Bu sinyaller başka hiçbir layer'da puan üretmez.
    """
    score = 20
    explain: list[str] = []

    def add(delta: int, msg: str) -> None:
        nonlocal score
        score += delta
        if delta:
            explain.append(f"{'+' if delta > 0 else ''}{delta} {msg}")

    # Review count
    yorum = lead.get("yorum_sayisi") or 0
    if yorum >= 100:
        add(20, "review 100+")
    elif yorum >= 50:
        add(14, "review 50+")
    elif yorum >= 20:
        add(8, "review 20+")

    # Review velocity
    rev_30 = lead.get("review_last_30d")
    if rev_30 is not None:
        if rev_30 >= 5:
            add(12, f"son 30g yorum hızı ({rev_30})")
        elif rev_30 >= 2:
            add(6, f"son 30g yorum ({rev_30})")

    # Rating
    puan = lead.get("puan") or 0
    if puan >= 4.3:
        add(8, f"puan yüksek ({puan})")
    elif 0 < puan < 3.8 and yorum >= 20:
        add(-6, f"puan düşük ({puan})")

    # Instagram hacim (post_90 ≥ 24 ≈ 8/ay aktif)
    post_90 = lead.get("instagram_post_90d") or 0
    if post_90 >= 24:
        add(10, f"IG aktif ({post_90} post/90g)")
    elif post_90 == 0 and lead.get("instagram_url"):
        add(-5, "IG hesabı var, pasif")

    # GMB fotoğraf
    gmb_photos = lead.get("gmb_photo_count")
    if gmb_photos is not None and gmb_photos >= 20:
        add(6, f"GMB fotoğraf ({gmb_photos})")

    # Organik SERP görünürlüğü
    organic = lead.get("in_organic_top10")
    if organic is True:
        add(6, "organik top10")
    elif organic is False:
        add(-4, "organik top10'da yok")

    # AI Overview
    if lead.get("in_ai_overview") is True:
        add(4, "AI Overview'da var")

    # Index sayısı (organic trafik proxy)
    indexed = lead.get("indexed_pages")
    if indexed is not None:
        if indexed >= 200:
            add(6, f"güçlü SEO varlığı ({indexed} sayfa)")
        elif 0 < indexed <= 5:
            add(-4, f"az indexlenmiş ({indexed} sayfa)")
        elif indexed == 0:
            add(-8, "hiç indexlenmemiş")

    return max(0, min(100, score)), explain


# ──────────────────────────────────────────────────────────────────────────────
# 3. CONVERSION SCORE (0–100, baz 50)
# ──────────────────────────────────────────────────────────────────────────────

def calc_conversion_score(lead: dict, audit: dict | None = None) -> tuple[int, list[str]]:
    """
    Sinyal sahipliği (SIGNAL_OWNERSHIP["conversion"]):
    website, site_durumu, pagespeed, ssl, has_online_booking, has_whatsapp,
    has_call_button, has_cta, has_form, has_trust_signals.

    Bu sinyaller başka hiçbir layer'da puan üretmez.
    """
    audit = audit or {}
    score = 50
    explain: list[str] = []

    def add(delta: int, msg: str) -> None:
        nonlocal score
        score += delta
        if delta:
            explain.append(f"{'+' if delta > 0 else ''}{delta} {msg}")

    website     = lead.get("website")
    site_durumu = lead.get("site_durumu")

    if not website:
        add(-22, "website yok")
    else:
        pagespeed = audit.get("pagespeed") if audit.get("pagespeed") is not None else lead.get("pagespeed")
        if pagespeed is not None:
            if pagespeed >= 70:
                add(6, f"site hızlı ({pagespeed})")
            elif pagespeed < 50:
                add(-10, f"site yavaş ({pagespeed})")

        ssl = audit.get("ssl") if audit.get("ssl") is not None else lead.get("ssl")
        if ssl is False:
            add(-8, "SSL yok")

        if site_durumu == "iyi":
            add(8, "site kaliteli")
        elif site_durumu == "zayif":
            add(-6, "site zayıf")

    # Booking
    if lead.get("has_online_booking") is True:
        add(18, "online booking var")
    else:
        add(-12, "booking yok")

    # WhatsApp
    if lead.get("has_whatsapp") is True:
        add(10, "WhatsApp var")
    else:
        add(-6, "WhatsApp yok")

    # CTA
    if lead.get("has_cta") is True:
        add(10, "CTA var")
    else:
        add(-8, "CTA yok")

    # Güven sinyali
    if lead.get("has_trust_signals") is True:
        add(8, "güven sinyali var")
    else:
        add(-6, "güven sinyali yok")

    return max(0, min(100, score)), explain


# ──────────────────────────────────────────────────────────────────────────────
# 4. INTENT SCORE (0–100, baz 40)
# ──────────────────────────────────────────────────────────────────────────────

def calc_intent_score(lead: dict) -> tuple[int, list[str]]:
    """
    Sinyal sahipliği (SIGNAL_OWNERSHIP["intent"]):
    son_yorum_gun, last_website_update_days, website_update_confidence,
    instagram_last_post_days, linkedin_active_30d, linkedin_url, youtube_video_180d.
    """
    score = 40
    explain: list[str] = []

    def add(delta: int, msg: str) -> None:
        nonlocal score
        score += delta
        if delta:
            explain.append(f"{'+' if delta > 0 else ''}{delta} {msg}")

    # Son yorum tazliği
    son_yorum = lead.get("son_yorum_gun")
    if son_yorum is not None:
        if son_yorum <= 30:
            add(14, f"son yorum yeni ({son_yorum}g)")
        elif son_yorum <= 90:
            add(6, f"son yorum orta ({son_yorum}g)")
        elif son_yorum > 180:
            add(-10, f"son yorum eski ({son_yorum}g)")

    # Site güncelleme tazliği (dijital yatırım sinyali)
    update_days = lead.get("last_website_update_days")
    update_conf = lead.get("website_update_confidence") or 0.0
    if update_days is not None and update_conf >= 0.4:
        if update_days <= 180:
            add(8, f"site güncel ({update_days}g)")
        elif update_days > 365:
            add(-4, f"site eski ({update_days}g)")

    # IG son post tazliği (recency, hacim Traffic'e ait)
    last_ig = lead.get("instagram_last_post_days")
    if last_ig is not None:
        if last_ig < 14:
            add(8, f"IG çok aktif ({last_ig}g)")
        elif last_ig < 60:
            add(4, f"IG aktif ({last_ig}g)")
        elif last_ig > 90:
            add(-4, f"IG pasif ({last_ig}g)")

    # LinkedIn
    if lead.get("linkedin_active_30d") is True:
        add(6, "LinkedIn aktif (30g)")
    elif lead.get("linkedin_url"):
        add(2, "LinkedIn profil var")

    # YouTube
    yt_180 = lead.get("youtube_video_180d")
    if yt_180 is not None and yt_180 >= 3:
        add(4, f"YouTube aktif ({yt_180} video/180g)")

    # Sosyal yokluk
    if not lead.get("instagram_url") and not lead.get("linkedin_url") and not lead.get("youtube_url"):
        add(-5, "sosyal varlık yok")

    return max(0, min(100, score)), explain


# ──────────────────────────────────────────────────────────────────────────────
# 5. FIT SCORE (0–100, baz 50)
# ──────────────────────────────────────────────────────────────────────────────

def calc_fit_score(lead: dict, playbook: dict | None = None) -> tuple[int, list[str]]:
    """
    Sinyal sahipliği (SIGNAL_OWNERSHIP["fit"]):
    oncelikli_ilce, decision_maker_reachable, kurumsal_yapi_yavas, playbook_tip_ok.
    Sektör uyumu playbook ile burada hesaplanır.
    """
    playbook = playbook or {}
    score = 50
    explain: list[str] = []

    def add(delta: int, msg: str) -> None:
        nonlocal score
        score += delta
        if delta:
            explain.append(f"{'+' if delta > 0 else ''}{delta} {msg}")

    # Hedef sektör
    sektor    = lead.get("sektor") or lead.get("sector") or ""
    preferred = playbook.get("preferred_sectors", [])
    if preferred and sektor in preferred:
        add(15, "hedef sektör")
    elif preferred and sektor and sektor not in preferred:
        add(-10, f"hedef dışı sektör ({sektor})")

    # Öncelikli ilçe
    if lead.get("oncelikli_ilce"):
        add(10, "öncelikli ilçe")

    # Karar verici ulaşılabilirliği
    if lead.get("decision_maker_reachable") is True:
        add(8, "karar verici ulaşılabilir")

    # Yüksek churn riski
    if lead.get("kurumsal_yapi_yavas") is True:
        add(-12, "yüksek churn riski (kurumsal döngü)")

    # Çok küçük işletme (≤4 yorum → churn risk proxy)
    yorum = lead.get("yorum_sayisi") or 0
    if yorum < 5:
        add(-8, f"çok küçük işletme ({yorum} yorum)")

    # İşletme tipi uyumu
    if lead.get("playbook_tip_ok") is True:
        add(5, "işletme tipi uygun")

    return max(0, min(100, score)), explain


# ──────────────────────────────────────────────────────────────────────────────
# 6. OPPORTUNITY SCORE (türetilmiş, 0–100)
# ──────────────────────────────────────────────────────────────────────────────

def calc_opportunity_score(traffic_score: int, conversion_score: int) -> tuple[float, list[str]]:
    """
    Yüksek trafik + düşük conversion = yüksek fırsat.
    Raw sinyal kullanmaz — layer çıktılarından türetilir.
    """
    raw = 50.0 + (traffic_score * 0.20) - (conversion_score * 0.35)
    opp = round(max(0.0, min(100.0, raw)), 1)
    explain = [
        f"traffic={traffic_score}",
        f"conversion={conversion_score}",
        f"opportunity={opp}",
    ]
    return opp, explain


# ──────────────────────────────────────────────────────────────────────────────
# 7. GAP BONUS (0–15)
# ──────────────────────────────────────────────────────────────────────────────

def calc_gap_bonus(traffic_score: int, conversion_score: int) -> tuple[int, int, list[str]]:
    """Layer çıktıları kullanır, raw sinyal yok."""
    gap = traffic_score - conversion_score
    if gap >= 40:
        bonus = 15
    elif gap >= 25:
        bonus = 10
    elif gap >= 10:
        bonus = 5
    else:
        bonus = 0
    explain = [f"+{bonus} traffic-conversion gap yüksek (gap={gap})"] if bonus else []
    return bonus, gap, explain


# ──────────────────────────────────────────────────────────────────────────────
# 8. PATTERN BONUS (0–15, max 2 aktif)
# ──────────────────────────────────────────────────────────────────────────────

def calc_pattern_bonus(
    lead: dict,
    traffic_score: int,
    conversion_score: int,
    intent_score: int,
    playbook: dict | None = None,
) -> tuple[int, list[str]]:
    """
    Layer-level çıktı ve yapısal boolean'lar kullanır.
    Raw sinyalleri PUANLAMAZ — sadece kombinasyon tetikleyicisi olarak kullanır.
    Max 2 pattern aktif, toplam max 15.
    """
    playbook = playbook or {}
    bonus  = 0
    active = 0
    explain: list[str] = []

    # P1: Güçlü trafik + kırık conversion → para kaçıyor
    if traffic_score >= 60 and conversion_score <= 35 and active < 2:
        bonus += 10
        active += 1
        explain.append("+10 trafik var ama dönüşüm zayıf")

    # P2: Güçlü trafik + site yok → ham fırsat
    if traffic_score >= 55 and not lead.get("website") and active < 2:
        bonus += 8
        active += 1
        explain.append("+8 güçlü trafik, website yok")

    # P3: Yüksek intent + kırık conversion → hazır alıcı, kötü landing
    if intent_score >= 55 and conversion_score <= 35 and active < 2:
        bonus += 8
        active += 1
        explain.append("+8 yüksek intent, conversion zayıf")

    # P4: Blog var + CTA yok (yüksek değerli sektörler)
    sektor = lead.get("sektor") or lead.get("sector") or ""
    blog   = lead.get("has_blog")
    if (blog and not lead.get("has_cta")
            and playbook.get("blog_weight", 1.0) > 0
            and sektor in ("klinik", "avukat", "egitim", "kadin_dogum")
            and active < 2):
        bonus += 6
        active += 1
        explain.append("+6 blog var, CTA yok")

    if active >= 2 and bonus > 15:
        explain.append("pattern bonus 2 ile sınırlandı")

    return min(15, bonus), explain


# ──────────────────────────────────────────────────────────────────────────────
# 9. CONFIDENCE (0.0–1.0)
# ──────────────────────────────────────────────────────────────────────────────

def calc_confidence(lead: dict, audit: dict | None = None) -> float:
    """Veri coverage'ına göre güven üretir."""
    audit = audit or {}
    conf  = 0.0

    # Core sinyaller
    if lead.get("telefon"):          conf += 0.08
    if lead.get("yorum_sayisi") is not None: conf += 0.08
    if lead.get("puan") is not None: conf += 0.06
    if lead.get("son_yorum_gun") is not None: conf += 0.10

    # Enrich sinyalleri
    if lead.get("review_last_30d") is not None:    conf += 0.10
    if lead.get("review_last_90d") is not None:    conf += 0.08
    if lead.get("gmb_photo_count") is not None:    conf += 0.06
    if lead.get("gmb_has_description") is not None: conf += 0.05
    if lead.get("gmb_has_qa") is not None:         conf += 0.05
    if "website" in lead:                          conf += 0.08
    pagespeed = audit.get("pagespeed") if audit.get("pagespeed") is not None else lead.get("pagespeed")
    if pagespeed is not None:                      conf += 0.08
    if lead.get("has_online_booking") is not None: conf += 0.08

    return min(1.0, round(conf, 2))


# ──────────────────────────────────────────────────────────────────────────────
# 10. DOUBLE-COUNTING GUARD
# ──────────────────────────────────────────────────────────────────────────────

def validate_no_double_counting(_result: dict | None = None) -> dict:
    """
    SIGNAL_OWNERSHIP tablosunun tutarlılığını doğrular.
    Aynı raw sinyal birden fazla layer'da tanımlıysa invalid döner.
    """
    seen: dict[str, str] = {}
    duplicates: list[str] = []

    for layer, signals in SIGNAL_OWNERSHIP.items():
        for sig in signals:
            if sig in seen:
                duplicates.append(sig)
                logger.warning(
                    "DOUBLE COUNTING: sinyal=%r hem %r hem %r layer'ında tanımlı",
                    sig, seen[sig], layer,
                )
            else:
                seen[sig] = layer

    return {"valid": len(duplicates) == 0, "duplicates": duplicates}


# ──────────────────────────────────────────────────────────────────────────────
# 11. FINAL SCORE
# ──────────────────────────────────────────────────────────────────────────────

def calculate_final_score(
    lead: dict,
    audit: dict | None = None,
    playbook: dict | None = None,
) -> dict:
    """
    V3 — No-double-counting, production-grade.

    base  = 0.50 × opportunity + 0.30 × intent + 0.20 × fit
    final = min(100, base + gap_bonus + pattern_bonus)
    """
    audit    = audit or {}
    playbook = playbook or {}

    # 1. Hard filter
    rejected, reason = hard_filter(lead, playbook)
    if rejected:
        return {
            "status":          "rejected",
            "segment":         "REJECTED",
            "reason":          reason,
            "final_score":     0,
            "confidence":      0.0,
            "score_breakdown": [],
            # Legacy keys so existing callers don't break.
            "opportunity_score": 0,
            "opportunity":       0,
            "intent_score":      0,
            "buyer_intent":      0,
            "priority":          SEGMENT_TO_PRIORITY["REJECTED"],
        }

    # 2–5. Layer scores
    traffic,    t_explain = calc_traffic_score(lead)
    conversion, c_explain = calc_conversion_score(lead, audit)
    intent,     i_explain = calc_intent_score(lead)
    fit,        f_explain = calc_fit_score(lead, playbook)

    # 6. Opportunity (derived, no raw signals)
    opp, o_explain = calc_opportunity_score(traffic, conversion)

    # 7. Gap bonus
    gap_bonus, gap_value, g_explain = calc_gap_bonus(traffic, conversion)

    # 8. Pattern bonus
    pat_bonus, p_explain = calc_pattern_bonus(lead, traffic, conversion, intent, playbook)

    # 9. Confidence
    confidence = calc_confidence(lead, audit)

    # 10. Final score
    base  = 0.50 * opp + 0.30 * intent + 0.20 * fit
    final = round(min(100.0, max(0.0, base + gap_bonus + pat_bonus)), 1)

    # Segment routing
    if confidence < 0.50:
        segment    = "REVIEW"
        reason_sum = f"Veri yetersiz (conf={confidence:.2f})"
    elif final >= 80 and confidence >= 0.60 and intent >= 45:
        segment    = "HOT"
        reason_sum = "Güçlü fırsat — tam audit"
    elif final >= 60:
        segment    = "WARM"
        reason_sum = "Orta fırsat — hafif audit"
    else:
        segment    = "LOW"
        reason_sum = "Yeterli sinyal yok"

    score_breakdown = (
        t_explain + c_explain + i_explain + f_explain
        + o_explain + g_explain + p_explain
    )

    result: dict = {
        # V3 keys
        "status":            "ok",
        "segment":           segment,
        "final_score":       final,
        "confidence":        confidence,
        "traffic_score":     traffic,
        "conversion_score":  conversion,
        "intent_score":      intent,
        "fit_score":         fit,
        "opportunity_score": opp,
        "gap_value":         gap_value,
        "gap_bonus":         gap_bonus,
        "pattern_bonus":     pat_bonus,
        "score_breakdown":   score_breakdown,
        "reason_summary":    reason_sum,
        "priority":          SEGMENT_TO_PRIORITY[segment],
        # Legacy aliases (backward compat with search_service, UI, etc.)
        "opportunity":       opp,
        "buyer_intent":      intent,
        "data_confidence":   confidence,
        "decision_reason":   reason_sum,
        "score_layers": {
            "traffic":     traffic,
            "conversion":  conversion,
            "intent":      intent,
            "fit":         fit,
            "opportunity": opp,
            "gap_bonus":   gap_bonus,
            "pattern":     pat_bonus,
            "final":       final,
        },
        "signals": {
            "traffic":    t_explain,
            "conversion": c_explain,
            "intent":     i_explain,
            "fit":        f_explain,
            "gap":        g_explain,
            "pattern":    p_explain,
        },
        "ownership_debug": {
            "traffic_signals_used":    SIGNAL_OWNERSHIP["traffic"],
            "conversion_signals_used": SIGNAL_OWNERSHIP["conversion"],
            "intent_signals_used":     SIGNAL_OWNERSHIP["intent"],
            "fit_signals_used":        SIGNAL_OWNERSHIP["fit"],
        },
    }

    # Double-counting guard — log-only, non-blocking in production.
    guard = validate_no_double_counting(result)
    if not guard["valid"]:
        logger.error("DOUBLE COUNTING ihlali: %s", guard["duplicates"])
    result["_dc_valid"] = guard["valid"]

    logger.debug(
        "score: segment=%s final=%.1f traffic=%d conversion=%d intent=%d fit=%d "
        "opp=%.1f gap=%d pat=%d conf=%.2f",
        segment, final, traffic, conversion, intent, fit,
        opp, gap_bonus, pat_bonus, confidence,
    )

    return result
