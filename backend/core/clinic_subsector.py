"""
Clinic Sub-Sector Detection

Klinik sektörünü satın alma psikolojisine göre 3 alt kategoriye ayırır:
  aesthetic  — yüksek ticket, görsel/sonuç odaklı (plastik, estetik, dermatoloji)
  trust      — güven/uzmanlık odaklı (psikolog, diyetisyen, fizyoterapi)
  general    — ulaşılabilirlik/hız odaklı (genel muayenehane, aile hekimi)
"""


AESTHETIC_NAMES = [
    "plastik", "estetik", "saç ekimi", "hair transplant",
    "implant", "dermatoloji", "lazer", "dolgu", "botoks",
    "rinoplasti", "liposuction",
]

AESTHETIC_CATEGORIES = [
    "esthetic", "cosmetic", "dermatology", "implant",
    "plastic surgery", "hair transplant",
]

TRUST_NAMES = [
    "psikolog", "psikiyatri", "diyetisyen", "fizyoterapi",
    "kadın doğum", "kadin dogum", "onkoloji", "nöroloji", "noroloji",
    "romatoloji", "endokrinoloji",
]

TRUST_CATEGORIES = [
    "psychologist", "psychiatrist", "nutrition", "nutritionist",
    "physiotherapy", "physical therapy", "gynecology", "therapy",
]


def detect_clinic_subsector(lead: dict) -> str:
    """
    Klinik lead'ini alt kategoriye sınıflandırır.
    return: "aesthetic" | "trust" | "general"
    """
    isim = (lead.get("isim") or "").lower()
    kategoriler = " ".join(lead.get("categories") or []).lower()

    if any(x in isim for x in AESTHETIC_NAMES) or \
       any(x in kategoriler for x in AESTHETIC_CATEGORIES):
        return "aesthetic"

    if any(x in isim for x in TRUST_NAMES) or \
       any(x in kategoriler for x in TRUST_CATEGORIES):
        return "trust"

    return "general"


def get_subsector_hook_language(subsector: str) -> str:
    """Outreach / audit mesajları için alt sektör kayıp dili."""
    return {
        "aesthetic": "yüksek değerli hasta kaybı",
        "trust": "güven oluşmuyor, danışan kaybı",
        "general": "ulaşılamama / randevu gecikmesi",
    }.get(subsector, "hasta kaybı")
