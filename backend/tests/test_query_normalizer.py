"""Query normalizer + cache key deterministic davranis testleri."""

from core.query_normalizer import normalize_query, build_search_cache_key


def test_normalize_turkish_chars():
    assert normalize_query("Beşiktaş Diş") == "besiktas dis"
    assert normalize_query("İzmir") == "izmir"
    assert normalize_query("Şişli") == "sisli"


def test_normalize_idempotent():
    q = "Beşiktaş, diş hekimi"
    once = normalize_query(q)
    twice = normalize_query(once)
    assert once == twice


def test_normalize_whitespace_collapse():
    assert normalize_query("  Beşiktaş   diş  ") == "besiktas dis"


def test_cache_key_different_queries_produce_different_keys():
    k1 = build_search_cache_key("doktor istanbul", 20)
    k2 = build_search_cache_key("doktor ankara", 20)
    assert k1 != k2


def test_cache_key_limit_in_key():
    k1 = build_search_cache_key("doktor", 20)
    k2 = build_search_cache_key("doktor", 50)
    assert k1 != k2


def test_cache_key_case_insensitive():
    k1 = build_search_cache_key("Doktor İstanbul", 20)
    k2 = build_search_cache_key("doktor istanbul", 20)
    assert k1 == k2
