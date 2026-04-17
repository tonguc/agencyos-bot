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


async def batch_score(leads: list[dict]) -> list[dict]:
    return [{**lead, "skor_detay": score_opportunity(lead)} for lead in leads]
