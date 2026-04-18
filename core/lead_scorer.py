import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Sektör bazlı override için varsayılan ağırlıklar (playbook'ta channel_weights ile ezilebilir)
DEFAULT_CHANNEL_WEIGHTS = {
    "instagram": 1.0,
    "youtube": 1.0,
    "ads": 1.0,
}

# Kanal sinyali field'ları — coverage_stats için
CHANNEL_FIELDS = [
    "instagram_post_90d",
    "instagram_last_post_days",
    "youtube_video_180d",
    "youtube_last_video_days",
    "market_ads_pressure",
    "competitor_ads_count",
    "self_ads_visible",
]


def _channel_weights(playbook: dict) -> dict:
    w = DEFAULT_CHANNEL_WEIGHTS.copy()
    w.update(playbook.get("channel_weights", {}))
    return w


# --------------------------------------------------
# 1. HARD FILTER (ELEME)
# --------------------------------------------------

def hard_filter(lead: dict, playbook: dict) -> Tuple[bool, str]:
    """
    Return:
    (True, reason) -> ELENDİ
    (False, "")    -> DEVAM
    """
    isim = lead.get("isim", "").lower()
    yorum = lead.get("yorum_sayisi", 0)
    puan = lead.get("puan", 0)
    telefon = lead.get("telefon")
    website = lead.get("website")
    son_yorum = lead.get("son_yorum_gun")

    if any(x in isim for x in ["hastane", "devlet", "group", "merkez"]):
        return True, "kurumsal / zincir"

    if yorum > 150 and puan > 4.5 and website:
        return True, "zaten güçlü"

    if not telefon:
        return True, "telefon yok"

    if son_yorum is not None and son_yorum > 365:
        return True, "ölü profil"

    return False, ""


# --------------------------------------------------
# 2. OPPORTUNITY SCORE (0-100)
# --------------------------------------------------

def calc_opportunity(lead: dict, audit: dict, playbook: dict) -> tuple[int, list[str]]:
    """Returns (score, signals) where signals log each non-zero contribution."""
    score = 40
    signals: list[str] = []

    yorum = lead.get("yorum_sayisi", 0)
    puan = lead.get("puan", 0)
    website = lead.get("website")
    site_durumu = lead.get("site_durumu")
    telefon = lead.get("telefon")
    son_yorum = lead.get("son_yorum_gun")

    audit_skor = audit.get("genel_skor", 50)
    pagespeed = audit.get("pagespeed", 60)
    ssl = audit.get("ssl", True)

    ads_pressure: bool | None = lead.get("market_ads_pressure")
    competitor_ads_count: int | None = lead.get("competitor_ads_count")
    self_ads_visible: bool | None = lead.get("self_ads_visible")

    cw = _channel_weights(playbook)

    def add(delta: int, label: str) -> None:
        nonlocal score
        score += delta
        if delta != 0:
            signals.append(f"{label} → {'+' if delta > 0 else ''}{delta}")

    # --- Yorum ---
    if yorum < 10:
        add(15, f"Yorum az ({yorum})")
    elif yorum < 30:
        add(8, f"Yorum orta ({yorum})")
    elif yorum > 100:
        add(-8, f"Yorum çok ({yorum})")

    # --- Puan ---
    if 3.8 <= puan <= 4.1:
        add(10, f"Puan orta ({puan})")
    elif puan < 3.8:
        add(5, f"Puan düşük ({puan})")
    elif puan > 4.6:
        add(-10, f"Puan yüksek ({puan})")

    # --- Website ---
    if not website:
        add(20, "Website yok")
    elif site_durumu == "zayif":
        add(10, "Site zayıf")
    elif site_durumu == "iyi":
        add(-5, "Site iyi")

    # --- Telefon ---
    if not telefon:
        add(-20, "Telefon yok")

    # --- Yorum güncelliği ---
    if son_yorum is not None:
        if son_yorum < 30:
            add(5, f"Son yorum yakın ({son_yorum}g)")
        elif son_yorum > 180:
            add(-8, f"Son yorum eski ({son_yorum}g)")

    # --- Audit ---
    if audit_skor < 35:
        add(15, f"Audit çok zayıf ({audit_skor})")
    elif audit_skor < 55:
        add(8, f"Audit zayıf ({audit_skor})")
    elif audit_skor > 75:
        add(-10, f"Audit güçlü ({audit_skor})")

    # --- PageSpeed ---
    if pagespeed < 40:
        add(10, f"PageSpeed çok yavaş ({pagespeed})")
    elif pagespeed < 60:
        add(5, f"PageSpeed yavaş ({pagespeed})")
    elif pagespeed > 85:
        add(-5, f"PageSpeed hızlı ({pagespeed})")

    # --- SSL ---
    if not ssl:
        add(8, "SSL yok")

    # --- Google Ads pressure (sektör ağırlıklı) ---
    ads_w = cw["ads"]
    if ads_pressure is True:
        add(round(4 * ads_w), "Ads pressure var")

    if competitor_ads_count is not None:
        if competitor_ads_count >= 3:
            add(round(4 * ads_w), f"Rakip reklam sayısı: {competitor_ads_count}")
        elif competitor_ads_count >= 1:
            add(round(2 * ads_w), f"Rakip reklam sayısı: {competitor_ads_count}")

    if ads_pressure is True and self_ads_visible is False:
        add(round(4 * ads_w), "Rakip var, self yok → açık")
    elif self_ads_visible is True:
        add(-3, "Self ads görünüyor")

    return max(0, min(score, 100)), signals


# --------------------------------------------------
# 3. BUYER INTENT SCORE (0-100)
# --------------------------------------------------

def calc_buyer_intent(lead: dict, audit: dict, playbook: dict) -> tuple[int, list[str]]:
    """Returns (score, signals) where signals log each non-zero contribution."""
    score = 50
    signals: list[str] = []

    son_yorum = lead.get("son_yorum_gun")
    telefon = lead.get("telefon")
    website = lead.get("website")
    ilce_oncelik = lead.get("oncelikli_ilce", False)
    rakip = audit.get("reklam_firsati", {}).get("rakip_durum", "")

    post_90: int | None = lead.get("instagram_post_90d")
    last_post_days: int | None = lead.get("instagram_last_post_days")
    yt_180: int | None = lead.get("youtube_video_180d")
    yt_last_days: int | None = lead.get("youtube_last_video_days")

    cw = _channel_weights(playbook)

    def add(delta: int, label: str) -> None:
        nonlocal score
        score += delta
        if delta != 0:
            signals.append(f"{label} → {'+' if delta > 0 else ''}{delta}")

    # --- Google Maps aktivitesi ---
    if son_yorum is not None:
        if son_yorum < 30:
            add(15, f"Son yorum yakın ({son_yorum}g)")
        elif son_yorum < 90:
            add(8, f"Son yorum orta ({son_yorum}g)")
        elif son_yorum > 180:
            add(-15, f"Son yorum eski ({son_yorum}g)")

    # --- Erişilebilirlik ---
    if telefon:
        add(10, "Telefon var")
    if website:
        add(5, "Website var")

    # --- Rakip reklam sinyali (TODO: ileride opportunity'e taşınabilir) ---
    if rakip == "aktif":
        add(10, "Rakip reklam aktif")

    if ilce_oncelik:
        add(8, "Öncelikli ilçe")

    # --- Instagram aktivite sinyali ---
    ig_w = cw["instagram"]
    if post_90 is not None:
        if post_90 == 0:
            add(round(-6 * ig_w), f"Instagram 90g post: {post_90}")
        elif post_90 <= 3:
            add(round(-2 * ig_w), f"Instagram 90g post: {post_90}")
        elif post_90 <= 10:
            add(round(4 * ig_w), f"Instagram 90g post: {post_90}")
        else:
            add(round(6 * ig_w), f"Instagram 90g post: {post_90}")

    if last_post_days is not None:
        if last_post_days < 14:
            add(round(4 * ig_w), f"Instagram son post: {last_post_days}g")
        elif last_post_days < 60:
            add(round(2 * ig_w), f"Instagram son post: {last_post_days}g")
        elif last_post_days > 60:
            add(round(-4 * ig_w), f"Instagram son post: {last_post_days}g")

    # --- YouTube aktivite sinyali (düşük ağırlık, yoksa ceza yok) ---
    yt_w = cw["youtube"]
    if yt_180 is not None:
        if yt_180 == 0:
            pass  # ceza verme
        elif yt_180 <= 2:
            add(round(1 * yt_w), f"YouTube 180g video: {yt_180}")
        elif yt_180 <= 6:
            add(round(3 * yt_w), f"YouTube 180g video: {yt_180}")
        else:
            add(round(4 * yt_w), f"YouTube 180g video: {yt_180}")

    if yt_last_days is not None:
        if yt_last_days < 30:
            add(round(2 * yt_w), f"YouTube son video: {yt_last_days}g")
        elif yt_last_days < 90:
            add(round(1 * yt_w), f"YouTube son video: {yt_last_days}g")

    return max(0, min(score, 100)), signals


# --------------------------------------------------
# 4. FINAL SCORE
# --------------------------------------------------

SEGMENT_TO_PRIORITY = {
    "HOT": "yuksek",
    "WARM": "yuksek",
    "OK": "orta",
    "LOW": "dusuk",
}


def calculate_final_score(lead: dict, audit: dict, playbook: dict) -> dict:
    """Full scoring pipeline. audit can be {} at scrape time."""

    is_blocked, reason = hard_filter(lead, playbook)
    if is_blocked:
        return {"status": "rejected", "reason": reason}

    opportunity, opp_signals = calc_opportunity(lead, audit, playbook)
    intent, intent_signals = calc_buyer_intent(lead, audit, playbook)

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
    }

    logger.info(
        "Score: %s | final=%.1f segment=%s opp=%d intent=%d",
        lead.get("isim"), final, segment, opportunity, intent,
    )
    return result


# --------------------------------------------------
# 5. DEBUG / LOG
# --------------------------------------------------

def explain_score(result: dict, lead: dict | None = None) -> str:
    if result["status"] == "rejected":
        return f"ELENDI: {result['reason']}"

    lines = [
        f"Skor: {result['final_score']} ({result['segment']})",
        f"Opportunity: {result['opportunity']}",
        f"Buyer Intent: {result['buyer_intent']}",
    ]

    signals = result.get("signals", {})
    opp_signals = signals.get("opportunity", [])
    intent_signals = signals.get("intent", [])

    if opp_signals:
        lines.append("\nOpportunity sinyalleri:")
        lines.extend(f"  {s}" for s in opp_signals)

    if intent_signals:
        lines.append("\nIntent sinyalleri:")
        lines.extend(f"  {s}" for s in intent_signals)

    return "\n".join(lines)


# --------------------------------------------------
# 6. COVERAGE STATS
# --------------------------------------------------

def coverage_stats(leads: list[dict]) -> dict:
    """Kaç lead'de kanal verisi var/yok. Veri coverage'ı ölçer."""
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
