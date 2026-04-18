"""
Beauty Sub-Sector Detection

Güzellik sektörünü hizmet tipine göre 2 alt kategoriye ayırır:
  aesthetic — lazer, dolgu, cilt bakımı (yüksek ticket, seans bazlı)
  routine   — kuaför, manikür, genel güzellik (tekrar müşteri odaklı, default)
"""

AESTHETIC_NAMES = [
    "lazer", "epilasyon", "cilt", "esthetic", "beauty clinic",
    "dolgu", "botoks", "botox", "medikal", "medical",
    "dermatoloji", "güzellik kliniği", "guzellik klinigi",
    "led terapi", "peeling", "mezoterapi",
]

AESTHETIC_CATEGORIES = [
    "skin care", "laser", "aesthetic", "beauty clinic",
    "medical spa", "medi spa", "cosmetic",
]

ROUTINE_NAMES = [
    "kuaför", "kuafor", "berber", "saç", "sac", "manikür", "manikur",
    "pedikür", "pedikur", "tırnak", "tirnak", "güzellik salonu",
    "guzellik salonu", "wax", "ağda", "agda",
]


def detect_beauty_subsector(lead: dict) -> str:
    """
    Güzellik lead'ini alt kategoriye sınıflandırır.
    return: "aesthetic" | "routine"
    """
    isim = (lead.get("isim") or "").lower()
    kategoriler = " ".join(lead.get("categories") or []).lower()

    if any(x in isim for x in AESTHETIC_NAMES) or \
       any(x in kategoriler for x in AESTHETIC_CATEGORIES):
        return "aesthetic"

    return "routine"


def get_subsector_hook_language(subsector: str) -> str:
    """Outreach / audit mesajları için alt sektör kayıp dili."""
    return {
        "aesthetic": "yüksek değerli müşteri kaybı — görüyor ama randevuya dönüşmüyor",
        "routine": "potansiyel müşteri kaybı — net bilgi olmadığı için başka salone gidiyor",
    }.get(subsector, "müşteri kaybı")
