"""
Ev Hizmetleri Sub-Sector Detection

Hizmet sektörünü iş modeline göre 3 alt kategoriye ayırır:
  tesisat   — sıhhi tesisatçı, su/boru/kalorifer
  elektrik  — elektrikçi, tesisat, aydınlatma
  tadilat   — boyacı, tadilatçı, renovasyon (default)
"""

TESISAT_NAMES = [
    "tesisatçı", "tesisatci", "sıhhi tesisat", "sihhi tesisat",
    "su tesisatı", "su tesisati", "tesisat", "musluk", "kalorifer",
    "petek", "tıkanıklık", "tikaniklik", "boru",
]

TESISAT_CATEGORIES = [
    "plumber", "plumbing", "sihhi tesisat",
]

ELEKTRIK_NAMES = [
    "elektrikçi", "elektrikci", "elektrik",
    "elektrik tesisatı", "elektrik tamiri", "aydınlatma",
    "sigorta paneli", "elektrik ustası", "elektrik ustaси",
]

ELEKTRIK_CATEGORIES = [
    "electrician", "electrical contractor", "electrical",
]

TADILAT_NAMES = [
    "tadilat", "boyacı", "boyaci", "boya badana", "badana",
    "alçı", "alcı", "alçıpan", "alcipan", "tamirat",
    "renovasyon", "dekorasyon", "iç mimar", "ic mimar",
]

TADILAT_CATEGORIES = [
    "painter", "general contractor", "renovation",
    "home improvement", "interior",
]


def detect_ev_hizmetleri_subsector(lead: dict) -> str:
    """
    Ev hizmetleri lead'ini alt kategoriye sınıflandırır.
    return: "tesisat" | "elektrik" | "tadilat"
    """
    isim = (lead.get("isim") or "").lower()
    kategoriler = " ".join(lead.get("categories") or []).lower()

    if any(x in isim for x in TESISAT_NAMES) or \
       any(x in kategoriler for x in TESISAT_CATEGORIES):
        return "tesisat"

    if any(x in isim for x in ELEKTRIK_NAMES) or \
       any(x in kategoriler for x in ELEKTRIK_CATEGORIES):
        return "elektrik"

    if any(x in isim for x in TADILAT_NAMES) or \
       any(x in kategoriler for x in TADILAT_CATEGORIES):
        return "tadilat"

    return "tadilat"


def get_subsector_hook_language(subsector: str) -> str:
    return {
        "tesisat":  "iş kaybı — acil aramada görünmüyor",
        "elektrik": "iş kaybı — acil aramada görünmüyor",
        "tadilat":  "proje kaybı — portföy yok, güven kurulmuyor",
    }.get(subsector, "iş kaybı")
