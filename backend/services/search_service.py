"""
Search Service — natural-language search for leads.

Pipeline:
  query → parse_search_query → collect_by_query (Apify) → enrich
       → if sector matched → playbook + icp_filter + scoring (skipped on miss)
       → normalize results for the UI
       → group into HOT / WARM / OK / LOW segments

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


def _segment(score: int | None) -> str:
    if score is None:
        return "low"
    if score >= 70:
        return "hot"
    if score >= 50:
        return "warm"
    if score >= 30:
        return "ok"
    return "low"


def _normalize_lead(lead: dict, score_info: dict | None) -> dict:
    score = int(score_info["final_score"]) if score_info and score_info.get("status") == "ok" else None
    return {
        "name":          lead.get("isim") or "",
        "address":       lead.get("adres") or "",
        "phone":         lead.get("telefon"),
        "website":       lead.get("website"),
        "google_rating": lead.get("puan") or None,
        "review_count":  lead.get("yorum_sayisi") or 0,
        "category":      lead.get("kategori"),
        "lat":           lead.get("enlem"),
        "lng":           lead.get("boylam"),
        "maps_url":      lead.get("maps_url"),
        "site_status":   lead.get("site_durumu"),
        "score":         score,
        "segment":       _segment(score),
        "priority":      score_info.get("priority") if score_info else None,
        "reason":        score_info.get("reason") if score_info else "sektör eşleşmedi",
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
            "summary": {"hot": 0, "warm": 0, "ok": 0, "low": 0, "total": 0},
            "filter_stats": None,
            "error": "Boş sorgu",
        }

    raw = await collect_by_query(
        search_string=parsed["search_string"],
        sehir=parsed["city"],
        ilce=parsed["district"],
        limit=limit,
        sektor_filter=parsed["sector"],
    )

    if not raw:
        return {
            "parsed": parsed,
            "results": [],
            "summary": {"hot": 0, "warm": 0, "ok": 0, "low": 0, "total": 0},
            "filter_stats": None,
            "error": "Sonuç bulunamadı",
        }

    # If the query parser identified a sector, apply ICP + scoring.
    # Otherwise return raw enriched leads (no score) so the user still sees something.
    results: list[dict] = []
    filter_stats: dict | None = None

    if parsed["sector"]:
        try:
            playbook = load_playbook_for_sector(parsed["sector"])
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
        "hot":   sum(1 for r in results if r["segment"] == "hot"),
        "warm":  sum(1 for r in results if r["segment"] == "warm"),
        "ok":    sum(1 for r in results if r["segment"] == "ok"),
        "low":   sum(1 for r in results if r["segment"] == "low"),
        "total": len(results),
    }

    logger.info(
        "Search: q=%r sector=%s results=%d hot=%d warm=%d",
        query, parsed["sector"], summary["total"], summary["hot"], summary["warm"],
    )

    return {
        "parsed":       parsed,
        "results":      results,
        "summary":      summary,
        "filter_stats": filter_stats,
        "error":        None,
    }
