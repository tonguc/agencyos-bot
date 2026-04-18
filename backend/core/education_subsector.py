"""
Education Sub-Sector Detection

Eğitim sektörünü hizmet modeline göre 2 alt kategoriye ayırır:
  course   — kurs, dil okulu, sınav hazırlık, akademi (grup/toplu eğitim)
  coaching — bireysel koçluk, danışmanlık, mentörlük (default)
"""

COURSE_NAMES = [
    "kurs", "academy", "akademi", "dil okulu", "dil kursu",
    "ingilizce", "yds", "toefl", "ielts", "yökdil",
    "sınav hazırlık", "sinav hazirlik", "lgs", "yks", "kpss",
    "eğitim merkezi", "egitim merkezi", "okul", "school",
]

COURSE_CATEGORIES = [
    "school", "course", "education center", "language school",
    "tutoring", "test preparation",
]

COACHING_NAMES = [
    "koç", "koc", "coach", "coaching", "mentor", "danışman", "danisman",
    "trainer", "eğitmen", "egitmen", "yaşam koçu", "yasam kocu",
    "kariyer", "liderlik", "gelişim", "gelisim",
]


def detect_education_subsector(lead: dict) -> str:
    """
    Eğitim lead'ini alt kategoriye sınıflandırır.
    return: "course" | "coaching"
    """
    isim = (lead.get("isim") or "").lower()
    kategoriler = " ".join(lead.get("categories") or []).lower()

    if any(x in isim for x in COURSE_NAMES) or \
       any(x in kategoriler for x in COURSE_CATEGORIES):
        return "course"

    return "coaching"


def get_subsector_hook_language(subsector: str) -> str:
    """Outreach / audit mesajları için alt sektör kayıp dili."""
    return {
        "course": "kayıt kaybı — ilgi var ama detay ve güven göremeden çıkıyor",
        "coaching": "müşteri kaybı — takip ediyor ama birebir çalışmaya dönüşmüyor",
    }.get(subsector, "müşteri kaybı")
