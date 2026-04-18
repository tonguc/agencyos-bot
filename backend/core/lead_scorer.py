"""
Lead Scorer — 3-layer scoring pipeline.

Layer 1: Hard Filter  (eleme)
Layer 2: Opportunity  (problemin büyüklüğü)
Layer 3: Buyer Intent (satın alma ihtimali)

Tüm sinyal ağırlıkları playbook["feature_weights"] üzerinden gelir.
weight = 0.0 → sinyal tamamen kapalı
weight < 1.0 → etki azaltılmış
weight = 1.0 → tam etki
weight > 1.0 → sektörde ekstra kritik sinyal
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)

CHANNEL_FIELDS = [
    "instagram_post_90d", "instagram_last_post_days",
    "youtube_video_180d", "youtube_last_video_days",
    "linkedin_url", "linkedin_active_30d", "linkedin_followers",
    "market_ads_pressure", "competitor_ads_count", "self_ads_visible",
    "gmb_photo_count", "gmb_last_photo_days", "gmb_has_description", "gmb_has_qa",
    "has_cta", "has_whatsapp", "has_online_booking",
    "has_blog", "last_blog_days",
    "has_service_pages", "has_faq", "has_about_depth",
    # Clinic aesthetic signals
    "has_before_after", "has_visual_gallery",
    # Clinic trust signals
    "has_doctor_profile",
    # Lawyer signals
    "has_legal_articles", "has_practice_areas", "has_case_examples",
    "has_contact_clear", "has_linkedin_profile",
    # Review velocity
    "review_last_30d", "review_last_90d",
    # Update detection
    "last_website_update_days", "website_update_confidence",
]

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

SEGMENT_TO_PRIORITY = {
    "HOT": "yuksek",
    "WARM": "yuksek",
    "OK": "orta",
    "LOW": "dusuk",
}


def _fw(playbook: dict) -> dict:
    """Playbook'tan feature_weights oku, eksikleri default ile doldur."""
    w = DEFAULT_FEATURE_WEIGHTS.copy()
    w.update(playbook.get("feature_weights", {}))
    return {k: float(v) for k, v in w.items()}


# --------------------------------------------------
# 1. HARD FILTER
# --------------------------------------------------

def hard_filter(lead: dict, playbook: dict) -> Tuple[bool, str]:
    """
    Return:
    (True, reason) → ELENDİ
    (False, "")    → DEVAM
    """
    isim = (lead.get("isim") or "").lower()
    yorum = lead.get("yorum_sayisi") or 0
    telefon = lead.get("telefon")
    son_yorum = lead.get("son_yorum_gun")

    if any(x in isim for x in ["hastane", "devlet", "group", "merkez"]):
        return True, "kurumsal / zincir"

    puan = lead.get("puan") or 0
    website = lead.get("website")
    if yorum > 150 and puan > 4.5 and website:
        return True, "zaten güçlü"

    if not telefon:
        return True, "telefon yok"

    if son_yorum is not None and son_yorum > 365:
        return True, "ölü profil"

    return False, ""


# --------------------------------------------------
# 2. OPPORTUNITY SCORE (0–100)
# --------------------------------------------------

def calc_opportunity(lead: dict, audit: dict, playbook: dict) -> tuple[int, list[str]]:
    """Returns (score, signals). Each signal entry: 'Label → +N'."""
    score = 40
    signals: list[str] = []
    fw = _fw(playbook)
    sub = lead.get("clinic_subsector")

    def add(delta: int, label: str) -> None:
        nonlocal score
        score += delta
        if delta != 0:
            signals.append(f"{label} → {'+' if delta > 0 else ''}{delta}")

    # ── Google Maps / Temel veriler ──────────────────
    yorum = lead.get("yorum_sayisi") or 0
    puan = lead.get("puan") or 0
    website = lead.get("website")
    site_durumu = lead.get("site_durumu")
    telefon = lead.get("telefon")
    son_yorum = lead.get("son_yorum_gun")

    if yorum < 10:
        add(15, f"Yorum az ({yorum})")
    elif yorum < 30:
        add(8, f"Yorum orta ({yorum})")
    elif yorum > 100:
        add(-8, f"Yorum çok ({yorum})")

    if 3.8 <= puan <= 4.1:
        add(10, f"Puan orta ({puan})")
    elif puan < 3.8:
        add(5, f"Puan düşük ({puan})")
    elif puan > 4.6:
        add(-10, f"Puan yüksek ({puan})")

    if not website:
        add(20, "Website yok")
    elif site_durumu == "zayif":
        add(10, "Site zayıf")
    elif site_durumu == "iyi":
        add(-5, "Site iyi")

    if not telefon:
        add(-20, "Telefon yok")

    if son_yorum is not None:
        if son_yorum < 30:
            add(5, f"Son yorum yakın ({son_yorum}g)")
        elif son_yorum > 180:
            add(-8, f"Son yorum eski ({son_yorum}g)")

    # ── Audit verileri ───────────────────────────────
    audit_skor = audit.get("genel_skor", 50)
    pagespeed = audit.get("pagespeed", 60)
    ssl = audit.get("ssl", True)

    if audit_skor < 35:
        add(15, f"Audit çok zayıf ({audit_skor})")
    elif audit_skor < 55:
        add(8, f"Audit zayıf ({audit_skor})")
    elif audit_skor > 75:
        add(-10, f"Audit güçlü ({audit_skor})")

    if pagespeed < 40:
        add(10, f"PageSpeed çok yavaş ({pagespeed})")
    elif pagespeed < 60:
        add(5, f"PageSpeed yavaş ({pagespeed})")
    elif pagespeed > 85:
        add(-5, f"PageSpeed hızlı ({pagespeed})")

    if not ssl:
        add(8, "SSL yok")

    # ── Google Ads pressure ──────────────────────────
    ads_w = fw["ads_signal"]
    ads_pressure = lead.get("market_ads_pressure")
    competitor_ads_count = lead.get("competitor_ads_count")
    self_ads_visible = lead.get("self_ads_visible")

    if ads_w > 0:
        if ads_pressure is True:
            add(round(4 * ads_w), "Ads pressure var")
        if competitor_ads_count is not None:
            if competitor_ads_count >= 3:
                add(round(4 * ads_w), f"Rakip reklam: {competitor_ads_count}")
            elif competitor_ads_count >= 1:
                add(round(2 * ads_w), f"Rakip reklam: {competitor_ads_count}")
        if ads_pressure is True and self_ads_visible is False:
            add(round(4 * ads_w), "Rakip var, self yok → açık")
        elif self_ads_visible is True:
            add(-3, "Self ads görünüyor")

    # ── GMB derinliği ────────────────────────────────
    photo_count = lead.get("gmb_photo_count")
    last_photo = lead.get("gmb_last_photo_days")

    if photo_count is not None:
        if photo_count < 5:
            add(6, f"GMB fotoğraf az ({photo_count})")
        elif photo_count < 15:
            add(3, f"GMB fotoğraf orta ({photo_count})")
    if last_photo is not None and last_photo > 90:
        add(4, f"GMB son fotoğraf eski ({last_photo}g)")
    if lead.get("gmb_has_description") is False:
        add(4, "GMB açıklama yok")
    if lead.get("gmb_has_qa") is False:
        add(3, "GMB Q&A yok")

    # ── Website conversion gap (sadece website varsa) ─
    if website:
        if lead.get("has_cta") is False:
            add(8, "CTA yok")
        if lead.get("has_whatsapp") is False:
            add(5, "WhatsApp yok")

        booking_w = fw["online_booking_signal"]
        if booking_w > 0 and lead.get("has_online_booking") is False:
            add(round(10 * booking_w), "Online booking yok")

        blog_w = fw["blog_signal"]
        if blog_w > 0:
            if lead.get("has_blog") is False:
                add(round(6 * blog_w), "Blog yok")
            elif lead.get("last_blog_days") is not None and lead["last_blog_days"] > 120:
                add(round(8 * blog_w), f"Blog eski ({lead['last_blog_days']}g)")

        cd_w = fw["content_depth_signal"]
        if cd_w > 0:
            if lead.get("has_service_pages") is False:
                add(round(5 * cd_w), "Servis sayfası yok")
            if lead.get("has_faq") is False:
                add(round(3 * cd_w), "SSS yok")
            if lead.get("has_about_depth") is False:
                add(round(4 * cd_w), "Hakkında derinliği yok")

    # ── Website güncellik ────────────────────────────
    update_days = lead.get("last_website_update_days")
    update_conf = lead.get("website_update_confidence") or 0.0
    if update_days is not None and update_conf >= 0.3 and update_days > 180:
        add(4, f"Site eski ({update_days}g, conf={update_conf:.1f})")

    # ── Clinic subsector sinyalleri ──────────────────
    if sub == "aesthetic":
        # Görsel içerik eksikliği estetik hastası için deal-breaker
        if lead.get("has_before_after") is False:
            add(10, "Before/after yok (estetik)")
        if lead.get("has_visual_gallery") is False:
            add(5, "Görsel galeri yok (estetik)")

    elif sub == "trust":
        # Otorite içeriği eksikliği güven kırıcı
        trust_w = fw.get("trust_signal", 1.0)
        if trust_w > 0 and lead.get("has_doctor_profile") is False:
            add(round(8 * trust_w), "Doktor profili yok (güven)")

    # "general" için mevcut GMB + pagespeed sinyalleri yeterli

    # ── Lawyer subsector sinyalleri ──────────────────
    sub_sector = lead.get("sub_sector")

    if sub_sector == "litigation":
        if lead.get("has_legal_articles") is False:
            add(8, "Hukuki içerik yok (dava)")
        if lead.get("has_practice_areas") is False:
            add(6, "Uzmanlık alanları yok (dava)")
        if lead.get("has_case_examples") is False:
            add(6, "Dava örnekleri yok (dava)")
        if lead.get("has_contact_clear") is False:
            add(6, "İletişim belirsiz (dava)")

    elif sub_sector == "corporate":
        if lead.get("has_linkedin_profile") is False:
            add(8, "LinkedIn profil yok (kurumsal)")
        if lead.get("has_practice_areas") is False:
            add(6, "Uzmanlık alanları yok (kurumsal)")
        if lead.get("has_contact_clear") is False:
            add(6, "İletişim belirsiz (kurumsal)")

    return max(0, min(score, 100)), signals


# --------------------------------------------------
# 3. BUYER INTENT SCORE (0–100)
# --------------------------------------------------

def calc_buyer_intent(lead: dict, audit: dict, playbook: dict) -> tuple[int, list[str]]:
    """Returns (score, signals)."""
    score = 50
    signals: list[str] = []
    fw = _fw(playbook)
    sub = lead.get("clinic_subsector")

    def add(delta: int, label: str) -> None:
        nonlocal score
        score += delta
        if delta != 0:
            signals.append(f"{label} → {'+' if delta > 0 else ''}{delta}")

    # ── Google Maps aktivitesi ───────────────────────
    son_yorum = lead.get("son_yorum_gun")
    if son_yorum is not None:
        if son_yorum < 30:
            add(15, f"Son yorum yakın ({son_yorum}g)")
        elif son_yorum < 90:
            add(8, f"Son yorum orta ({son_yorum}g)")
        elif son_yorum > 180:
            add(-15, f"Son yorum eski ({son_yorum}g)")

    # ── Erişilebilirlik ──────────────────────────────
    if lead.get("telefon"):
        add(10, "Telefon var")
    if lead.get("website"):
        add(5, "Website var")

    # ── Rakip reklam sinyali (audit) ─────────────────
    rakip = audit.get("reklam_firsati", {}).get("rakip_durum", "")
    if rakip == "aktif":
        add(10, "Rakip reklam aktif")

    if lead.get("oncelikli_ilce"):
        add(8, "Öncelikli ilçe")

    # ── Instagram ────────────────────────────────────
    ig_w = fw["instagram_signal"]
    post_90 = lead.get("instagram_post_90d")
    last_post_days = lead.get("instagram_last_post_days")

    if ig_w > 0 and post_90 is not None:
        if post_90 == 0:
            add(round(-6 * ig_w), f"Instagram 90g post: {post_90}")
        elif post_90 <= 3:
            add(round(-2 * ig_w), f"Instagram 90g post: {post_90}")
        elif post_90 <= 10:
            add(round(4 * ig_w), f"Instagram 90g post: {post_90}")
        else:
            add(round(6 * ig_w), f"Instagram 90g post: {post_90}")

    if ig_w > 0 and last_post_days is not None:
        if last_post_days < 14:
            add(round(4 * ig_w), f"Instagram son post: {last_post_days}g")
        elif last_post_days < 60:
            add(round(2 * ig_w), f"Instagram son post: {last_post_days}g")
        elif last_post_days > 60:
            add(round(-4 * ig_w), f"Instagram son post: {last_post_days}g")

    # ── YouTube ──────────────────────────────────────
    yt_w = fw["youtube_signal"]
    yt_180 = lead.get("youtube_video_180d")
    yt_last_days = lead.get("youtube_last_video_days")

    if yt_w > 0 and yt_180 is not None:
        if yt_180 == 0:
            pass  # yoksa ceza yok
        elif yt_180 <= 2:
            add(round(1 * yt_w), f"YouTube 180g video: {yt_180}")
        elif yt_180 <= 6:
            add(round(3 * yt_w), f"YouTube 180g video: {yt_180}")
        else:
            add(round(4 * yt_w), f"YouTube 180g video: {yt_180}")

    if yt_w > 0 and yt_last_days is not None:
        if yt_last_days < 30:
            add(round(2 * yt_w), f"YouTube son video: {yt_last_days}g")
        elif yt_last_days < 90:
            add(round(1 * yt_w), f"YouTube son video: {yt_last_days}g")

    # ── LinkedIn ─────────────────────────────────────
    li_w = fw["linkedin_signal"]
    if li_w > 0:
        if lead.get("linkedin_active_30d") is True:
            add(round(10 * li_w), "LinkedIn aktif (30g)")
        elif lead.get("linkedin_url"):
            add(round(2 * li_w), "LinkedIn profil var")

    # ── Review velocity ──────────────────────────────
    rev_30 = lead.get("review_last_30d")
    rev_90 = lead.get("review_last_90d")

    if rev_30 is not None:
        if rev_30 >= 5:
            add(12, f"Son 30g yorum: {rev_30}")
        elif rev_30 >= 2:
            add(6, f"Son 30g yorum: {rev_30}")
    if rev_90 is not None and rev_90 >= 10:
        add(8, f"Son 90g yorum: {rev_90}")

    # ── Website güncellik ────────────────────────────
    update_days = lead.get("last_website_update_days")
    update_conf = lead.get("website_update_confidence") or 0.0
    if update_days is not None and update_conf > 0.5:
        if update_days < 30:
            add(8, f"Site çok güncel ({update_days}g)")
        elif update_days < 90:
            add(4, f"Site güncel ({update_days}g)")
        elif update_days > 365:
            add(-4, f"Site terk edilmiş ({update_days}g)")

    # ── Clinic subsector intent sinyalleri ───────────
    if sub == "aesthetic":
        # Estetik hasta Instagram'dan karar veriyor — düşük aktiflik = düşük intent
        ig_followers = lead.get("instagram_followers")
        if ig_followers is not None and ig_followers < 500:
            add(-5, f"Instagram takipçi az ({ig_followers}, estetik)")

    elif sub == "trust":
        # Güven segmenti için son yorum puanı extra kritik
        puan = lead.get("puan") or 0
        if 3.0 <= puan < 3.8:
            add(8, f"Puan kritik aralık ({puan}, güven segmenti)")

    # ── Lawyer subsector intent sinyalleri ───────────
    sub_sector = lead.get("sub_sector")
    if sub_sector in ("litigation", "corporate"):
        li_w = fw["linkedin_signal"]
        # has_linkedin_profile boolean flag (avukat için ek kontrol)
        if lead.get("has_linkedin_profile") is True and not lead.get("linkedin_url"):
            add(round(4 * li_w), "LinkedIn profil var (avukat)")
        elif lead.get("has_linkedin_profile") is False and not lead.get("linkedin_url"):
            add(round(-4 * li_w), "LinkedIn yok (avukat)")
        # Review velocity extra boost for lawyers (danışman güveni için kritik)
        if rev_30 is not None and 3 <= rev_30 < 5:
            add(2, f"Avukat yorum hız bonusu ({rev_30}/30g)")

    return max(0, min(score, 100)), signals


# --------------------------------------------------
# 4. FINAL SCORE
# --------------------------------------------------

def calculate_final_score(lead: dict, audit: dict, playbook: dict) -> dict:
    """Full scoring pipeline. audit can be {} at scrape time."""
    is_blocked, reason = hard_filter(lead, playbook)
    if is_blocked:
        return {"status": "rejected", "reason": reason}

    opportunity, opp_signals = calc_opportunity(lead, audit, playbook)
    intent, intent_signals = calc_buyer_intent(lead, audit, playbook)

    def _sum(signals: list[str], keywords: list[str]) -> float:
        total = 0.0
        for s in signals:
            if any(k in s for k in keywords):
                try:
                    total += float(s.split("→")[-1].strip().replace("+", ""))
                except ValueError:
                    pass
        return total

    score_breakdown = {
        "maps":       _sum(opp_signals, ["Yorum", "Puan", "Son yorum", "GMB"]),
        "audit":      _sum(opp_signals, ["Audit", "PageSpeed", "SSL"]),
        "conversion": _sum(opp_signals, ["CTA", "WhatsApp", "booking", "Blog", "Website yok", "Site", "Servis", "SSS", "Hakkında", "Before", "Görsel", "Doktor"]),
        "ads":        _sum(opp_signals, ["Ads", "Rakip reklam", "Self ads"]),
        "social":     _sum(intent_signals, ["Instagram", "YouTube", "LinkedIn"]),
        "intent":     _sum(intent_signals, ["Telefon", "yorum", "Öncelikli", "Rakip reklam aktif", "Website var"]),
    }

    fw = _fw(playbook)
    active_weights = {k: v for k, v in fw.items() if v != 1.0}

    final = round((opportunity * 0.65) + (intent * 0.35), 1)

    if final >= 80:
        segment = "HOT"
    elif final >= 65:
        segment = "WARM"
    elif final >= 50:
        segment = "OK"
    else:
        segment = "LOW"

    result = {
        "status": "ok",
        "opportunity": opportunity,
        "buyer_intent": intent,
        "final_score": final,
        "segment": segment,
        "priority": SEGMENT_TO_PRIORITY[segment],
        "signals": {"opportunity": opp_signals, "intent": intent_signals},
        "score_breakdown": score_breakdown,
        "active_weights": active_weights,
        "clinic_subsector": lead.get("clinic_subsector"),
    }

    logger.info(
        "Score: %s | final=%.1f segment=%s opp=%d intent=%d subsector=%s",
        lead.get("isim"), final, segment, opportunity, intent,
        lead.get("clinic_subsector", "-"),
    )
    return result


# --------------------------------------------------
# 5. EXPLAIN / DEBUG
# --------------------------------------------------

def explain_score(result: dict, lead: dict | None = None) -> str:
    if result["status"] == "rejected":
        return f"ELENDI: {result['reason']}"

    lines = [
        f"Skor: {result['final_score']} ({result['segment']})",
        f"Opportunity: {result['opportunity']}",
        f"Buyer Intent: {result['buyer_intent']}",
    ]

    sub = result.get("clinic_subsector")
    if sub:
        lines.append(f"Klinik alt sektör: {sub}")

    signals = result.get("signals", {})
    if signals.get("opportunity"):
        lines.append("\nOpportunity sinyalleri:")
        lines.extend(f"  {s}" for s in signals["opportunity"])
    if signals.get("intent"):
        lines.append("\nIntent sinyalleri:")
        lines.extend(f"  {s}" for s in signals["intent"])

    active_w = result.get("active_weights", {})
    if active_w:
        lines.append("\nSektör ağırlıkları (1.0'dan farklı):")
        for k, v in active_w.items():
            status = "KAPALI" if v == 0.0 else f"x{v}"
            lines.append(f"  {k}: {status}")

    return "\n".join(lines)


# --------------------------------------------------
# 6. COVERAGE STATS
# --------------------------------------------------

def coverage_stats(leads: list[dict]) -> dict:
    """Kaç lead'de kanal verisi var/yok."""
    total = len(leads)
    if total == 0:
        return {}
    stats: dict[str, dict] = {}
    for field in CHANNEL_FIELDS:
        present = sum(1 for l in leads if l.get(field) is not None)
        stats[field] = {
            "present": present,
            "missing": total - present,
            "coverage_pct": round(present / total * 100, 1),
        }
    return {"total_leads": total, "fields": stats}
