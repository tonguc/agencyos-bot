"""
SERP Enricher — SerpAPI üzerinden Google arama sinyalleri (ads + organik + AI Overview).

Arama başına TEK çağrı yapılır; sonuç tüm batch'e uygulanır.
Her lead için doldurduğu alanlar:
  market_ads_pressure   bool   — sektörde reklam var mı?
  competitor_ads_count  int    — kaç rakip reklam veriyor?
  self_ads_visible      bool   — lead'in kendi sitesi reklam veriyor mu?
  in_organic_top10      bool   — lead organik top-10'da mı?
  organic_position      int|None — organik sıralama (1-10)
  has_ai_overview       bool   — bu sorgu için AI Overview var mı?
  in_ai_overview        bool   — lead'in sitesi AI Overview'da mı?

enrich_keyword_coverage() 3 paralel web sorgusuyla high-intent coverage ölçer:
  keyword_coverage_score  int  0-3  (kaç sorguda lead top-10'da görünüyor)
  Sorgular: "{ilce} {category}" · "{ilce} acil {category}" · "{ilce} {category} fiyat"
"""

from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import urlparse

import requests

from config import settings

logger = logging.getLogger(__name__)

_SERPAPI_URL = "https://serpapi.com/search"


def _extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return None


def _extract_urls_from_text(text: str) -> list[str]:
    """Extract URLs from plain text (for AI Overview parsing)."""
    url_pattern = re.compile(r"https?://[^\s\"'>]+")
    return url_pattern.findall(text)


def _fetch_serp_sync(query: str) -> dict:
    """
    SerpAPI Google Search — ads, organic results ve AI Overview döndürür.

    Returns:
    {
      "market_ads_pressure": bool,
      "competitor_ads_count": int,
      "ad_domains": set[str],
      "has_ai_overview": bool,
      "ai_overview_domains": set[str],
      "organic_domains": list[tuple[str, int]],   # [(domain, position), ...]
    }
    """
    key = settings.SERPAPI_API_KEY
    if not key:
        logger.warning("SERPAPI_API_KEY tanımlı değil — SERP enrichment atlandı")
        return {}

    try:
        resp = requests.get(
            _SERPAPI_URL,
            params={
                "engine": "google",
                "q": query,
                "hl": "tr",
                "gl": "tr",
                "num": 10,
                "api_key": key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("SerpAPI çağrısı başarısız (%s): %s", query, e)
        return {}

    # ── Ads ────────────────────────────────────────────────────────────────────
    ads: list[dict] = data.get("ads") or []
    ad_domains: set[str] = set()
    for ad in ads:
        domain = _extract_domain(ad.get("link") or ad.get("displayed_link"))
        if domain:
            ad_domains.add(domain)

    # ── Organic results ────────────────────────────────────────────────────────
    organic_results: list[dict] = data.get("organic_results") or []
    organic_domains: list[tuple[str, int]] = []
    for item in organic_results:
        pos = item.get("position")
        link = item.get("link")
        domain = _extract_domain(link)
        if domain and pos is not None:
            organic_domains.append((domain, int(pos)))

    # ── AI Overview ────────────────────────────────────────────────────────────
    ai_overview_data = data.get("ai_overview") or {}
    has_ai_overview = bool(ai_overview_data)
    ai_overview_domains: set[str] = set()

    if has_ai_overview:
        # Extract domains from text_blocks
        text_blocks = ai_overview_data.get("text_blocks") or []
        for block in text_blocks:
            # Inline links within text blocks
            for link_item in (block.get("links") or []):
                url = link_item.get("url") or link_item.get("href")
                domain = _extract_domain(url)
                if domain:
                    ai_overview_domains.add(domain)
            # Plain text may also contain URLs
            snippet = block.get("snippet") or block.get("text") or ""
            for url in _extract_urls_from_text(snippet):
                domain = _extract_domain(url)
                if domain:
                    ai_overview_domains.add(domain)

        # Some SerpAPI versions surface sources at the top level of ai_overview
        for source in (ai_overview_data.get("sources") or []):
            url = source.get("url") or source.get("link")
            domain = _extract_domain(url)
            if domain:
                ai_overview_domains.add(domain)

        # Also check if the response has a separate "ai_overview_sources" key
        for source in (data.get("ai_overview_sources") or []):
            url = source.get("url") or source.get("link")
            domain = _extract_domain(url)
            if domain:
                ai_overview_domains.add(domain)

    result = {
        "market_ads_pressure": len(ad_domains) > 0,
        "competitor_ads_count": len(ad_domains),
        "ad_domains": ad_domains,
        "has_ai_overview": has_ai_overview,
        "ai_overview_domains": ai_overview_domains,
        "organic_domains": organic_domains,
    }

    logger.info(
        "SerpAPI: q=%r ads=%d organic=%d ai_overview=%s ai_domains=%d",
        query,
        len(ad_domains),
        len(organic_domains),
        has_ai_overview,
        len(ai_overview_domains),
    )
    return result


async def fetch_serp_data(query: str) -> dict:
    """Async wrapper for _fetch_serp_sync."""
    return await asyncio.to_thread(_fetch_serp_sync, query)


# ---------------------------------------------------------------------------
# Backward-compatible aliases (used by search_service before rename)
# ---------------------------------------------------------------------------

async def fetch_ads(query: str) -> list[dict]:
    """
    DEPRECATED — retained for backward compatibility.
    Use fetch_serp_data() instead, which returns the full SERP dict.
    Returns the raw ads list for callers that only need ads.
    """
    logger.warning(
        "fetch_ads() is deprecated — use fetch_serp_data() + apply_serp_data() instead"
    )
    key = settings.SERPAPI_API_KEY
    if not key:
        return []
    try:
        resp = await asyncio.to_thread(
            requests.get,
            _SERPAPI_URL,
            params={
                "engine": "google",
                "q": query,
                "hl": "tr",
                "gl": "tr",
                "num": 10,
                "api_key": key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("ads") or []
    except Exception as e:
        logger.warning("SerpAPI (legacy fetch_ads) başarısız (%s): %s", query, e)
        return []


def apply_ads_data(leads: list[dict], ads: list[dict]) -> list[dict]:
    """
    DEPRECATED — retained for backward compatibility.
    Use apply_serp_data() instead.
    """
    logger.warning(
        "apply_ads_data() is deprecated — use apply_serp_data() instead"
    )
    if not ads:
        for lead in leads:
            lead.setdefault("market_ads_pressure", False)
            lead.setdefault("competitor_ads_count", 0)
            lead.setdefault("self_ads_visible", False)
        return leads

    ad_domains = {_extract_domain(ad.get("link") or ad.get("displayed_link")) for ad in ads}
    ad_domains.discard(None)

    for lead in leads:
        lead_domain = _extract_domain(lead.get("website"))
        lead["market_ads_pressure"] = True
        lead["competitor_ads_count"] = len(ad_domains)
        lead["self_ads_visible"] = lead_domain is not None and lead_domain in ad_domains

    return leads


def apply_serp_data(leads: list[dict], serp: dict) -> list[dict]:
    """
    SERP sonuçlarını lead listesine uygular (in-place güncelleme).

    Batch-wide fields (aynı sorgudan gelir, tüm leadlere eşit uygulanır):
      market_ads_pressure, competitor_ads_count, has_ai_overview

    Per-lead fields (lead'in domain'ine göre hesaplanır):
      self_ads_visible, in_organic_top10, organic_position, in_ai_overview
    """
    if not serp:
        for lead in leads:
            lead.setdefault("market_ads_pressure", False)
            lead.setdefault("competitor_ads_count", 0)
            lead.setdefault("self_ads_visible", False)
            lead.setdefault("in_organic_top10", False)
            lead.setdefault("organic_position", None)
            lead.setdefault("has_ai_overview", False)
            lead.setdefault("in_ai_overview", False)
        return leads

    # Batch-wide signals
    market_ads_pressure: bool = serp.get("market_ads_pressure", False)
    competitor_ads_count: int = serp.get("competitor_ads_count", 0)
    has_ai_overview: bool = serp.get("has_ai_overview", False)
    ad_domains: set[str] = serp.get("ad_domains") or set()
    ai_overview_domains: set[str] = serp.get("ai_overview_domains") or set()

    # Build organic_position lookup: domain → position
    organic_lookup: dict[str, int] = {
        domain: pos for domain, pos in (serp.get("organic_domains") or [])
    }

    for lead in leads:
        lead_domain = _extract_domain(lead.get("website"))

        lead["market_ads_pressure"] = market_ads_pressure
        lead["competitor_ads_count"] = competitor_ads_count
        lead["has_ai_overview"] = has_ai_overview

        if lead_domain:
            lead["self_ads_visible"] = lead_domain in ad_domains
            lead["in_organic_top10"] = lead_domain in organic_lookup
            lead["organic_position"] = organic_lookup.get(lead_domain)
            lead["in_ai_overview"] = lead_domain in ai_overview_domains
        else:
            lead["self_ads_visible"] = False
            lead["in_organic_top10"] = False
            lead["organic_position"] = None
            lead["in_ai_overview"] = False

    return leads


async def enrich_keyword_coverage(
    leads: list[dict],
    ilce: str | None,
    category: str,
) -> list[dict]:
    """
    High-intent keyword coverage: 3 paralel web araması, batch başına 3 SerpAPI çağrısı.

    Sorgular:
      1. "{ilce} {category}"          — temel lokal sorgu
      2. "{ilce} acil {category}"     — acil/aciliyet niyeti
      3. "{ilce} {category} fiyat"    — satın alma niyeti

    Her lead'e keyword_coverage_score (0-3) set eder: kaç sorguda top-10'da görünüyor.
    in_organic_top10 da temel sorgudan güncellenir.

    Lead'in sitesi yoksa → coverage=0 (zaten FIRSAT, scorer bonus verir).
    SERPAPI_API_KEY yoksa → tüm leadlere coverage=None (scorer bu alanı atlar).
    """
    if not settings.SERPAPI_API_KEY:
        logger.debug("enrich_keyword_coverage: SERPAPI_API_KEY yok, atlanıyor")
        return leads

    if not leads or not category:
        for lead in leads:
            lead.setdefault("keyword_coverage_score", 0)
        return leads

    prefix = f"{ilce} " if ilce else ""
    queries = [
        f"{prefix}{category}",
        f"{prefix}acil {category}",
        f"{prefix}{category} fiyat",
    ]

    serp_results = await asyncio.gather(
        *[fetch_serp_data(q) for q in queries],
        return_exceptions=True,
    )

    for lead in leads:
        domain = _extract_domain(lead.get("website"))
        count = 0

        for i, serp in enumerate(serp_results):
            if isinstance(serp, Exception) or not isinstance(serp, dict) or not serp:
                continue
            organic_lookup: dict[str, int] = {
                d: p for d, p in (serp.get("organic_domains") or [])
            }
            if domain and domain in organic_lookup:
                count += 1
                if i == 0:
                    lead["in_organic_top10"] = True
                    lead["organic_position"] = organic_lookup[domain]

        if domain and lead.get("in_organic_top10") is None:
            lead["in_organic_top10"] = False

        lead["keyword_coverage_score"] = count

    logger.info(
        "keyword_coverage: ilce=%r cat=%r leads=%d queries=%s",
        ilce, category, len(leads), queries,
    )
    return leads
