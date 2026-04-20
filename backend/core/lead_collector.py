import os
import re
import asyncio
import logging
from datetime import date
from urllib.parse import urlparse

import requests

from core.utils import API_SEMAPHORE

logger = logging.getLogger(__name__)

# Domains that are listing/directory/social sites — NOT the business's own website.
# A URL on these domains means "no own website" = sales opportunity.
_LISTING_DOMAINS: frozenset[str] = frozenset({
    # Turkish medical/business directories
    "doktorsitesi.com", "saglikta.com", "doktortakvimi.com", "hepsidoktor.com",
    "doktorfizik.com", "hastaneadres.com", "randevu.com", "doktortercihim.com",
    "doktorumol.com", "drdesc.com",
    # Turkish general directories / classifieds
    "sahibinden.com", "yemeksepeti.com", "getir.com", "trendyol.com",
    "n11.com", "hepsiburada.com", "gittigidiyor.com",
    # Social media
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "youtube.com", "tiktok.com", "pinterest.com",
    # International directories
    "yelp.com", "tripadvisor.com", "foursquare.com", "zomato.com",
    "zocdoc.com", "healthgrades.com", "vitals.com", "ratemds.com",
    "webmd.com", "practo.com",
    # Maps / search
    "google.com", "maps.google.com", "maps.app.goo.gl",
    "yandex.com", "yandex.com.tr",
})

APIFY_ACTOR = "compass~crawler-google-places"
APIFY_RUN_URL = f"https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items"

_SECTOR_SEARCH_TERMS: dict[str, str] = {
    "klinik":          "klinik muayenehane",
    "avukat":          "avukat hukuk bürosu",
    "emlak":           "emlak danışmanı",
    "guzellik":        "güzellik salonu kuaför",
    "egitim":          "eğitim kursu dil okulu",
    "ev_hizmetleri":   "tesisatçı elektrikçi kombi servisi",
    "kadin_dogum":     "kadın hastalıkları ve doğum uzmanı jinekoloji",
    "restoran":        "restoran lokanta",
    # Yeni sektörler
    "oto_servis":      "oto tamir servis lastikçi",
    "klima_beyaz_esya": "klima servisi beyaz eşya servisi kombi tamiri",
    "cilingir":        "çilingir kilitçi",
    "tadilat":         "tadilat boyacı boya badana dekorasyon",
    "nakliyat":        "nakliyat evden eve nakliye",
    "hali_temizlik":   "halı yıkama ev temizliği temizlik şirketi",
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
    # Yeni sektörler
    "oto_servis": re.compile(
        r"\b(klinik|hastane|eczane|restoran|kafe|güzellik|kuaför|avukat|"
        r"eğitim|nakliyat|temizlik|inşaat|tesisat|tekstil|mağaza|market)\b",
        re.I | re.UNICODE,
    ),
    "klima_beyaz_esya": re.compile(
        r"\b(klinik|hastane|eczane|restoran|kafe|güzellik|kuaför|avukat|"
        r"eğitim|nakliyat|oto\s*tamir|inşaat|tekstil|mağaza|market)\b",
        re.I | re.UNICODE,
    ),
    "cilingir": re.compile(
        r"\b(klinik|hastane|eczane|restoran|kafe|güzellik|kuaför|avukat|"
        r"eğitim|oto|nakliyat|inşaat|tesisat|elektrik|tekstil|mağaza)\b",
        re.I | re.UNICODE,
    ),
    "tadilat": re.compile(
        r"\b(klinik|hastane|eczane|restoran|kafe|güzellik|kuaför|avukat|"
        r"eğitim|oto|nakliyat|tesisat|elektrik|tekstil|market|süpermarket)\b",
        re.I | re.UNICODE,
    ),
    "nakliyat": re.compile(
        r"\b(klinik|hastane|eczane|restoran|kafe|güzellik|kuaför|avukat|"
        r"eğitim|oto\s*tamir|tesisat|elektrik|temizlik|tekstil|market)\b",
        re.I | re.UNICODE,
    ),
    "hali_temizlik": re.compile(
        r"\b(klinik|hastane|eczane|restoran|kafe|güzellik|kuaför|avukat|"
        r"eğitim|oto|nakliyat|elektrik|tesisat|inşaat|tekstil|market)\b",
        re.I | re.UNICODE,
    ),
}


async def collect_by_query(
    search_string: str,
    sehir: str | None = None,
    ilce: str | None = None,
    limit: int = 30,
    sektor_filter: str | None = None,
    apify_timeout: int = 300,
    max_reviews: int = 20,
) -> list[dict]:
    """
    Free-form search against Apify Google Places.
    Applies query-relevance filter so results actually match the search term.
    """
    if not (search_string or "").strip():
        return []
    leads = await _run_apify(
        search_term=search_string.strip(),
        sehir=sehir or "",
        ilce=ilce or "",
        limit=limit,
        sektor_for_filter=sektor_filter,
        apify_timeout=apify_timeout,
        max_reviews=max_reviews,
    )
    return _filter_by_query_relevance(leads, search_string.strip())


_QUERY_STOPWORDS = {
    "ara", "bul", "tara", "bak", "listele", "getir", "çek",
    "doktoru", "uzmanı", "servisi", "kliniği", "merkezi", "firması",
    "hizmeti", "şirketi", "bürosu", "ofisi",
    "ve", "ile", "için", "bir", "bu", "da", "de", "ya", "ki",
}


def _filter_by_query_relevance(leads: list[dict], query: str) -> list[dict]:
    """Keep only leads whose name or Google category contains a query keyword."""
    tokens = [w.lower() for w in re.findall(r"\w+", query) if w.lower() not in _QUERY_STOPWORDS]
    if not tokens:
        return leads

    result = []
    for lead in leads:
        text = f"{lead.get('isim') or ''} {lead.get('kategori') or ''}".lower()
        if any(tok in text for tok in tokens):
            result.append(lead)
        else:
            logger.info(
                "Query relevance filter: '%s' (kategori: %s) — hiçbir token (%s) eşleşmedi",
                lead.get("isim"), lead.get("kategori"), tokens,
            )
    logger.info("Query relevance: %d/%d lead kaldı (query=%r)", len(result), len(leads), query)
    return result


async def collect_google_maps(sektor: str, sehir: str, ilce: str, limit: int = 30) -> list[dict]:
    search_term = _SECTOR_SEARCH_TERMS.get(sektor, sektor)
    return await _run_apify(
        search_term=search_term,
        sehir=sehir,
        ilce=ilce,
        limit=limit,
        sektor_for_filter=sektor,
    )


async def _run_apify(
    search_term: str,
    sehir: str,
    ilce: str,
    limit: int,
    sektor_for_filter: str | None,
    apify_timeout: int = 300,
    max_reviews: int = 20,
) -> list[dict]:
    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        logger.error("APIFY_API_TOKEN .env'de tanımlı değil — lead toplama atlandı")
        return []

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
        "maxReviews": max_reviews,
        "reviewsSort": "newest",   # en yeni yorumlar önce gelsin
    }

    async with API_SEMAPHORE:
        try:
            response = await asyncio.to_thread(
                requests.post,
                APIFY_RUN_URL,
                params={"token": token},
                json=payload,
                timeout=apify_timeout,
            )
            response.raise_for_status()
            raw_leads = response.json()
        except requests.Timeout:
            logger.warning(f"Apify zaman aşımı ({apify_timeout}s) — {search_term} @ {location}")
            raise TimeoutError(f"Apify {apify_timeout}s içinde yanıt vermedi")
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
    if sektor_for_filter:
        enriched = _filter_relevant(enriched, sektor_for_filter)
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
    if website_raw:
        try:
            domain = urlparse(website_raw).netloc.lower().lstrip("www.")
            if any(domain == d or domain.endswith("." + d) for d in _LISTING_DOMAINS):
                website_raw = None
        except Exception:
            website_raw = None
    website = _normalize_url(website_raw)
    telefon = _format_phone(raw.get("phone") or raw.get("phoneNumber") or raw.get("phoneUnformatted"))

    today = date.today()

    # ── Review velocity (son yorumların tarihlerinden) ──────────────────
    reviews = raw.get("reviews") or []
    review_dates: list[date] = []
    for r in reviews:
        ds = r.get("publishedAtDate") or r.get("publishAt") or ""
        if isinstance(ds, str) and len(ds) >= 10:
            try:
                review_dates.append(date.fromisoformat(ds[:10]))
            except ValueError:
                pass

    son_yorum_gun: int | None = None
    review_last_30d: int | None = None
    review_last_90d: int | None = None

    if review_dates:
        review_dates.sort(reverse=True)
        son_yorum_gun  = (today - review_dates[0]).days
        review_last_30d = sum(1 for d in review_dates if (today - d).days <= 30)
        review_last_90d = sum(1 for d in review_dates if (today - d).days <= 90)

    # ── GMB derinliği ────────────────────────────────────────────────────
    photos = raw.get("imageUrls") or raw.get("images") or []
    gmb_photo_count: int | None = len(photos) if isinstance(photos, list) else None

    desc = raw.get("description")
    gmb_has_description: bool | None = bool(desc.strip()) if isinstance(desc, str) else (
        None if desc is None else bool(desc)
    )

    qa = raw.get("questionsAndAnswers")
    gmb_has_qa: bool | None = (bool(qa) if qa is not None else None)

    # ── Zombie / kapalı işletme ──────────────────────────────────────────
    permanently_closed = raw.get("permanentlyClosed") or raw.get("isClosed") or False

    lead = {
        "isim":           raw.get("title") or raw.get("name"),
        "adres":          raw.get("address"),
        "telefon":        telefon,
        "website":        website,
        "yorum_sayisi":   raw.get("reviewsCount") or 0,
        "puan":           raw.get("totalScore") or 0,
        "kategori":       raw.get("categoryName"),
        "enlem":          raw.get("location", {}).get("lat") if isinstance(raw.get("location"), dict) else None,
        "boylam":         raw.get("location", {}).get("lng") if isinstance(raw.get("location"), dict) else None,
        "maps_url":       raw.get("url"),
        "site_durumu":    _site_durumu(website),
        "kaynak":         "google_maps",
        "toplama_tarihi": today.isoformat(),
        # Review velocity
        "son_yorum_gun":  son_yorum_gun,
        "review_last_30d": review_last_30d,
        "review_last_90d": review_last_90d,
        # GMB derinliği
        "gmb_photo_count":      gmb_photo_count,
        "gmb_has_description":  gmb_has_description,
        "gmb_has_qa":           gmb_has_qa,
        # Zombie sinyali
        "permanently_closed":   permanently_closed,
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
