"""
Search Service — natural-language search for leads.

Pipeline:
  query → parse_search_query → collect_by_query (Apify) → enrich
       → if sector matched → playbook + icp_filter + scoring (skipped on miss)
       → normalize results for the UI
       → group into HOT / WARM / REVIEW / OK / LOW segments
         (REVIEW: scorer tarafindan dusuk confidence / celisik sinyal ile isaretlenen)

Note: Search results are NOT persisted to DB. The user can later trigger a
real scrape from the same query to save them.
"""

from __future__ import annotations

import logging

from core.icp_filter import filter_leads
from core.lead_collector import collect_by_query
from core.lead_scorer import calculate_final_score
from core.playbook import load_playbook_for_sector
from core.query_parser import parse_search_query

logger = logging.getLogger(__name__)


# CRM segment (lead_scorer) → search UI segment (lowercase).
# REVIEW = düşük confidence / çelişkili sinyal / zombie risk.
_CRM_TO_SEARCH_SEGMENT = {
    "HOT":    "hot",
    "WARM":   "warm",
    "LOW":    "low",
    "REVIEW": "review",
}


def _segment_from_score(score: int | None) -> str:
    """Unscored veya rejected leadler icin threshold tabanli fallback.

    score=None → "review": sektor eslesmedi veya scoring atlandi →
    "Elendi" degil, "On Skor" (henuz degerlendirilmedi). Thresholds
    scorer'in route_decision'i ile hizali: HOT>=80, WARM>=60.
    """
    if score is None:
        return "review"
    if score >= 80:
        return "hot"
    if score >= 60:
        return "warm"
    if score >= 40:
        return "ok"
    return "low"


def _normalize_lead(lead: dict, score_info: dict | None) -> dict:
    score = int(score_info["final_score"]) if score_info and score_info.get("status") == "ok" else None

    # Segment kararı üç kaynaktan gelir, şu öncelikle:
    #   1. Scorer'in verdiği karar (HOT/WARM/LOW/REVIEW)
    #   2. Hard-filter reddi (status=rejected) → "low" (gercek Elendi)
    #   3. Hic scorelanmamis (score_info=None, ornek: sektor eslesmedi) → "review"
    crm_seg = score_info.get("segment") if score_info and score_info.get("status") == "ok" else None
    segment = _CRM_TO_SEARCH_SEGMENT.get(crm_seg) if crm_seg else None
    if segment is None:
        if score_info and score_info.get("status") == "rejected":
            segment = "low"   # gercek hard-filter reddi
        else:
            segment = _segment_from_score(score)  # unscored → "review"

    reason = (
        score_info.get("reason_summary") or score_info.get("reason")
        if score_info else "sektör eşleşmedi"
    )

    # Score breakdown: en etkili sinyaller (UI'da madde madde gösterilir)
    if score_info and score_info.get("status") == "ok":
        breakdown: list[str] = score_info.get("score_breakdown") or []
    elif score_info and score_info.get("status") == "rejected":
        breakdown = [f"Elendi: {score_info.get('reason', '?')}"]
    else:
        breakdown = []

    return {
        "name":           lead.get("isim") or "",
        "address":        lead.get("adres") or "",
        "phone":          lead.get("telefon"),
        "website":        lead.get("website"),
        "google_rating":  lead.get("puan") or None,
        "review_count":   lead.get("yorum_sayisi") or 0,
        "category":       lead.get("kategori"),
        "lat":            lead.get("enlem"),
        "lng":            lead.get("boylam"),
        "maps_url":       lead.get("maps_url"),
        "site_status":    lead.get("site_durumu"),
        "score":          score,
        "segment":        segment,
        "priority":       score_info.get("priority") if score_info else None,
        "reason":         reason,
        "score_breakdown": breakdown,
    }


async def run_search(query: str, limit: int = 25) -> dict:
    """
    Returns:
    {
      "parsed":       <query parser output>,
      "results":      [<normalized lead>, ...],
      "summary":      {"hot": n, "warm": n, "ok": n, "low": n, "total": n},
      "filter_stats": {"toplam": ..., "elenen": ..., "gecen": ...} | None,
      "error":        str | None,
    }
    """
    parsed = parse_search_query(query)

    if not parsed["search_string"]:
        return {
            "parsed": parsed,
            "results": [],
            "summary": {"hot": 0, "warm": 0, "ok": 0, "low": 0, "review": 0, "total": 0},
            "filter_stats": None,
            "error": "Boş sorgu",
        }

    try:
        raw = await collect_by_query(
            search_string=parsed["search_string"],
            sehir=parsed["city"],
            ilce=parsed["district"],
            limit=limit,
            sektor_filter=parsed["sector"],
            apify_timeout=150,
            max_reviews=3,
            search_only=True,   # Firma Ara: always SerpAPI, never Apify
        )
    except TimeoutError:
        return {
            "parsed": parsed, "results": [],
            "summary": {"hot": 0, "warm": 0, "ok": 0, "low": 0, "review": 0, "total": 0},
            "filter_stats": None,
            "error": "Arama zaman aşımına uğradı (150s). Daha az limit dene veya Yeni Tarama kullan.",
        }
    except RuntimeError as e:
        return {
            "parsed": parsed, "results": [],
            "summary": {"hot": 0, "warm": 0, "ok": 0, "low": 0, "review": 0, "total": 0},
            "filter_stats": None,
            "error": str(e),
        }

    if not raw:
        return {
            "parsed": parsed,
            "results": [],
            "summary": {"hot": 0, "warm": 0, "ok": 0, "low": 0, "review": 0, "total": 0},
            "filter_stats": None,
            "error": "Sonuç bulunamadı — farklı arama terimi veya ilçe dene.",
        }

    # If the query parser identified a sector, apply ICP + scoring.
    # Otherwise return raw enriched leads (no score) so the user still sees something.
    results: list[dict] = []
    filter_stats: dict | None = None

    if parsed["sector"]:
        try:
            playbook = load_playbook_for_sector(parsed["sector"])

            # Site analysis and SERP are skipped for quick search —
            # they add 30-90s per run. Full analysis happens during collect_leads job.
            filtered = filter_leads(raw, playbook)
            filter_stats = filtered["istatistik"]
            for lead in filtered["nitelikli"]:
                score_info = calculate_final_score(lead, {}, playbook)
                results.append(_normalize_lead(lead, score_info))
            # also include filtered-out leads as "low" so user sees the full picture
            for elem in filtered["elendi"]:
                results.append(_normalize_lead(elem["lead"], {
                    "status": "rejected", "final_score": 0, "priority": "low",
                    "reason": elem["neden"],
                }))
        except Exception as e:  # pragma: no cover — playbook missing etc.
            logger.exception("Playbook scoring failed for sector=%s: %s", parsed["sector"], e)
            results = [_normalize_lead(l, None) for l in raw]
    else:
        results = [_normalize_lead(l, None) for l in raw]

    # Sort: highest score first, unscored last.
    results.sort(key=lambda r: (r["score"] is None, -(r["score"] or 0)))

    summary = {
        "hot":    sum(1 for r in results if r["segment"] == "hot"),
        "warm":   sum(1 for r in results if r["segment"] == "warm"),
        "ok":     sum(1 for r in results if r["segment"] == "ok"),
        "low":    sum(1 for r in results if r["segment"] == "low"),
        "review": sum(1 for r in results if r["segment"] == "review"),
        "total":  len(results),
    }

    logger.info(
        "Search: q=%r sector=%s results=%d hot=%d warm=%d review=%d",
        query, parsed["sector"], summary["total"], summary["hot"], summary["warm"], summary["review"],
    )

    return {
        "parsed":       parsed,
        "results":      results,
        "summary":      summary,
        "filter_stats": filter_stats,
        "error":        None,
    }
