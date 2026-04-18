import os
import re
import asyncio
import logging
from urllib.parse import urljoin

import requests

from core.utils import safe_json_parse, API_SEMAPHORE, claude_api_call
from core.prompts import build_audit_prompt

logger = logging.getLogger(__name__)

PAGESPEED_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

FALLBACK_AUDIT = {
    "ilk_izlenim": {"ne_yapiyor": "", "deger_onerisi": "belirsiz", "guven_seviyesi": "dusuk", "ilk_surtunum": ""},
    "killer_insight": {"bulgu": "Analiz yapilamadi", "etki": "", "rakam": ""},
    "ux_hatalar": [],
    "seo_aciklar": [],
    "donusum_engelleri": [],
    "hizli_kazanimlar": [],
    "reklam_firsati": {"kanal": "", "aciklama": "", "rakip_durum": "yok"},
    "skorlar": {"ux": 0, "seo": 0, "donusum": 0},
    "urgency": "dusuk",
    "lead_kalitesi": "soguk",
    "genel_skor": 0,
    "en_acitan_nokta": "",
    "kisisel_insight": "",
}

_DIGIT_RE = re.compile(r"\d")

# Form varlığını tespit eden genişletilmiş regex'ler
_FORM_PATTERNS = re.compile(
    r"<form\b"                                   # standart HTML form
    r"|class=[\"'][^\"']*(?:wpcf7|wpforms|gform_wrapper|elementor-form|hs-form)"  # WP / HubSpot
    r"|data-form-id"                             # Wix / builder formları
    r"|<iframe[^>]+(?:form|iletisim|contact)",   # gömülü iframe form
    re.I,
)
_CONTACT_PAGE_RE = re.compile(
    r'href=["\']([^"\'#]*(?:iletisim|contact|bize[\-_]ulasin|ulasin)[^"\']*)["\']',
    re.I,
)


async def _detect_form(base_url: str, html: str) -> bool:
    """Form var mı? Ana sayfada yoksa iletişim sayfasına da bakar."""
    if _FORM_PATTERNS.search(html):
        return True
    # Ana sayfada bulunamadıysa iletişim linkini bul ve kontrol et
    m = _CONTACT_PAGE_RE.search(html)
    if m:
        contact_path = m.group(1).strip()
        contact_url = urljoin(base_url, contact_path)
        if contact_url != base_url:
            try:
                resp = await asyncio.to_thread(
                    requests.get, contact_url, timeout=10,
                    headers={"User-Agent": "Mozilla/5.0 (AgencyOS)"}, allow_redirects=True,
                )
                if _FORM_PATTERNS.search(resp.text[:80_000]):
                    logger.info("Form iletisim sayfasinda bulundu: %s", contact_url)
                    return True
            except Exception as e:
                logger.debug("Contact page fetch hatasi (%s): %s", contact_url, e)
    return False


async def fetch_site_data(url: str) -> dict:
    if not url:
        logger.info("Site verisi atlandi: url yok")
        return {"url": "", "hata": True, "neden": "url yok"}

    data: dict = {
        "url": url,
        "hiz_skoru": 0,
        "title": "",
        "meta": "",
        "h1": "",
        "form_var": False,
        "tel_var": False,
        "ssl": url.startswith("https://"),
        "hata": False,
    }

    key = os.getenv("PAGESPEED_API_KEY")
    if key:
        try:
            ps = await asyncio.to_thread(
                requests.get,
                PAGESPEED_URL,
                params={"url": url, "key": key, "strategy": "mobile"},
                timeout=60,
            )
            ps.raise_for_status()
            payload = ps.json()
            score = (
                payload.get("lighthouseResult", {})
                .get("categories", {})
                .get("performance", {})
                .get("score")
            )
            if score is not None:
                data["hiz_skoru"] = int(score * 100)
        except Exception as e:
            logger.warning("PageSpeed hatasi (%s): %s", url, e)
    else:
        logger.warning("PAGESPEED_API_KEY yok — hiz skoru atlandi")

    try:
        resp = await asyncio.to_thread(
            requests.get,
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (AgencyOS)"},
            allow_redirects=True,
        )
        html = resp.text[:150_000]
        if m := re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S):
            data["title"] = m.group(1).strip()[:200]
        if m := re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html, re.I):
            data["meta"] = m.group(1).strip()[:300]
        if m := re.search(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S):
            data["h1"] = re.sub(r"<[^>]+>", "", m.group(1)).strip()[:200]
        data["form_var"] = await _detect_form(url, html)
        data["tel_var"] = bool(re.search(r'href=["\']tel:', html, re.I))
    except Exception as e:
        logger.warning("Site fetch hatasi (%s): %s", url, e)

    logger.info(
        "Site verisi alindi: %s | hiz=%d form=%s tel=%s ssl=%s",
        url, data["hiz_skoru"], data["form_var"], data["tel_var"], data["ssl"],
    )
    return data


def _validate_audit(audit: dict, playbook: dict) -> tuple[bool, list[str]]:
    warnings: list[str] = []

    killer = audit.get("killer_insight") or {}
    rakam = (killer.get("rakam") or "").strip()
    bulgu = (killer.get("bulgu") or "").strip()
    if not rakam or not _DIGIT_RE.search(rakam):
        warnings.append("killer_insight.rakam bos/rakamsiz")
    if not bulgu or len(bulgu) < 15:
        warnings.append("killer_insight.bulgu cok kisa/bos")

    en_acitan = (audit.get("en_acitan_nokta") or "").strip()
    if not _DIGIT_RE.search(en_acitan):
        warnings.append("en_acitan_nokta rakam icermiyor")

    if not audit.get("ux_hatalar"):
        warnings.append("ux_hatalar bos")
    if not audit.get("seo_aciklar"):
        warnings.append("seo_aciklar bos")
    if not audit.get("kisisel_insight"):
        warnings.append("kisisel_insight bos")

    skorlar = audit.get("skorlar") or {}
    if not isinstance(skorlar, dict) or not any(skorlar.get(k, 0) > 0 for k in ("ux", "seo", "donusum")):
        warnings.append("skorlar eksik veya sifir")

    if audit.get("lead_kalitesi") not in ("soguk", "ilik", "sicak"):
        warnings.append("lead_kalitesi gecersiz deger")
    if audit.get("urgency") not in ("dusuk", "orta", "yuksek"):
        warnings.append("urgency gecersiz deger")

    yasak = [y.lower() for y in playbook.get("audit_dil_kurallari", {}).get("yasak", [])]
    if yasak:
        blob = " ".join([
            bulgu, killer.get("etki", "") or "", en_acitan,
            audit.get("kisisel_insight", "") or "",
            *(h.get("sorun", "") for h in (audit.get("ux_hatalar") or [])),
            *(s.get("sorun", "") for s in (audit.get("seo_aciklar") or [])),
        ]).lower()
        for y in yasak:
            if y and y in blob:
                warnings.append(f"yasak kelime kullanildi: '{y}'")

    return len(warnings) == 0, warnings


async def generate_audit(lead: dict, playbook: dict) -> dict:
    async with API_SEMAPHORE:
        site = await fetch_site_data(lead.get("website") or "")
        prompt = build_audit_prompt(lead, playbook, site)

        response = await claude_api_call(prompt, max_tokens=2800, temperature=0)
        result = safe_json_parse(response, fallback=dict(FALLBACK_AUDIT))

        for k, v in FALLBACK_AUDIT.items():
            result.setdefault(k, v)

        ok, warnings = _validate_audit(result, playbook)
        if not ok:
            logger.warning(
                "Audit validasyon uyarilari: %s | %s",
                lead.get("isim"), warnings,
            )
            result["_validation_warnings"] = warnings

        logger.info(
            "Audit tamamlandi: %s | skor=%s | uyari=%d",
            lead.get("isim"), result.get("genel_skor", 0), len(warnings),
        )
        result["_site_data"] = site  # passed through for service layer to persist
        return result
