"""
Real Estate Sub-Sector Detection

Emlak sektörünü portföy ve hedef kitleye göre 2 alt kategoriye ayırır:
  luxury  — yüksek değerli portföy, marka/prestij odaklı
  local   — bireysel danışman, küçük ofis, genel portföy (default)
"""

LUXURY_NAMES = [
    "luxury", "lüks", "luks", "prestij", "exclusive", "premium",
    "boutique", "butik", "elite",
]

# Büyük franchise ağları → local kategorisinde değerlendirilir
# ama kurumsal ofis olduğu için local scoring daha uygundur
FRANCHISE_NAMES = [
    "remax", "re/max", "century 21", "era emlak", "era türkiye",
    "coldwell banker", "sotheby",
]

LUXURY_CATEGORIES = [
    "luxury real estate", "premium real estate", "luxury property",
]


def detect_real_estate_subsector(lead: dict) -> str:
    """
    Emlak lead'ini alt kategoriye sınıflandırır.
    return: "luxury" | "local"
    """
    isim = (lead.get("isim") or "").lower()
    kategoriler = " ".join(lead.get("categories") or []).lower()

    # Franchise → local (kurumsal ama bireysel danışman odaklı)
    if any(x in isim for x in FRANCHISE_NAMES):
        return "local"

    if any(x in isim for x in LUXURY_NAMES) or \
       any(x in kategoriler for x in LUXURY_CATEGORIES):
        return "luxury"

    return "local"


def get_subsector_hook_language(subsector: str) -> str:
    """Outreach / audit mesajları için alt sektör kayıp dili."""
    return {
        "luxury": "yüksek değerli müşteri kaybı — görünmeden karar veriliyor",
        "local": "potansiyel alıcı/satıcı kaybı — ilan veya iletişim eksikliği",
    }.get(subsector, "müşteri kaybı")
