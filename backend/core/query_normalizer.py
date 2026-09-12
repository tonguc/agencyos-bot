"""
Query Normalizer — cache key üretimi için sorguları normalize eder.

Amaç: "Beşiktaş Diş", "beşiktaş diş", "  Beşiktaş   diş " gibi
varyasyonların aynı cache key'e dönmesini sağlamak.
"""

import re
import unicodedata

CACHE_TTL_SECONDS = 14 * 24 * 3600  # 14 gün

_TR_MAP = str.maketrans("çğışöüÇĞİŞÖÜ", "cgisouCGISOu")
_PUNCT_RE = re.compile(r"[^\w\s]")
_SPACE_RE = re.compile(r"\s+")


def normalize_query(query: str) -> str:
    """
    Cache key için sorgu normalize eder.

    "Beşiktaş Diş" / "beşiktaş diş" / "  Beşiktaş,  diş " → "besiktas dis"
    """
    q = query.strip()
    q = q.translate(_TR_MAP)          # Türkçe karakter → ASCII
    q = unicodedata.normalize("NFD", q)
    q = "".join(c for c in q if unicodedata.category(c) != "Mn")  # aksan kaldır
    q = q.lower()
    q = _PUNCT_RE.sub(" ", q)         # noktalama → boşluk
    q = _SPACE_RE.sub(" ", q).strip() # çoklu boşluk → tek
    return q


def build_search_cache_key(query: str, limit: int = 20) -> str:
    """
    Normalized query + limit ile Redis cache key üretir.
    Örnek: "search:besiktas dis:20"
    """
    normalized = normalize_query(query)
    return f"search:relevance-v3:{normalized}:{limit}"
