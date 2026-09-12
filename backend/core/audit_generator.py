import os
import re
import asyncio
import logging
from urllib.parse import urljoin
from datetime import datetime, timezone

import requests

from core.utils import safe_json_parse, API_SEMAPHORE, claude_api_call
from core.prompts import build_audit_prompt
from core.technical_evidence import html_evidence, lab_evidence, ground_audit

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


async def _detect_form(base_url: str, html: str) -> bool | None:
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
                resp.raise_for_status()
                if _FORM_PATTERNS.search(resp.text[:80_000]):
                    logger.info("Form iletisim sayfasinda bulundu: %s", contact_url)
                    return True
            except Exception as e:
                logger.debug("Contact page fetch hatasi (%s): %s", contact_url, e)
                return None
    return False


async def fetch_site_data(url: str) -> dict:
    if not url:
        logger.info("Site verisi atlandi: url yok")
        return {"url": "", "hata": True, "neden": "url yok"}

    data: dict = {
        "url": url,
        "hiz_skoru": None,
        "hiz_veri_var": False,  # True yalnızca PageSpeed gerçek skor döndürdüğünde
        "title": "",
        "meta": "",
        "h1": "",
        "form_var": None,
        "tel_var": None,
        "ssl": None,
        "hata": False,
        "technical": {
            "version": 1,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "html_status": "unavailable",
            "speed_status": "not_configured",
            "lab": {},
        },
    }

    key = os.getenv("PAGESPEED_API_KEY")
    if key:
        data["technical"]["speed_status"] = "unavailable"
        try:
            ps = await asyncio.to_thread(
                requests.get,
                PAGESPEED_URL,
                params={"url": url, "key": key, "strategy": "mobile"},
                timeout=60,
            )
            ps.raise_for_status()
            payload = ps.json()
            lab = lab_evidence(payload)
            data["technical"]["lab"] = lab
            score = lab.get("performance")
            if score is not None:
                data["hiz_skoru"] = score
                data["hiz_veri_var"] = True
                data["technical"]["speed_status"] = "measured"
        except Exception as e:
            logger.warning("PageSpeed ölçülemedi: %s", type(e).__name__)
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
        data["technical"]["http_status"] = resp.status_code
        resp.raise_for_status()
        if "html" not in resp.headers.get("Content-Type", "").lower():
            raise ValueError("HTML olmayan yanıt")
        html = resp.text[:150_000]
        data["technical"].update(html_evidence(html, resp.headers))
        data["technical"].update(
            html_status="measured", final_url=resp.url,
            html_truncated=len(resp.text) > 150_000,
        )
        # Use final URL after redirects for SSL check (http:// sites often redirect to https://)
        data["ssl"] = resp.url.startswith("https://")
        if m := re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S):
            data["title"] = m.group(1).strip()[:200]
        if m := re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html, re.I):
            data["meta"] = m.group(1).strip()[:300]
        if m := re.search(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S):
            data["h1"] = re.sub(r"<[^>]+>", "", m.group(1)).strip()[:200]
        data["meta"] = data["technical"]["meta_description"]
        data["form_var"] = await _detect_form(resp.url, html)
        data["tel_var"] = bool(re.search(r'href=["\']tel:', html, re.I))
    except Exception as e:
        data["hata"] = True
        logger.warning("Site fetch hatasi (%s): %s", url, e)

    logger.info(
        "Site verisi alindi: %s | hiz=%s form=%s tel=%s ssl=%s",
        url, data["hiz_skoru"], data["form_var"], data["tel_var"], data["ssl"],
    )
    return data


def _validate_audit(audit: dict, playbook: dict) -> tuple[bool, list[str]]:
    warnings: list[str] = []

    killer = audit.get("killer_insight") or {}
    rakam = (killer.get("rakam") or "").strip()
    bulgu = (killer.get("bulgu") or "").strip()
    if not bulgu or len(bulgu) < 15:
        warnings.append("killer_insight.bulgu cok kisa/bos")

    en_acitan = (audit.get("en_acitan_nokta") or "").strip()
    if not audit.get("kisisel_insight"):
        warnings.append("kisisel_insight bos")

    skorlar = audit.get("skorlar") or {}
    if not isinstance(skorlar, dict) or not any((skorlar.get(k) or 0) > 0 for k in ("ux", "seo", "donusum")):
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
        result = safe_json_parse(response)
        scores = result.get("skorlar") if isinstance(result, dict) else None
        if not isinstance(scores, dict) or not all(
            isinstance(scores.get(k), (int, float)) and not isinstance(scores.get(k), bool)
            and 0 <= scores[k] <= 100 for k in ("ux", "seo", "donusum")
        ) or not isinstance(result.get("genel_skor"), (int, float)) or isinstance(
            result.get("genel_skor"), bool
        ) or not 0 <= result["genel_skor"] <= 100:
            raise RuntimeError("Audit üretilemedi: AI yanıtı boş veya geçersiz. API yapılandırmasını kontrol edin.")

        for k, v in FALLBACK_AUDIT.items():
            result.setdefault(k, v)

        ground_audit(result, site)

        if not lead.get("website"):
            # No URL is a single evidence limitation, not multiple site defects.
            finding = "Eldeki işletme kaydında web sitesi bağlantısı bulunamadı."
            result.update(
                killer_insight={"bulgu": finding, "etki": "İşletmenin ayrı bir sitesi olup olmadığı doğrulanmalı; Google profilindeki telefon ve diğer iletişim yolları ayrıca incelenmeli.", "rakam": ""},
                en_acitan_nokta=finding,
                kisisel_insight="Site bağlantısı doğrulanmadan site kalitesi veya müşteri kaybı hakkında sonuç çıkarılamaz.",
                ilk_izlenim={"ne_yapiyor": "Site incelenemedi", "deger_onerisi": "belirsiz", "guven_seviyesi": "dusuk", "ilk_surtunum": finding},
                ux_hatalar=[], seo_aciklar=[], donusum_engelleri=[],
                hizli_kazanimlar=["İşletmenin resmi web sitesi olup olmadığını doğrulayın.", "Site varsa Google işletme kaydındaki bağlantıyı kontrol edin."],
                reklam_firsati={"kanal": "", "aciklama": "Reklam değerlendirmesi için yeterli veri yok.", "rakip_durum": "bilinmiyor"},
            )
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
