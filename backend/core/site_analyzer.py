"""
Site Analyzer — her lead'in web sitesini ziyaret ederek dönüşüm sinyallerini çıkarır.

Async HTTP ile paralel çalışır; max_concurrent semaphore ile throttle eder.
Site fetch başarısız olursa o lead için tüm alanlar False bırakılır.

Her lead için doldurduğu alanlar:
  has_cta              bool — randevu/iletişim/rezervasyon/booking butonu
  has_whatsapp         bool — wa.me veya whatsapp linki
  has_online_booking   bool — online booking/randevu sistemi
  has_phone_visible    bool — HTML'de telefon numarası
  has_form             bool — <form> tag'i var
  site_durumu          str  — "iyi" | "zayif" (CTA/booking varsa "iyi")

Not: site_durumu "yok" değerini korumaz — website alanı None ise lead atlanır.
"yok" zaten lead_collector._site_durumu tarafından atanır.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urlparse

import httpx
import requests

logger = logging.getLogger(__name__)


async def check_indexed_pages(domain: str) -> int | None:
    """
    Query SerpAPI with `site:domain` to get approximate Google indexed page count.
    Returns None if SERPAPI_API_KEY is not set or request fails.
    """
    from config import settings  # local import to avoid circular
    key = settings.SERPAPI_API_KEY
    if not key or not domain:
        return None
    try:
        params = {
            "engine": "google",
            "q": f"site:{domain}",
            "gl": "tr",
            "hl": "tr",
            "num": 1,
            "api_key": key,
        }
        r = await asyncio.to_thread(
            requests.get, "https://serpapi.com/search",
            params=params, timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        total = data.get("search_information", {}).get("total_results")
        return int(total) if total is not None else None
    except Exception as e:
        logger.debug("indexed_pages kontrol başarısız (%s): %s", domain, e)
        return None

_USER_AGENT = "Mozilla/5.0 (compatible; AgencyOS/1.0)"

# ── Regex patterns ─────────────────────────────────────────────────────────────

# Turkish phone numbers: 0[235]XXXXXXXXX or +90XXXXXXXXXX
_PHONE_RE = re.compile(r"(?:\+90|0)[235]\d{9}")

# WhatsApp links
_WHATSAPP_RE = re.compile(r"wa\.me|whatsapp", re.IGNORECASE)

# CTA keywords inside button/a tag text or href
_CTA_KEYWORDS_RE = re.compile(
    r"randevu|rezervasyon|appointment|book|hemen\s*ara|iletişim|contact|teklif\s*al",
    re.IGNORECASE,
)

# Online booking keywords in visible text
_BOOKING_KEYWORDS_RE = re.compile(
    r"randevu\s*al|online\s*randevu|appointment|booking|rezervasyon\s*yap",
    re.IGNORECASE,
)

# Form tag
_FORM_RE = re.compile(r"<form[\s>]", re.IGNORECASE)

# Strip all HTML tags for text-level keyword searching
_TAG_RE = re.compile(r"<[^>]+>")

# Extract href attributes
_HREF_RE = re.compile(r'href=["\']([^"\']*)["\']', re.IGNORECASE)

# Extract button/a tag inner text
_BUTTON_A_RE = re.compile(r"<(?:button|a)[^>]*>(.*?)</(?:button|a)>", re.IGNORECASE | re.DOTALL)


def _analyze_html(html: str) -> dict:
    """
    Parse HTML string and extract conversion signals.
    Returns a dict with the boolean signal fields.
    """
    # WhatsApp: check hrefs for wa.me or whatsapp
    hrefs = _HREF_RE.findall(html)
    has_whatsapp = any(_WHATSAPP_RE.search(href) for href in hrefs)

    # CTA: button/a tags that contain CTA keywords (text or href)
    has_cta = False
    for match in _BUTTON_A_RE.finditer(html):
        tag_full = match.group(0)
        inner_text = _TAG_RE.sub("", match.group(1))
        if _CTA_KEYWORDS_RE.search(inner_text) or _CTA_KEYWORDS_RE.search(tag_full):
            has_cta = True
            break

    # Online booking: any visible text on the page
    plain_text = _TAG_RE.sub(" ", html)
    has_online_booking = bool(_BOOKING_KEYWORDS_RE.search(plain_text))

    # Phone: raw HTML (phone numbers often appear as plain text)
    has_phone_visible = bool(_PHONE_RE.search(html))

    # Form
    has_form = bool(_FORM_RE.search(html))

    # site_durumu upgrade
    if has_cta or has_online_booking:
        site_durumu = "iyi"
    else:
        site_durumu = "zayif"

    return {
        "has_cta": has_cta,
        "has_whatsapp": has_whatsapp,
        "has_online_booking": has_online_booking,
        "has_phone_visible": has_phone_visible,
        "has_form": has_form,
        "site_durumu": site_durumu,
    }


def _blank_signals(site_durumu_original: Optional[str] = None) -> dict:
    """Return all-False signals dict, preserving existing site_durumu."""
    return {
        "has_cta": False,
        "has_whatsapp": False,
        "has_online_booking": False,
        "has_phone_visible": False,
        "has_form": False,
        "site_durumu": site_durumu_original or "zayif",
        "indexed_pages": None,
    }


async def _fetch_and_analyze(
    lead: dict,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    timeout: int,
) -> None:
    """
    Fetch the lead's website and update it in-place with conversion signals.
    Also checks indexed page count via SerpAPI site: query.
    If fetch fails, sets all fields to False, preserves existing site_durumu.
    """
    url = lead.get("website")
    if not url:
        return  # No website — skip; site_durumu already "yok"

    try:
        domain = urlparse(url).netloc.lstrip("www.")
    except Exception:
        domain = ""

    # Run HTML fetch and indexed pages check in parallel
    async with semaphore:
        try:
            html_task = client.get(url, timeout=timeout, follow_redirects=True)
            index_task = check_indexed_pages(domain)
            response, indexed_pages = await asyncio.gather(html_task, index_task, return_exceptions=True)
            if isinstance(response, Exception):
                logger.debug("Site fetch başarısız (%s): %s", url, response)
                signals = _blank_signals(lead.get("site_durumu"))
                signals["indexed_pages"] = indexed_pages if isinstance(indexed_pages, int) else None
                lead.update(signals)
                return
            response.raise_for_status()
            html = response.text
            lead["indexed_pages"] = indexed_pages if isinstance(indexed_pages, int) else None
        except Exception as e:
            logger.debug("Site fetch başarısız (%s): %s", url, e)
            signals = _blank_signals(lead.get("site_durumu"))
            lead.update(signals)
            return

    try:
        signals = _analyze_html(html)
        lead.update(signals)
        logger.debug(
            "Site analiz: %s → cta=%s whatsapp=%s booking=%s phone=%s form=%s durumu=%s",
            url,
            signals["has_cta"],
            signals["has_whatsapp"],
            signals["has_online_booking"],
            signals["has_phone_visible"],
            signals["has_form"],
            signals["site_durumu"],
        )
    except Exception as e:
        logger.warning("HTML ayrıştırma hatası (%s): %s", url, e)
        lead.update(_blank_signals(lead.get("site_durumu")))


async def analyze_sites(
    leads: list[dict],
    max_concurrent: int = 5,
    timeout: int = 5,
) -> list[dict]:
    """
    For each lead with a website, fetch and analyze it.
    Updates leads in-place with conversion signal fields.

    Returns the same list (mutated in-place) for easy chaining.
    """
    leads_with_sites = [l for l in leads if l.get("website")]
    if not leads_with_sites:
        logger.debug("analyze_sites: website olan lead yok, atlandı")
        return leads

    logger.info(
        "Site analizi başlıyor: %d/%d lead (max_concurrent=%d, timeout=%ds)",
        len(leads_with_sites),
        len(leads),
        max_concurrent,
        timeout,
    )

    semaphore = asyncio.Semaphore(max_concurrent)
    headers = {"User-Agent": _USER_AGENT}

    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        tasks = [
            _fetch_and_analyze(lead, client, semaphore, timeout)
            for lead in leads_with_sites
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    iyi_count = sum(1 for l in leads_with_sites if l.get("site_durumu") == "iyi")
    logger.info(
        "Site analizi tamamlandı: %d analyzed, %d 'iyi' durumunda",
        len(leads_with_sites),
        iyi_count,
    )

    return leads
