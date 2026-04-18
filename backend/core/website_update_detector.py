"""
Website Update Detector

Bir web sitesinin ne kadar güncel olduğunu çoklu kaynaktan tahmin eder.
Kesin tarih bulunamazsa confidence düşürülür, scoring nötr kalır.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import List

import requests

logger = logging.getLogger(__name__)

TIMEOUT = 10

TURKISH_MONTHS = {
    "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4,
    "mayıs": 5, "haziran": 6, "temmuz": 7, "ağustos": 8,
    "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
    # ascii variants
    "subat": 2, "mayis": 5, "eylul": 9, "kasim": 11, "aralik": 12,
}

BLOG_PATHS = ["/blog", "/haberler", "/news", "/articles", "/yazilar", "/duyurular"]

_FOOTER_YEAR_RE = re.compile(r"(?:©|copyright|\btelif\b)[^\d]*(\d{4})", re.I)
_YEAR_RE = re.compile(r"\b(20\d{2})\b")


# --------------------------------------------------
# DATE UTILITIES
# --------------------------------------------------

def extract_dates_from_text(text: str) -> List[datetime]:
    """HTML / text içinden datetime listesi çıkarır."""
    found: list[datetime] = []
    now = datetime.now(timezone.utc)
    text_lower = text.lower()

    # ISO: 2024-03-12
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        try:
            d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
            if d <= now:
                found.append(d)
        except ValueError:
            pass

    # dd/mm/yyyy or dd.mm.yyyy
    for m in re.finditer(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b", text):
        try:
            d = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), tzinfo=timezone.utc)
            if d <= now:
                found.append(d)
        except ValueError:
            pass

    # "12 Mart 2024" or "Mart 2024"
    month_pattern = re.compile(
        r"\b(\d{1,2}\s+)?(" + "|".join(TURKISH_MONTHS.keys()) + r")\s+(\d{4})\b",
        re.I,
    )
    for m in month_pattern.finditer(text_lower):
        try:
            day = int(m.group(1).strip()) if m.group(1) else 1
            month = TURKISH_MONTHS[m.group(2)]
            year = int(m.group(3))
            d = datetime(year, month, day, tzinfo=timezone.utc)
            if d <= now:
                found.append(d)
        except (ValueError, KeyError):
            pass

    return found


def calculate_days_diff(date: datetime) -> int:
    """Verilen tarih ile bugün arasındaki gün farkı."""
    now = datetime.now(timezone.utc)
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    return max(0, (now - date).days)


def _most_recent_days(dates: list[datetime]) -> int | None:
    if not dates:
        return None
    return calculate_days_diff(max(dates))


def _fetch(url: str, method: str = "get", **kwargs) -> requests.Response | None:
    try:
        fn = getattr(requests, method)
        return fn(
            url,
            timeout=TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (AgencyOS/2)"},
            allow_redirects=True,
            **kwargs,
        )
    except Exception as e:
        logger.debug("Fetch hatasi (%s %s): %s", method.upper(), url, e)
        return None


# --------------------------------------------------
# SOURCE STRATEGIES
# --------------------------------------------------

def _try_header(url: str) -> dict | None:
    """HEAD isteğiyle Last-Modified header'ı kontrol et."""
    resp = _fetch(url, method="head")
    if not resp:
        return None
    lm = resp.headers.get("Last-Modified") or resp.headers.get("last-modified")
    if not lm:
        return None
    try:
        from email.utils import parsedate_to_datetime
        date = parsedate_to_datetime(lm)
        days = calculate_days_diff(date)
        logger.debug("Header Last-Modified: %s → %d gün", lm, days)
        return {"last_update_days": days, "confidence": 0.6, "source": "header"}
    except Exception:
        return None


def _try_sitemap(base_url: str) -> dict | None:
    """sitemap.xml içindeki <lastmod> tarihlerini kontrol et."""
    sitemap_url = base_url.rstrip("/") + "/sitemap.xml"
    resp = _fetch(sitemap_url)
    if not resp or not resp.ok:
        return None

    dates = extract_dates_from_text(resp.text)
    for m in re.finditer(r"<lastmod>([^<]+)</lastmod>", resp.text, re.I):
        dates.extend(extract_dates_from_text(m.group(1)))

    days = _most_recent_days(dates)
    if days is None:
        return None
    logger.debug("Sitemap lastmod: %d gün", days)
    return {"last_update_days": days, "confidence": 0.8, "source": "sitemap"}


def _try_blog(base_url: str) -> dict | None:
    """Blog / haber sayfalarındaki son içeriğin tarihini bul."""
    base = base_url.rstrip("/")
    for path in BLOG_PATHS:
        resp = _fetch(base + path)
        if not resp or not resp.ok:
            continue
        dates = extract_dates_from_text(resp.text[:50_000])
        if not dates:
            continue
        days = _most_recent_days(dates)
        if days is not None:
            logger.debug("Blog (%s) → %d gün", path, days)
            return {"last_update_days": days, "confidence": 0.9, "source": "blog"}
    return None


def _try_footer(html: str) -> dict | None:
    """HTML footer içindeki copyright yılını bul."""
    years = [int(m.group(1)) for m in _FOOTER_YEAR_RE.finditer(html)]
    if not years:
        footer_match = re.search(r"<footer[^>]*>(.*?)</footer>", html, re.I | re.S)
        if footer_match:
            years = [int(m) for m in _YEAR_RE.findall(footer_match.group(1))]

    if not years:
        return None

    latest_year = max(years)
    current_year = datetime.now().year
    approx_days = (current_year - latest_year) * 365
    logger.debug("Footer yıl: %d → yaklaşık %d gün", latest_year, approx_days)
    return {
        "last_update_days": max(0, approx_days),
        "confidence": 0.3,
        "source": "footer",
    }


# --------------------------------------------------
# MAIN DETECTOR
# --------------------------------------------------

async def detect_website_update(url: str) -> dict:
    """
    Web sitesinin son güncelleme tarihini çoklu kaynaktan tahmin eder.

    Öncelik: blog > sitemap > header > footer > none

    Return:
    {
      "last_update_days": int | None,
      "confidence": float,   # 0.0 – 1.0
      "source": "blog" | "sitemap" | "header" | "footer" | "none"
    }
    """
    if not url:
        return {"last_update_days": None, "confidence": 0.0, "source": "none"}

    result = await asyncio.to_thread(_try_blog, url)
    if result:
        return result

    result = await asyncio.to_thread(_try_sitemap, url)
    if result:
        return result

    result = await asyncio.to_thread(_try_header, url)
    if result:
        return result

    resp = await asyncio.to_thread(_fetch, url)
    if resp and resp.ok:
        result = _try_footer(resp.text[:100_000])
        if result:
            return result

    logger.debug("Website güncelleme verisi bulunamadı: %s", url)
    return {"last_update_days": None, "confidence": 0.0, "source": "none"}
