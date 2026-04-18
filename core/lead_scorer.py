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

    rakip = audit.get("reklam_firsati", {}).get("rakip_durum", "")

    # --- Aktivite ---
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

    # --- Büyüme sinyali ---
    if rakip == "aktif":
        score += 10

    if ilce_oncelik:
        score += 8

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

def explain_score(result: dict) -> str:
    if result["status"] == "rejected":
        return f"ELENDI: {result['reason']}"

    return (
        f"Skor: {result['final_score']} ({result['segment']})\n"
        f"Opportunity: {result['opportunity']}\n"
        f"Buyer Intent: {result['buyer_intent']}"
    )
