import logging
from typing import Tuple

logger = logging.getLogger(__name__)


# --------------------------------------------------
# 1. HARD FILTER (ELEME)
# --------------------------------------------------

def hard_filter(lead: dict, playbook: dict) -> Tuple[bool, str]:
    """
    Lead tamamen elenmeli mi?

    Return:
    (True, reason) -> ELENDİ
    (False, "")    -> DEVAM
    """

    isim = lead.get("isim", "").lower()
    yorum = lead.get("yorum_sayisi", 0)
    puan = lead.get("puan", 0)
    telefon = lead.get("telefon")
    website = lead.get("website")
    son_yorum = lead.get("son_yorum_gun")  # None = veri yok, sadece gelince kontrol et

    # Zincir / kurumsal ele
    if any(x in isim for x in ["hastane", "devlet", "group", "merkez"]):
        return True, "kurumsal / zincir"

    # Zaten çok iyi olanı ele
    if yorum > 150 and puan > 4.5 and website:
        return True, "zaten güçlü"

    # Telefon yoksa
    if not telefon:
        return True, "telefon yok"

    # Ölü profil — sadece veri varsa uygula
    if son_yorum is not None and son_yorum > 365:
        return True, "ölü profil"

    return False, ""


# --------------------------------------------------
# 2. OPPORTUNITY SCORE (0-100)
# --------------------------------------------------

def calc_opportunity(lead: dict, audit: dict, playbook: dict) -> int:
    score = 40

    yorum = lead.get("yorum_sayisi", 0)
    puan = lead.get("puan", 0)
    website = lead.get("website")
    site_durumu = lead.get("site_durumu")
    telefon = lead.get("telefon")
    son_yorum = lead.get("son_yorum_gun")  # None = veri yok

    audit_skor = audit.get("genel_skor", 50)
    pagespeed = audit.get("pagespeed", 60)
    ssl = audit.get("ssl", True)

    # Google Ads pressure (None = veri yok → nötr)
    ads_pressure: bool | None = lead.get("market_ads_pressure")
    competitor_ads_count: int | None = lead.get("competitor_ads_count")
    self_ads_visible: bool | None = lead.get("self_ads_visible")

    # --- Yorum ---
    if yorum < 10:
        score += 15
    elif yorum < 30:
        score += 8
    elif yorum > 100:
        score -= 8

    # --- Puan ---
    if 3.8 <= puan <= 4.1:
        score += 10
    elif puan < 3.8:
        score += 5
    elif puan > 4.6:
        score -= 10

    # --- Website ---
    if not website:
        score += 20
    elif site_durumu == "zayif":
        score += 10
    elif site_durumu == "iyi":
        score -= 5

    # --- Telefon ---
    if not telefon:
        score -= 20

    # --- Yorum güncelliği ---
    if son_yorum is not None:
        if son_yorum < 30:
            score += 5
        elif son_yorum > 180:
            score -= 8

    # --- Audit ---
    if audit_skor < 35:
        score += 15
    elif audit_skor < 55:
        score += 8
    elif audit_skor > 75:
        score -= 10

    # --- PageSpeed ---
    if pagespeed < 40:
        score += 10
    elif pagespeed < 60:
        score += 5
    elif pagespeed > 85:
        score -= 5

    # --- SSL ---
    if not ssl:
        score += 8

    # --- Google Ads pressure (pazar ticari, fırsat var) ---
    if ads_pressure is True:
        score += 4

    if competitor_ads_count is not None:
        if competitor_ads_count >= 3:
            score += 4
        elif competitor_ads_count >= 1:
            score += 2

    if ads_pressure is True and self_ads_visible is False:
        # Rakipler reklam yapıyor, işletme yapmıyor → büyük açık
        score += 4
    elif self_ads_visible is True:
        # Zaten reklam yapıyor → fırsatımız daha küçük
        score -= 3

    return max(0, min(score, 100))


# --------------------------------------------------
# 3. BUYER INTENT SCORE (0-100)
# --------------------------------------------------

def calc_buyer_intent(lead: dict, audit: dict, playbook: dict) -> int:
    score = 50

    son_yorum = lead.get("son_yorum_gun")  # None = veri yok
    telefon = lead.get("telefon")
    website = lead.get("website")
    ilce_oncelik = lead.get("oncelikli_ilce", False)

    # Instagram (None = veri yok → nötr)
    post_90: int | None = lead.get("instagram_post_90d")
    last_post_days: int | None = lead.get("instagram_last_post_days")

    # YouTube (None = veri yok → nötr, düşük ağırlık)
    yt_180: int | None = lead.get("youtube_video_180d")
    yt_last_days: int | None = lead.get("youtube_last_video_days")

    # Audit'ten rakip reklam sinyali (buyer intent tarafı zaten var, ads_pressure ile çakışmaz)
    rakip = audit.get("reklam_firsati", {}).get("rakip_durum", "")

    # --- Google Maps aktivitesi ---
    if son_yorum is not None:
        if son_yorum < 30:
            score += 15
        elif son_yorum < 90:
            score += 8
        elif son_yorum > 180:
            score -= 15

    # --- Erişilebilirlik ---
    if telefon:
        score += 10
    if website:
        score += 5

    # --- Rakip reklam sinyali (audit verisi) ---
    if rakip == "aktif":
        score += 10

    # --- Öncelikli ilçe ---
    if ilce_oncelik:
        score += 8

    # --- Instagram aktivite sinyali ---
    if post_90 is not None:
        if post_90 == 0:
            score -= 6   # Hesap var ama ölü
        elif post_90 <= 3:
            score -= 2   # Neredeyse durmuş
        elif post_90 <= 10:
            score += 4   # Orta aktif
        else:
            score += 6   # Aktif hesap, dijital bilinç var

    if last_post_days is not None:
        if last_post_days < 14:
            score += 4   # Bu hafta/geçen hafta post atmış
        elif last_post_days < 60:
            score += 2   # Son 2 ayda atmış
        elif last_post_days > 60:
            score -= 4   # 2 aydan uzun süredir sessiz

    # --- YouTube aktivite sinyali (düşük ağırlık) ---
    # Yoksa ceza yok — çoğu yerel işletme YouTube kullanmaz
    if yt_180 is not None:
        if yt_180 == 0:
            score += 0
        elif yt_180 <= 2:
            score += 1
        elif yt_180 <= 6:
            score += 3
        else:
            score += 4

    if yt_last_days is not None:
        if yt_last_days < 30:
            score += 2
        elif yt_last_days < 90:
            score += 1

    return max(0, min(score, 100))


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

    opportunity = calc_opportunity(lead, audit, playbook)
    intent = calc_buyer_intent(lead, audit, playbook)

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

    if lead:
        extras: list[str] = []
        if lead.get("instagram_post_90d") is not None:
            extras.append(f"Instagram 90g post: {lead['instagram_post_90d']}")
        if lead.get("instagram_last_post_days") is not None:
            extras.append(f"Instagram son post: {lead['instagram_last_post_days']} gün")
        if lead.get("youtube_video_180d") is not None:
            extras.append(f"YouTube 180g video: {lead['youtube_video_180d']}")
        if lead.get("youtube_last_video_days") is not None:
            extras.append(f"YouTube son video: {lead['youtube_last_video_days']} gün")
        if lead.get("market_ads_pressure") is not None:
            extras.append(f"Ads pressure: {lead['market_ads_pressure']}")
        if lead.get("competitor_ads_count") is not None:
            extras.append(f"Rakip reklam sayisi: {lead['competitor_ads_count']}")
        if lead.get("self_ads_visible") is not None:
            extras.append(f"Self ads visible: {lead['self_ads_visible']}")
        if extras:
            lines.append("")
            lines.extend(extras)

    return "\n".join(lines)
