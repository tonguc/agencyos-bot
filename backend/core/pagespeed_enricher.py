"""
PageSpeed Enricher — Google PageSpeed Insights API ile mobil hız testi.

Batch başına lead sayısı kadar çağrı (her site için 1), max 5 eşzamanlı.
API key olmadan da çalışır (ücretsiz, ~100/gün limit); key ile 400 QPS.

Her lead için:
  mobile_speed_score  int   0-100  (Lighthouse Performance skoru × 100)
  mobile_lcp          float        LCP saniye (Largest Contentful Paint)
  mobile_fcp          float        FCP saniye (First Contentful Paint)
"""

from __future__ import annotations

import asyncio
import logging

import requests

logger = logging.getLogger(__name__)

_PSI_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
_MAX_CONCURRENT = 5


def _parse_seconds(display: str | None) -> float | None:
    """'3.2 s' veya '840 ms' → float saniye. Ayrıştırma başarısız → None."""
    if not display:
        return None
    display = display.strip()
    try:
        if "ms" in display:
            return round(float(display.replace("ms", "").strip()) / 1000, 2)
        return round(float(display.replace("s", "").strip()), 2)
    except ValueError:
        return None


async def _check_one(url: str, api_key: str) -> dict | None:
    params: dict = {"url": url, "strategy": "MOBILE", "category": "PERFORMANCE"}
    if api_key:
        params["key"] = api_key
    try:
        resp = await asyncio.to_thread(
            requests.get, _PSI_URL, params=params, timeout=25
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.debug("PageSpeed başarısız (%s): %s", url, e)
        return None

    lhr = data.get("lighthouseResult") or {}
    perf_score = (lhr.get("categories") or {}).get("performance", {}).get("score")
    audits = lhr.get("audits") or {}

    return {
        "mobile_speed_score": int(round(perf_score * 100)) if perf_score is not None else None,
        "mobile_lcp": _parse_seconds((audits.get("largest-contentful-paint") or {}).get("displayValue")),
        "mobile_fcp": _parse_seconds((audits.get("first-contentful-paint") or {}).get("displayValue")),
    }


async def enrich_pagespeed(leads: list[dict], api_key: str = "") -> list[dict]:
    """
    Sitesi olan her lead için mobil PageSpeed skoru çeker.
    Leadleri in-place günceller; site olmayanları atlar.
    """
    sem = asyncio.Semaphore(_MAX_CONCURRENT)

    async def _safe(lead: dict) -> None:
        url = lead.get("website")
        if not url:
            return
        async with sem:
            result = await _check_one(url, api_key)
        if result:
            lead.update(result)

    await asyncio.gather(*[_safe(l) for l in leads], return_exceptions=True)

    scored = sum(1 for l in leads if l.get("mobile_speed_score") is not None)
    logger.info("PageSpeed: %d/%d lead skorlandı", scored, len(leads))
    return leads
