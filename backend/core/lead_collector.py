import os
import re
import asyncio
import logging
from datetime import date

import requests

from core.utils import API_SEMAPHORE

logger = logging.getLogger(__name__)

APIFY_ACTOR = "compass~crawler-google-places"
APIFY_RUN_URL = f"https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items"

_SECTOR_SEARCH_TERMS: dict[str, str] = {
    "klinik":        "klinik muayenehane",
    "avukat":        "avukat hukuk bürosu",
    "emlak":         "emlak danışmanı",
    "guzellik":      "güzellik salonu kuaför",
    "egitim":        "eğitim kursu dil okulu",
    "ev_hizmetleri": "tesisatçı",
    "kadin_dogum":   "kadın hastalıkları ve doğum uzmanı jinekoloji",
    "restoran":      "restoran lokanta",
}

# İsim veya kategori bu pattern'lara uyan lead'ler koleksiyon aşamasında filtrelenir.
# icp_filter.eleme_kriterleri ikinci katman olarak çalışır.
_SECTOR_REJECT: dict[str, re.Pattern] = {
    "klinik": re.compile(
        r"\b(bilgisayar|gsm|telefon\s*tamiri|teknik\s*servis|oto\s*klinik|"
        r"boya\s*kliniği|eczane|veteriner|market|süpermarket|"
        r"mağaza|butik|restoran|kafe|inşaat|tesisat)\b",
        re.I | re.UNICODE,
    ),
    "avukat": re.compile(
        r"\b(mağaza|butik|restoran|kafe|market|tekstil|tesisat|elektrik|"
        r"inşaat|boyacı|temizlik|nakliyat|oto|güzellik|kuaför|"
        r"bilgisayar|gsm|eczane|veteriner)\b",
        re.I | re.UNICODE,
    ),
    "emlak": re.compile(
        r"\b(mağaza|butik|tekstil|kafe|restoran|otel|tesisat|elektrik|"
        r"boyacı|temizlik|güzellik|kuaför|muayenehane|eczane|"
        r"avukat|bilgisayar|gsm)\b",
        re.I | re.UNICODE,
    ),
    "guzellik": re.compile(
        r"\b(muayenehane|klinik|hastane|eczane|veteriner|avukat|hukuk|"
        r"tesisat|elektrik|inşaat|boyacı|nakliyat|temizlik|"
        r"mağaza|butik|tekstil|market|bilgisayar|gsm|oto|restoran)\b",
        re.I | re.UNICODE,
    ),
    "egitim": re.compile(
        r"\b(mağaza|butik|tekstil|kafe|restoran|market|tesisat|elektrik|"
        r"inşaat|boyacı|nakliyat|güzellik|kuaför|muayenehane|klinik|"
        r"eczane|avukat|bilgisayar|gsm|oto|veteriner)\b",
        re.I | re.UNICODE,
    ),
    "ev_hizmetleri": re.compile(
        r"\b(mağaza|butik|tekstil|kafe|restoran|market|otel|"
        r"muayenehane|klinik|hastane|eczane|veteriner|"
        r"avukat|hukuk|güzellik|kuaför|emlak|bilgisayar|gsm)\b",
        re.I | re.UNICODE,
    ),
    "kadin_dogum": re.compile(
        r"\b(butik|mağaza|shop|store|tekstil|moda|giyim|kuaför|güzellik\s*salonu|"
        r"kozmetik|parfüm|takı|kafe|restoran|otel|hostel|temizlik|"
        r"tesisat|elektrik|inşaat|bilgisayar|gsm|veteriner)\b",
        re.I | re.UNICODE,
    ),
    "restoran": re.compile(
        r"\b(klinik|hastane|eczane|tesisat|elektrik|inşaat|boyacı|tadilat|"
        r"mağaza|butik|tekstil|avukat|hukuk|güzellik\s*merkezi|"
        r"bilgisayar|gsm|nakliyat|temizlik|veteriner)\b",
        re.I | re.UNICODE,
    ),
}


async def collect_google_maps(sektor: str, sehir: str, ilce: str, limit: int = 30) -> list[dict]:
    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        logger.error("APIFY_API_TOKEN .env'de tanımlı değil — lead toplama atlandı")
        return []

    search_term = _SECTOR_SEARCH_TERMS.get(sektor, sektor)
    location = ", ".join(p for p in [ilce, sehir, "Turkey"] if p)
    logger.info(
        "Google Maps taraması başlıyor: arama='%s' konum='%s' limit=%d",
        search_term, location, limit,
    )

    payload = {
        "searchStringsArray": [search_term],
        "locationQuery": location,
        "maxCrawledPlacesPerSearch": limit,
        "language": "tr",
        "countryCode": "tr",
    }

    async with API_SEMAPHORE:
        try:
            response = await asyncio.to_thread(
                requests.post,
                APIFY_RUN_URL,
                params={"token": token},
                json=payload,
                timeout=300,
            )
            response.raise_for_status()
            raw_leads = response.json()
        except requests.RequestException as e:
            logger.exception(f"Apify API çağrısı başarısız ({search_term} @ {location}): {e}")
            return []
        except ValueError as e:
            logger.exception(f"Apify yanıtı JSON olarak ayrıştırılamadı ({search_term} @ {location}): {e}")
            return []

    if not isinstance(raw_leads, list):
        logger.error(f"Apify beklenmedik yanıt döndü ({search_term} @ {location}): tip={type(raw_leads).__name__}")
        return []

    logger.info(f"{len(raw_leads)} ham lead alındı: '{search_term} @ {location}'")
    enriched = [enrich_lead(lead) for lead in raw_leads]
    enriched = _filter_relevant(enriched, sektor)
    logger.info(f"{len(enriched)} lead zenginleştirildi ve filtrelendi: '{search_term} @ {location}'")
    return enriched


def _filter_relevant(leads: list[dict], sektor: str) -> list[dict]:
    pattern = _SECTOR_REJECT.get(sektor)
    if not pattern:
        return leads
    result = []
    for lead in leads:
        text = f"{lead.get('isim') or ''} {lead.get('kategori') or ''}".lower()
        if pattern.search(text):
            logger.info("Alakasız lead filtrelendi: %s (kategori: %s)", lead.get("isim"), lead.get("kategori"))
        else:
            result.append(lead)
    return result


def enrich_lead(raw: dict) -> dict:
    website_raw = raw.get("website")
    if website_raw and "google.com/maps" in website_raw:
        website_raw = None
    website = _normalize_url(website_raw)
    telefon = _format_phone(raw.get("phone") or raw.get("phoneNumber") or raw.get("phoneUnformatted"))

    lead = {
        "isim": raw.get("title") or raw.get("name"),
        "adres": raw.get("address"),
        "telefon": telefon,
        "website": website,
        "yorum_sayisi": raw.get("reviewsCount") or 0,
        "puan": raw.get("totalScore") or 0,
        "kategori": raw.get("categoryName"),
        "enlem": raw.get("location", {}).get("lat") if isinstance(raw.get("location"), dict) else None,
        "boylam": raw.get("location", {}).get("lng") if isinstance(raw.get("location"), dict) else None,
        "maps_url": raw.get("url"),
        "site_durumu": _site_durumu(website),
        "kaynak": "google_maps",
        "toplama_tarihi": date.today().isoformat(),
    }
    return lead


def _normalize_url(url) -> str | None:
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _format_phone(phone) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", str(phone))
    if not digits:
        return None
    if digits.startswith("90") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"+90{digits}"
    logger.warning(f"Telefon standart formata sokulamadı, ham döndürüldü: {phone}")
    return f"+{digits}" if digits else None


def _site_durumu(website: str | None) -> str:
    if not website:
        return "yok"
    return "zayif"
