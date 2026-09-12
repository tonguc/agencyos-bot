"""Query-scoped search observations; never a calibrated payment probability."""
import asyncio
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from config import settings

ENDPOINT = "https://serpapi.com/search"


def domain(url):
    if not isinstance(url, str):
        return None
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return None
        return (parsed.hostname or "").lower().removeprefix("www.") or None
    except ValueError:
        return None


def query_plan(lead):
    name = " ".join((lead.get("isim") or "").split())[:150]
    city = " ".join((lead.get("city") or "").split())[:80]
    district = " ".join((lead.get("district") or "").split())[:80]
    normalized = name.lower().replace("i̇", "i")
    services = (("veteriner", "veteriner"), ("diş", "diş hekimi"), ("dental", "diş hekimi"),
                ("psikolog", "psikolog"), ("diyetisyen", "diyetisyen"), ("anaokulu", "anaokulu"),
                ("dil", "dil kursu"), ("avukat", "avukat"), ("tesisat", "tesisatçı"))
    service = next((value for word, value in services if re.search(r"\b" + re.escape(word) + r"\b", normalized)), None)
    if not service:
        service = {"avukat": "avukat", "emlak": "emlak ofisi", "guzellik": "güzellik merkezi", "restoran": "restoran"}.get(lead.get("sektor"))
    queries = []
    if name:
        queries.append({"kind": "brand", "query": f"{name} {district} {city}".strip()})
    if service and (district or city):
        queries.append({"kind": "service", "query": f"{district} {city} {service}".strip()})
    return queries


def target_domain(website):
    host = domain(website)
    shared = ("facebook.com", "instagram.com", "google.com", "business.site", "wixsite.com", "linktr.ee")
    if host and any(host == item or host.endswith("." + item) for item in shared):
        return None
    return host


def parse_observation(payload, website, ai_payload=None):
    target = target_domain(website)
    rows = []
    for item in (payload.get("organic_results") or []):
        position = item.get("position")
        link = item.get("link")
        if isinstance(position, int) and not isinstance(position, bool) and 1 <= position <= 10 and domain(link):
            rows.append({"position": position, "url": link, "matched": bool(target and domain(link) == target)})
    matched = [row["position"] for row in rows if row["matched"]]
    organic_status = "unknown_domain" if not target else "measured" if rows else "unavailable"
    overview = ai_payload if ai_payload is not None else (payload.get("ai_overview") or {})
    references = [{"url": ref.get("link"), "matched": bool(target and domain(ref.get("link")) == target)}
                  for ref in overview.get("references", []) if domain(ref.get("link"))]
    if overview.get("error") or (overview.get("page_token") and not references):
        ai_status = "unavailable"
    elif not overview:
        ai_status = "not_returned"
    elif not target:
        ai_status = "unknown_domain"
    elif references:
        ai_status = "measured"
    else:
        ai_status = "no_references"
    ads = payload.get("ads") or []
    ad_match = any(domain(item.get("link")) == target for item in ads) if target else None
    return {"organic_status": organic_status, "position": min(matched) if matched else None,
            "organic_results": sorted(rows, key=lambda row: row["position"]),
            "ai_status": ai_status, "ai_cited": any(ref["matched"] for ref in references) if ai_status == "measured" else None,
            "ai_references": references[:30], "self_ad_observed": ad_match,
            "ad_count": len(ads), "provider_search_id": (payload.get("search_metadata") or {}).get("id"),
            "provider_created_at": (payload.get("search_metadata") or {}).get("created_at"),
            "query_used": (payload.get("search_information") or {}).get("query_displayed"),
            "location_used": (payload.get("search_parameters") or {}).get("location_used")}


async def collect_market(lead):
    plan = query_plan(lead)
    result = {"version": 1, "checked_at": datetime.now(timezone.utc).isoformat(),
              "provider": "SerpAPI / Google", "device": "mobile", "country": "tr", "language": "tr",
              "domain": target_domain(lead.get("website")), "queries": [], "status": "not_configured"}
    if not settings.SERPAPI_API_KEY:
        return result
    result["status"] = "complete"
    try:
        async with asyncio.timeout(55), httpx.AsyncClient(timeout=15) as client:
            for item in plan:
                record = {**item, "status": "unavailable"}
                result["queries"].append(record)
                params = {"engine": "google", "q": item["query"], "hl": "tr", "gl": "tr", "device": "mobile", "api_key": settings.SERPAPI_API_KEY}
                city = lead.get("city")
                if city:
                    params["location"] = f"{city}, Turkey"
                try:
                    response = await client.get(ENDPOINT, params=params)
                    response.raise_for_status()
                    payload = response.json()
                    if payload.get("error") or (payload.get("search_metadata") or {}).get("status") != "Success":
                        continue
                    overview = payload.get("ai_overview") or {}
                    token = overview.get("page_token")
                    if token and not overview.get("references"):
                        try:
                            more = await client.get(ENDPOINT, params={"engine": "google_ai_overview", "page_token": token, "api_key": settings.SERPAPI_API_KEY}, timeout=10)
                            more.raise_for_status()
                            more_data = more.json()
                            overview = more_data.get("ai_overview") or {"error": True}
                        except (httpx.HTTPError, ValueError):
                            overview = {"error": True}
                    record.update(parse_observation(payload, lead.get("website"), overview), status="measured")
                except (httpx.HTTPError, ValueError, TypeError, AttributeError):
                    # Never persist/log provider errors containing credential-bearing URLs.
                    pass
    except TimeoutError:
        result["status"] = "partial"
    if not plan:
        result["status"] = "no_query"
    elif any(row["status"] != "measured" for row in result["queries"]):
        result["status"] = "partial"
    return result


def commercial_evidence(lead, market, audit):
    """Transparent prospecting signals, not solvency or credit assessment."""
    self_ad = any(row.get("self_ad_observed") is True for row in market.get("queries", []))
    technical = (audit.get("_site_data") or {}).get("technical") or {}
    lab = technical.get("lab") or {}
    need = technical.get("meta_noindex") is True or (lab.get("lcp_ms") is not None and lab["lcp_ms"] > 4000)
    signals = []
    if self_ad:
        signals.append("Kayıtlı alan adı arama reklamında gözlendi; mevcut dijital yatırım sinyali.")
    reviews = lead.get("review_count")
    if isinstance(reviews, int) and reviews > 0:
        signals.append(f"İşletme kaydında {reviews} yorum var; geçmiş etkileşim göstergesi, gelir veya güncel faaliyet kanıtı değil.")
    if need:
        signals.append("Ölçümle desteklenen teknik inceleme ihtiyacı var.")
    return {"payment_probability": None, "priority": "investment_and_need" if self_ad and need else "need_to_qualify" if need else "insufficient",
            "signals": signals, "budget": "unknown", "buying_intent": "unknown",
            "next_questions": ["Bu çalışma için ayırdığınız bir bütçe var mı?", "Kararı kim veriyor ve ne zaman başlamak istiyorsunuz?", "Şu an dijital kanallardan gelen talepleri nasıl takip ediyorsunuz?"]}
