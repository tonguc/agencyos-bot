import logging

logger = logging.getLogger(__name__)


def score_opportunity(lead: dict) -> dict:
    skor = 50
    aciks: list[str] = []

    yorum = lead.get("yorum_sayisi") or 0
    if yorum < 10:
        skor += 15
        aciks.append("Az yorum (zayif sosyal kanit)")
    elif yorum < 20:
        skor += 8
    elif yorum > 100:
        skor -= 10

    puan = lead.get("puan") or 0
    if puan and puan < 4.0:
        skor += 20
        aciks.append(f"Dusuk puan ({puan})")
    elif puan and puan > 4.6:
        skor -= 10

    if not lead.get("website"):
        skor += 20
        aciks.append("Web sitesi yok")
    elif lead.get("site_durumu") == "zayif":
        skor += 10
        aciks.append("Site zayif")

    if not lead.get("telefon"):
        skor -= 10

    skor = max(0, min(100, skor))
    oncelik = "yuksek" if skor >= 70 else ("orta" if skor >= 40 else "dusuk")
    en_buyuk = aciks[0] if aciks else "Dijital varlik zayif"

    logger.info(
        "Skor: %s | skor=%d oncelik=%s acik=%s",
        lead.get("isim"), skor, oncelik, en_buyuk,
    )

    return {"skor": skor, "oncelik": oncelik, "en_buyuk_acik": en_buyuk, "aciklar": aciks}


def score_opportunity_with_audit(base_score: int, audit_result: dict, site_data: dict) -> dict:
    """Refine opportunity score using real audit data. Returns updated score + priority."""
    skor = base_score
    aciks: list[str] = []

    # Claude's overall site quality score (low = more opportunity for us)
    genel_skor = audit_result.get("genel_skor")
    if genel_skor is not None:
        if genel_skor < 35:
            skor += 15
            aciks.append(f"Site cok zayif (audit skoru {genel_skor})")
        elif genel_skor < 55:
            skor += 8
            aciks.append(f"Site zayif (audit skoru {genel_skor})")
        elif genel_skor > 75:
            skor -= 12
            aciks.append(f"Site guclü (audit skoru {genel_skor})")

    # Page speed
    hiz = site_data.get("hiz_skoru")
    if hiz is not None:
        if hiz < 40:
            skor += 10
            aciks.append(f"Cok yavas site (hiz {hiz})")
        elif hiz < 60:
            skor += 5
        elif hiz > 85:
            skor -= 5

    # Missing technical basics
    if site_data.get("ssl") is False:
        skor += 8
        aciks.append("SSL yok")
    if site_data.get("form_var") is False:
        skor += 5
        aciks.append("Form yok")

    # Claude's urgency and lead quality signals
    urgency = audit_result.get("urgency")
    if urgency == "yuksek":
        skor += 10
        aciks.append("Yuksek urgency")
    elif urgency == "dusuk":
        skor -= 8

    lead_quality = audit_result.get("lead_kalitesi")
    if lead_quality == "yuksek":
        skor += 8
        aciks.append("Yuksek lead kalitesi")
    elif lead_quality == "dusuk":
        skor -= 10

    skor = max(0, min(100, skor))
    oncelik = "yuksek" if skor >= 70 else ("orta" if skor >= 40 else "dusuk")

    logger.info("Audit sonrasi skor guncellendi: %d → %d (%s)", base_score, skor, oncelik)

    return {"skor": skor, "oncelik": oncelik, "aciklar": aciks}


async def batch_score(leads: list[dict]) -> list[dict]:
    return [{**lead, "skor_detay": score_opportunity(lead)} for lead in leads]

