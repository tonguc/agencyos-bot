"""
Ads Enricher — SerpAPI üzerinden Google Ads baskısı tespiti.

Arama başına TEK çağrı yapılır; sonuç tüm batch'e uygulanır.
Her lead için doldurduğu alanlar:
  market_ads_pressure   bool   — sektörde reklam var mı?
  competitor_ads_count  int    — kaç rakip reklam veriyor?
  self_ads_visible      bool   — lead'in kendi sitesi reklam veriyor mu?
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


def _fetch_ads_sync(query: str) -> list[dict]:
    """SerpAPI Google Search — reklamları döndürür."""
    key = settings.SERPAPI_API_KEY
    if not key:
        logger.warning("SERPAPI_API_KEY tanımlı değil — ads enrichment atlandı")
        return []
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
        return data.get("ads") or []
    except Exception as e:
        logger.warning("SerpAPI çağrısı başarısız (%s): %s", query, e)
        return []


async def fetch_ads(query: str) -> list[dict]:
    return await asyncio.to_thread(_fetch_ads_sync, query)


def apply_ads_data(leads: list[dict], ads: list[dict]) -> list[dict]:
    """
    Ads sonuçlarını lead listesine uygular (in-place güncelleme).
    """
    if not ads:
        for lead in leads:
            lead["market_ads_pressure"] = False
            lead["competitor_ads_count"] = 0
            lead["self_ads_visible"] = False
        return leads

    ad_domains = {_extract_domain(ad.get("link") or ad.get("displayed_link")) for ad in ads}
    ad_domains.discard(None)
    ads_count = len(ad_domains)

    for lead in leads:
        lead_domain = _extract_domain(lead.get("website"))
        self_ads = lead_domain is not None and lead_domain in ad_domains

        lead["market_ads_pressure"] = True
        lead["competitor_ads_count"] = ads_count
        lead["self_ads_visible"] = self_ads

    return leads
