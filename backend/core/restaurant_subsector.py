"""
Restaurant Sub-Sector Detection

Restoran lead'ini trafik kaynağına göre 2 alt kategoriye ayırır:
  social_driven — sosyal medya aktif, rezervasyona dönüşüm eksik
  maps_driven   — Google Maps odaklı, sosyal görünürlük zayıf (default)
"""

SOCIAL_NAMES = [
    "cafe", "kafe", "bistro", "brasserie", "lounge",
    "brunch", "rooftop", "konsept", "fusion",
]


def detect_restaurant_subsector(lead: dict) -> str:
    """
    Önce instagram_post_30d bakar. Yoksa website + yorum sayısını kullanır.
    return: "social_driven" | "maps_driven"
    """
    ig_posts = lead.get("instagram_post_30d") or lead.get("instagram_post_90d") or 0
    if ig_posts > 5:
        return "social_driven"

    has_website = bool(lead.get("website"))
    reviews = lead.get("yorum_sayisi") or 0
    isim = (lead.get("isim") or "").lower()

    # Web varlığı + makul yorum sayısı → sosyal kanallarda büyük ihtimalle aktif
    if has_website and reviews >= 30:
        return "social_driven"

    if any(x in isim for x in SOCIAL_NAMES) and has_website:
        return "social_driven"

    return "maps_driven"
