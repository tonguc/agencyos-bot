"""
Lawyer Sub-Sector Detection

Avukat sektörünü müşteri tipine göre 2 alt kategoriye ayırır:
  corporate   — hukuk bürosu, kurumsal danışmanlık, B2B
  litigation  — bireysel avukat, dava odaklı (default)
"""

CORPORATE_NAMES = [
    "hukuk bürosu", "hukuk burosu", "law firm", "danışmanlık", "danismanlik",
    "legal", "avukatlık ortaklığı", "avukatlik ortakligi",
]

CORPORATE_CATEGORIES = [
    "corporate", "business law", "commercial", "law firm",
    "legal services", "corporate law",
]


def detect_lawyer_subsector(lead: dict) -> str:
    """
    Avukat lead'ini alt kategoriye sınıflandırır.
    return: "corporate" | "litigation"
    """
    isim = (lead.get("isim") or "").lower()
    kategoriler = " ".join(lead.get("categories") or []).lower()

    if any(x in isim for x in CORPORATE_NAMES) or \
       any(x in kategoriler for x in CORPORATE_CATEGORIES):
        return "corporate"

    return "litigation"


def get_subsector_hook_language(subsector: str) -> str:
    """Outreach / audit mesajları için alt sektör kayıp dili."""
    return {
        "litigation": "potansiyel müvekkil kaybı — bulunamıyor veya güven oluşmuyor",
        "corporate": "kurumsal müşteri kaybı — görünürlük ve otorite eksikliği",
    }.get(subsector, "müvekkil kaybı")
