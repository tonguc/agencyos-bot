"""Bounded observations of fetched HTML and mobile Lighthouse lab data.

These are page-level observations, not rankings, crawlability or revenue claims.
"""
import math
import re
from html.parser import HTMLParser


class PageSignals(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.canonical = False
        self.json_ld = False
        self.noindex = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            name = (attrs.get("name") or "").lower()
            content = attrs.get("content") or ""
            self.meta[name] = content
            if name in ("robots", "googlebot") and re.search(r"\b(noindex|none)\b", content, re.I):
                self.noindex = True
        if tag == "link" and "canonical" in (attrs.get("rel") or "").lower().split():
            self.canonical = bool(attrs.get("href")) or self.canonical
        if tag == "script" and (attrs.get("type") or "").lower() == "application/ld+json":
            self.json_ld = True


def html_evidence(html, headers):
    parser = PageSignals()
    parser.feed(html)
    header = headers.get("X-Robots-Tag", "")
    # Keep crawler-specific HTTP directives separate; do not infer a Google block.
    return {
        "meta_description": parser.meta.get("description", "")[:300],
        "meta_noindex": parser.noindex,
        "http_robots_present": bool(header),
        "canonical_present": parser.canonical,
        "viewport_present": bool(parser.meta.get("viewport")),
        "json_ld_present": parser.json_ld,
    }


def lab_evidence(payload):
    lighthouse = payload.get("lighthouseResult") or {}
    if lighthouse.get("runtimeError"):
        return {}
    result = {}
    score = ((lighthouse.get("categories") or {}).get("performance") or {}).get("score")
    if isinstance(score, (int, float)) and not isinstance(score, bool) and math.isfinite(score) and 0 <= score <= 1:
        result["performance"] = round(score * 100)
    audits = lighthouse.get("audits") or {}
    for key, metric in (("lcp_ms", "largest-contentful-paint"), ("cls", "cumulative-layout-shift"), ("tbt_ms", "total-blocking-time")):
        value = (audits.get(metric) or {}).get("numericValue")
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
            result[key] = round(value, 3)
    return result


def ground_audit(result, site):
    """Do not allow generated findings to outrun the actual measured evidence."""
    technical = site.get("technical") or {}
    if technical.get("version") != 1:
        return
    lab = technical.get("lab") or {}
    ux, seo, actions = [], [], []
    finding = "Bu ölçüm kapsamında öncelikli bir teknik sorun doğrulanmadı."
    metric = ""
    if technical.get("html_status") != "measured":
        finding = "Site HTML yanıtı bu denemede incelenemedi; erişim yeniden kontrol edilmeli."
        actions.append("Siteye erişimi yeniden kontrol edin.")
    lcp = lab.get("lcp_ms")
    if lcp is not None and lcp > 4000:
        finding = f"Mobil laboratuvar testinde ana içeriğin görünmesi (LCP) {lcp / 1000:.2f} saniye sürdü."
        metric = f"LCP: {lcp} ms"
        ux.append({"sorun": finding, "etki": "Yüklenme süresi ayrıca gerçek cihazda doğrulanmalı.", "siddet": "yuksek", "cozum": "Ana içerik ve kaynak yükleme sırasını inceleyip değişiklik sonrası yeniden ölçün."})
        actions.append("Yüklenme süresini gerçek cihazda doğrulayın ve yavaşlığın kaynağını inceleyin.")
    if technical.get("meta_noindex") is True:
        finding = "İncelenen HTML’de robots veya Googlebot için noindex yönergesi gözlendi."
        metric = ""
        seo.append({"sorun": finding, "etki": "Yönergenin bu sayfa için bilinçli olarak kullanılıp kullanılmadığı doğrulanmalı.", "cozum": "Sayfanın indekslenme amacıyla yönergeyi karşılaştırın."})
        actions.append("Noindex yönergesinin amacını işletmeyle doğrulayın.")
    if not actions:
        actions.append("Hedef hizmet ve bölge sorgularındaki gerçek görünürlüğü ayrı bir çalışmayla ölçün.")
    result.update(
        killer_insight={"bulgu": finding, "rakam": metric, "etki": "Bu teknik gözlemden müşteri kaybı veya arama sıralaması sonucu çıkarılamaz."},
        en_acitan_nokta=finding,
        kisisel_insight="İnceleme tek sayfanın ilk HTML yanıtı ve varsa mobil laboratuvar ölçümüyle sınırlı. Gerçek kullanıcı davranışı, rakip karşılaştırması ve arama görünürlüğü ölçülmedi.",
        ilk_izlenim={"ne_yapiyor": "Teknik ölçüm", "deger_onerisi": "belirsiz", "guven_seviyesi": "belirsiz", "ilk_surtunum": finding},
        ux_hatalar=ux, seo_aciklar=seo, donusum_engelleri=[], hizli_kazanimlar=actions,
        reklam_firsati={"kanal": "", "aciklama": "Reklam ve rakip verileri bu ölçümde incelenmedi.", "rakip_durum": "bilinmiyor"},
    )
