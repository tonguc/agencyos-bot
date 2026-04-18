"""
Natural language query parser for the Search experience.

Input examples:
- "kadıköyde estetik diş hekimi"
- "beşiktaş psikolog"
- "kaş'ta restoran"
- "ankara emlak"

Output (always returns a usable dict, never raises):
{
  "raw_query":       "...",                 # original
  "city":            "İstanbul" | None,     # capitalized, Turkish
  "district":        "Kadıköy"  | None,
  "category":        "estetik diş hekimi",  # the noun phrase used as search modifier
  "sector":          "klinik"   | None,     # mapped top-level sector
  "sub_sector_hint": "dental"   | None,
  "search_string":   "estetik diş hekimi",  # what we send to Maps
}

Rule-based & fail-safe. If we cannot identify a sector, we fall back to using
the raw query as the search_string and leave sector=None.
"""

from __future__ import annotations

import re
import unicodedata

# ── City / district dictionary ───────────────────────────────────────────────
# Keys are normalized (lowercase, no diacritics, no apostrophe).
# Value: (display_district, default_city_display)
_DISTRICTS: dict[str, tuple[str, str]] = {
    # İstanbul
    "kadikoy":       ("Kadıköy",       "İstanbul"),
    "besiktas":      ("Beşiktaş",      "İstanbul"),
    "sisli":         ("Şişli",         "İstanbul"),
    "uskudar":       ("Üsküdar",       "İstanbul"),
    "atasehir":      ("Ataşehir",      "İstanbul"),
    "maltepe":       ("Maltepe",       "İstanbul"),
    "kartal":        ("Kartal",        "İstanbul"),
    "pendik":        ("Pendik",        "İstanbul"),
    "umraniye":      ("Ümraniye",      "İstanbul"),
    "bakirkoy":      ("Bakırköy",      "İstanbul"),
    "beylikduzu":    ("Beylikdüzü",    "İstanbul"),
    "esenyurt":      ("Esenyurt",      "İstanbul"),
    "avcilar":       ("Avcılar",       "İstanbul"),
    "kucukcekmece":  ("Küçükçekmece",  "İstanbul"),
    "buyukcekmece":  ("Büyükçekmece",  "İstanbul"),
    "fatih":         ("Fatih",         "İstanbul"),
    "beyoglu":       ("Beyoğlu",       "İstanbul"),
    "sariyer":       ("Sarıyer",       "İstanbul"),
    "eyup":          ("Eyüpsultan",    "İstanbul"),
    "eyupsultan":    ("Eyüpsultan",    "İstanbul"),
    "basaksehir":    ("Başakşehir",    "İstanbul"),
    "bahcelievler":  ("Bahçelievler",  "İstanbul"),
    "bagcilar":      ("Bağcılar",      "İstanbul"),
    "gaziosmanpasa": ("Gaziosmanpaşa", "İstanbul"),
    "tuzla":         ("Tuzla",         "İstanbul"),
    "sancaktepe":    ("Sancaktepe",    "İstanbul"),
    "cekmekoy":      ("Çekmeköy",      "İstanbul"),
    "kagithane":     ("Kağıthane",     "İstanbul"),
    "zeytinburnu":   ("Zeytinburnu",   "İstanbul"),
    # Ankara
    "cankaya":       ("Çankaya",       "Ankara"),
    "kecioren":      ("Keçiören",      "Ankara"),
    "yenimahalle":   ("Yenimahalle",   "Ankara"),
    "etimesgut":     ("Etimesgut",     "Ankara"),
    "mamak":         ("Mamak",         "Ankara"),
    "sincan":        ("Sincan",        "Ankara"),
    "altindag":      ("Altındağ",      "Ankara"),
    "golbasi":       ("Gölbaşı",       "Ankara"),
    "pursaklar":     ("Pursaklar",     "Ankara"),
    # İzmir
    "konak":         ("Konak",         "İzmir"),
    "karsiyaka":     ("Karşıyaka",     "İzmir"),
    "bornova":       ("Bornova",       "İzmir"),
    "buca":          ("Buca",          "İzmir"),
    "cesme":         ("Çeşme",         "İzmir"),
    "alsancak":      ("Alsancak",      "İzmir"),
    "karabaglar":    ("Karabağlar",    "İzmir"),
    "gaziemir":      ("Gaziemir",      "İzmir"),
    "balcova":       ("Balçova",       "İzmir"),
    "narlidere":     ("Narlıdere",     "İzmir"),
    # Antalya
    "muratpasa":     ("Muratpaşa",     "Antalya"),
    "konyaalti":     ("Konyaaltı",     "Antalya"),
    "kepez":         ("Kepez",         "Antalya"),
    "kas":           ("Kaş",           "Antalya"),
    "alanya":        ("Alanya",        "Antalya"),
    "manavgat":      ("Manavgat",      "Antalya"),
    "side":          ("Side",          "Antalya"),
    "kemer":         ("Kemer",         "Antalya"),
    # Bursa
    "nilufer":       ("Nilüfer",       "Bursa"),
    "osmangazi":     ("Osmangazi",     "Bursa"),
    "yildirim":      ("Yıldırım",      "Bursa"),
    "mudanya":       ("Mudanya",       "Bursa"),
    "gemlik":        ("Gemlik",        "Bursa"),
    # Diğer popüler ilçeler
    "bodrum":        ("Bodrum",        "Muğla"),
    "marmaris":      ("Marmaris",      "Muğla"),
    "fethiye":       ("Fethiye",       "Muğla"),
    "didim":         ("Didim",         "Aydın"),
    "kusadasi":      ("Kuşadası",      "Aydın"),
    "cesnova":       ("Çeşnova",       "İzmir"),
}

_CITIES: dict[str, str] = {
    "istanbul":   "İstanbul",
    "ankara":     "Ankara",
    "izmir":      "İzmir",
    "antalya":    "Antalya",
    "bursa":      "Bursa",
    "adana":      "Adana",
    "konya":      "Konya",
    "gaziantep":  "Gaziantep",
    "kayseri":    "Kayseri",
    "mersin":     "Mersin",
    "eskisehir":  "Eskişehir",
    "samsun":     "Samsun",
    "trabzon":    "Trabzon",
    "diyarbakir": "Diyarbakır",
    "mugla":      "Muğla",
    "aydin":      "Aydın",
    "denizli":    "Denizli",
    "sakarya":    "Sakarya",
    "kocaeli":    "Kocaeli",
    "tekirdag":   "Tekirdağ",
    "balikesir":  "Balıkesir",
    "manisa":     "Manisa",
    "edirne":     "Edirne",
}

# ── Sector keyword mapping ───────────────────────────────────────────────────
# Order matters: more specific keywords first so we don't shadow them.
# Each entry: (regex matching the noun, sector, sub_sector_hint or None)
# Patterns are deliberately stem-style (no trailing \b) so Turkish noun
# suffixes are matched: "hekim", "hekimi", "hekimleri", "hekimlerimiz", etc.
_SECTOR_KEYWORDS: list[tuple[re.Pattern, str, str | None]] = [
    # Klinik
    (re.compile(r"\b(estetik\s+di[sş]|di[sş]\s+hekim|di[sş]\s+klini[gğ]i|implant|ortodonti|"
                r"di[sş]\s+doktor)", re.I | re.U), "klinik", "dental"),
    (re.compile(r"\b(plastik\s+cerrah|estetik\s+cerrah|burun\s+esteti[gğ]i|meme\s+esteti[gğ]i|"
                r"liposakshion|liposuction)", re.I | re.U), "klinik", "aesthetic"),
    (re.compile(r"\b(psikolog|psikiyatr|terapist|psikoterapist|aile\s+danı[sş]man)",
                re.I | re.U), "klinik", "trust"),
    (re.compile(r"\b(diyetisyen|beslenme\s+uzman)", re.I | re.U), "klinik", "general"),
    (re.compile(r"\b(dermatolog|cilt\s+doktor|cildiye)", re.I | re.U), "klinik", "aesthetic"),
    (re.compile(r"\b(fizyoterap|fizik\s+tedavi)", re.I | re.U), "klinik", "trust"),
    (re.compile(r"\b(g[oö]z\s+doktor|oftalmolog|kbb|kulak\s+burun)", re.I | re.U),
     "klinik", "general"),
    (re.compile(r"\b(klinik|muayenehane|doktor|hekim|t[ıi]p\s+merkez)", re.I | re.U),
     "klinik", "general"),

    # Kadın doğum (own top-level sector)
    (re.compile(r"\b(kad[ıi]n\s+do[gğ]um|jinekolog|jinekoloji|gebelik\s+takip|"
                r"obstetri|t[uü]p\s+bebek)", re.I | re.U), "kadin_dogum", None),

    # Avukat
    (re.compile(r"\b(bo[sş]anma\s+avukat|aile\s+hukuk)", re.I | re.U), "avukat", "family"),
    (re.compile(r"\b(ceza\s+avukat|ceza\s+hukuk)", re.I | re.U), "avukat", "litigation"),
    (re.compile(r"\b(ticaret\s+hukuk|[sş]irket\s+avukat|kurumsal\s+avukat)", re.I | re.U),
     "avukat", "corporate"),
    (re.compile(r"\b(i[sş]\s+hukuk|i[sş]çi\s+avukat)", re.I | re.U), "avukat", "litigation"),
    (re.compile(r"\b(avukat|hukuk\s+b[uü]ros|hukuk\s+ofis)", re.I | re.U),
     "avukat", "litigation"),

    # Emlak
    (re.compile(r"\b(emlak|gayrimenkul|emlakç|m[uü]teahhit)", re.I | re.U),
     "emlak", "local"),

    # Güzellik
    (re.compile(r"\b(lazer\s+epilasyon|epilasyon)", re.I | re.U), "guzellik", "premium"),
    (re.compile(r"\b(g[uü]zellik\s+merkez|g[uü]zellik\s+salon|cilt\s+bak[ıi]m|"
                r"medikal\s+estetik)", re.I | re.U), "guzellik", "premium"),
    (re.compile(r"\b(kuaf[oö]r|berber|saç\s+tasarım|nail\s+art|t[ıi]rnak)", re.I | re.U),
     "guzellik", "routine"),
    (re.compile(r"\b(g[uü]zellik)", re.I | re.U), "guzellik", "routine"),

    # Eğitim
    (re.compile(r"\b(dil\s+kurs|ingilizce\s+kurs|almanca\s+kurs|fransizca\s+kurs)",
                re.I | re.U), "egitim", "course"),
    (re.compile(r"\b(yks|tyt|ayt|lgs|[oö]zel\s+ders|et[uü]t\s+merkez)", re.I | re.U),
     "egitim", "exam_prep"),
    (re.compile(r"\b(kurs|e[gğ]itim\s+merkez|akademi)", re.I | re.U), "egitim", "course"),

    # Ev hizmetleri
    (re.compile(r"\b(tesisat|su\s+tesisat|d[oö][sş]eme\s+ustas)", re.I | re.U),
     "ev_hizmetleri", "tesisat"),
    (re.compile(r"\b(elektrik[çc]i)", re.I | re.U), "ev_hizmetleri", "elektrik"),
    (re.compile(r"\b(boyac|tadilat|dekorasyon)", re.I | re.U), "ev_hizmetleri", "tesisat"),
    (re.compile(r"\b(beyaz\s+e[sş]ya\s+servis|kombi\s+servis)", re.I | re.U),
     "ev_hizmetleri", "tesisat"),

    # Restoran
    (re.compile(r"\b(restoran|restaurant|lokanta|kebab[çc]|pide\s+salon|"
                r"k[oö]fteci|bal[ıi]k[çc]ı|et\s+lokanta)", re.I | re.U), "restoran", None),
    (re.compile(r"\b(kafe|cafe|kahve\s+d[uü]kkan|brunch)", re.I | re.U), "restoran", None),
]

# Stop-words to strip from the search string after we've extracted city/district.
_LOCATION_STRIP_WORDS = {
    "icin", "için", "ile", "yakin", "yakın", "yakininda", "yakınında",
    "civari", "civarı", "yakinindaki", "yakınındaki", "ve", "ya", "veya",
    "bul", "bulur", "bulan", "ara", "ariyorum", "arıyorum", "arıyor",
    "lazim", "lazım", "gerekli", "lutfen", "lütfen",
    "bana", "bir", "tane",
    # Orphan locative/ablative/dative suffixes left after apostrophe split.
    "de", "da", "te", "ta",
    "den", "dan", "ten", "tan",
    "deki", "daki", "teki", "taki",
    "nde", "nda", "nte", "nta",
    "nden", "ndan",
    "ye", "ya", "e", "a",
    "nin", "nın", "nun", "nün",
}

# Common Turkish suffixes attached to place names: "kadıköyde", "izmirde", "ankaranın"
# Tried longest-first so we don't strip too little.
_PLACE_SUFFIXES = (
    "ndeki", "ndaki",
    "nden", "ndan",
    "nde", "nda",
    "deki", "daki", "teki", "taki",
    "den", "dan", "ten", "tan",
    "nin", "nın", "nun", "nün",
    "de", "da", "te", "ta",
    "ye", "ya",
    "in", "ın", "un", "ün",  # genitive: kadıköyün → kadıköy
)


def _normalize(s: str) -> str:
    """Lowercase + ASCII-fold (Turkish-aware)."""
    s = s.strip().lower()
    s = "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )
    s = s.replace("ı", "i").replace("ğ", "g").replace("ş", "s")
    s = s.replace("ö", "o").replace("ü", "u").replace("ç", "c")
    return s


def _strip_place_suffix(token: str) -> str:
    """Remove a single trailing Turkish locative/dative/ablative suffix, if any."""
    for suf in _PLACE_SUFFIXES:
        if len(token) > len(suf) + 2 and token.endswith(suf):
            return token[: -len(suf)]
    return token


def _find_location(query: str) -> tuple[str | None, str | None, list[str]]:
    """
    Return (district_display, city_display, leftover_tokens).
    Leftover tokens are the original words minus the location ones.
    """
    raw_tokens = re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+", query, flags=re.UNICODE)
    if not raw_tokens:
        return None, None, []

    # Per-token normalization: lowercase+fold, then try suffix-strip if no direct hit.
    norm_tokens = [_normalize(t) for t in raw_tokens]
    stripped = [_strip_place_suffix(nt) for nt in norm_tokens]

    district = None
    city = None
    consumed_idx: set[int] = set()

    # First pass: districts (more specific). Try both the normalized token
    # and the suffix-stripped form (catches "kadıköyde" → "kadikoy").
    for i in range(len(raw_tokens)):
        for candidate in (norm_tokens[i], stripped[i]):
            if candidate in _DISTRICTS:
                district_display, default_city = _DISTRICTS[candidate]
                district = district_display
                if not city:
                    city = default_city
                consumed_idx.add(i)
                break
        if district:
            break

    # Second pass: explicit city (overrides default city from district).
    for i in range(len(raw_tokens)):
        if i in consumed_idx:
            continue
        for candidate in (norm_tokens[i], stripped[i]):
            if candidate in _CITIES:
                city = _CITIES[candidate]
                consumed_idx.add(i)
                break

    leftover = [
        raw_tokens[i]
        for i in range(len(raw_tokens))
        if i not in consumed_idx and norm_tokens[i] not in _LOCATION_STRIP_WORDS
    ]
    return district, city, leftover


def _detect_sector(query_remainder: str) -> tuple[str | None, str | None]:
    """Find the sector + optional sub_sector hint by scanning the noun phrase."""
    for pattern, sector, sub in _SECTOR_KEYWORDS:
        if pattern.search(query_remainder):
            return sector, sub
    return None, None


def parse_search_query(query: str) -> dict:
    """
    Parse a natural-language search query into structured fields.
    Always returns a dict; never raises.
    """
    raw = (query or "").strip()
    if not raw:
        return {
            "raw_query":       "",
            "city":            None,
            "district":        None,
            "category":        "",
            "sector":          None,
            "sub_sector_hint": None,
            "search_string":   "",
        }

    district, city, leftover_tokens = _find_location(raw)
    category = " ".join(leftover_tokens).strip() or raw
    sector, sub_hint = _detect_sector(category)

    # Build Maps search string. Prefer the user's original noun phrase verbatim
    # — Apify Google Places handles Turkish-language queries well.
    search_string = category if category else raw

    return {
        "raw_query":       raw,
        "city":            city,
        "district":        district,
        "category":        category,
        "sector":          sector,
        "sub_sector_hint": sub_hint,
        "search_string":   search_string,
    }
