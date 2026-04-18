"""
Score Distribution Debug Dashboard

Scoring sisteminin skor enflasyonu, segment dağılımı ve
katman ağırlıklarını analiz eder. Mevcut scoring mantığına dokunmaz.
"""

from statistics import mean, median
from typing import List

BREAKDOWN_KEYS = ["maps", "audit", "conversion", "intent", "ads", "social", "fit", "boost"]

INFLATION_THRESHOLDS = {
    "hot_ratio_warn": 0.25,
    "hot_warm_ratio_warn": 0.55,
    "mean_warn": 70.0,
    "high_score_pct_warn": 0.30,
}


def summarize_score_distribution(results: List[dict]) -> dict:
    """results: calculate_final_score çıktılarının listesi."""
    total = len(results)
    if total == 0:
        return {"count": 0}

    ok_results = [r for r in results if r.get("status") == "ok"]
    rejected = len(results) - len(ok_results)

    final_scores = [r["final_score"] for r in ok_results]
    opportunities = [r["opportunity"] for r in ok_results]
    intents = [r["buyer_intent"] for r in ok_results]

    seg_counts: dict[str, int] = {"HOT": 0, "WARM": 0, "LOW": 0, "REJECTED": rejected}
    for r in ok_results:
        seg = r.get("segment", "LOW")
        seg_counts[seg] = seg_counts.get(seg, 0) + 1

    seg_ratio = {k: round(v / total, 3) for k, v in seg_counts.items()}
    breakdown_drivers = find_top_score_drivers(ok_results)

    return {
        "count": total,
        "ok_count": len(ok_results),
        "mean_final": round(mean(final_scores), 1) if final_scores else 0,
        "median_final": round(median(final_scores), 1) if final_scores else 0,
        "min_final": round(min(final_scores), 1) if final_scores else 0,
        "max_final": round(max(final_scores), 1) if final_scores else 0,
        "mean_opportunity": round(mean(opportunities), 1) if opportunities else 0,
        "mean_intent": round(mean(intents), 1) if intents else 0,
        "high_score_count": sum(1 for s in final_scores if s >= 90),
        "segment_counts": seg_counts,
        "segment_ratio": seg_ratio,
        "top_breakdown_drivers": breakdown_drivers,
    }


def detect_score_inflation(summary: dict) -> dict:
    """Skor enflasyonu var mı? Heuristic tabanlı."""
    if summary.get("count", 0) == 0:
        return {"inflation_risk": "unknown", "reasons": []}

    reasons: list[str] = []
    seg_ratio = summary.get("segment_ratio", {})

    hot_ratio = seg_ratio.get("HOT", 0)
    hot_warm_ratio = hot_ratio + seg_ratio.get("WARM", 0)
    mean_final = summary.get("mean_final", 0)
    high_score_pct = summary.get("high_score_count", 0) / max(summary.get("ok_count", 1), 1)

    if hot_ratio > INFLATION_THRESHOLDS["hot_ratio_warn"]:
        reasons.append(f"HOT orani %{round(hot_ratio * 100)} — esik: %{round(INFLATION_THRESHOLDS['hot_ratio_warn'] * 100)}")
    if hot_warm_ratio > INFLATION_THRESHOLDS["hot_warm_ratio_warn"]:
        reasons.append(f"HOT+WARM orani %{round(hot_warm_ratio * 100)} — esik: %{round(INFLATION_THRESHOLDS['hot_warm_ratio_warn'] * 100)}")
    if mean_final > INFLATION_THRESHOLDS["mean_warn"]:
        reasons.append(f"Ortalama skor {mean_final} — esik: {INFLATION_THRESHOLDS['mean_warn']}")
    if high_score_pct > INFLATION_THRESHOLDS["high_score_pct_warn"]:
        reasons.append(f"Skorlarin %{round(high_score_pct * 100)}'i 90 uzerinde")

    drivers = summary.get("top_breakdown_drivers", {})
    if drivers.get("conversion", 0) > 20:
        reasons.append(f"Conversion katmani cok yuksek ortalama: {drivers['conversion']}")
    if drivers.get("maps", 0) > 18:
        reasons.append(f"Maps katmani cok yuksek ortalama: {drivers['maps']}")

    if len(reasons) >= 3:
        risk = "high"
    elif len(reasons) >= 1:
        risk = "medium"
    else:
        risk = "low"

    return {"inflation_risk": risk, "reasons": reasons}


def find_top_score_drivers(results: List[dict]) -> dict:
    if not results:
        return {}

    breakdown_totals: dict[str, list[float]] = {k: [] for k in BREAKDOWN_KEYS}
    has_breakdown = False

    for r in results:
        bd = r.get("score_layers") or r.get("score_breakdown")
        if isinstance(bd, dict):
            has_breakdown = True
            for k in BREAKDOWN_KEYS:
                if k in bd:
                    breakdown_totals[k].append(bd[k])

    if has_breakdown:
        return {k: round(mean(v), 1) if v else 0.0 for k, v in breakdown_totals.items()}

    opps = [r.get("opportunity", 0) for r in results]
    intents = [r.get("buyer_intent", 0) for r in results]
    return {
        "opportunity_avg": round(mean(opps), 1) if opps else 0.0,
        "intent_avg": round(mean(intents), 1) if intents else 0.0,
    }


def suggest_rebalancing(summary: dict, inflation: dict) -> List[str]:
    """Deterministic öneriler. AI çağrısı yok."""
    suggestions: list[str] = []
    risk = inflation.get("inflation_risk", "low")
    reasons = inflation.get("reasons", [])
    drivers = summary.get("top_breakdown_drivers", {})
    seg_ratio = summary.get("segment_ratio", {})

    if risk == "low":
        suggestions.append("Scoring dengeli gorunuyor. Baska degisiklik gerekmez.")
        return suggestions

    if "Conversion katmani" in " ".join(reasons):
        suggestions.append("Conversion gap sinyallerini cap'le: tek lead icin max +20 uygula.")
    if "HOT orani" in " ".join(reasons):
        hot_pct = round(seg_ratio.get("HOT", 0) * 100)
        suggestions.append(f"HOT esigini 80 → {'85' if hot_pct > 40 else '82'} cek.")
    if "HOT+WARM orani" in " ".join(reasons):
        suggestions.append("WARM esigini 60 → 63 yukselt.")
    if "Ortalama skor" in " ".join(reasons):
        suggestions.append("Opportunity base score'u 40 → 35 dusurun.")
    if "90 uzerinde" in " ".join(reasons):
        suggestions.append("Soft cap uygula: 85 uzerini yavas artir (diminishing returns).")

    intent_avg = drivers.get("intent_avg", 0)
    if intent_avg > 75:
        suggestions.append(f"Buyer intent ortalamasi cok yuksek ({intent_avg}). Telefon/website bonuslarini azalt.")

    if not suggestions:
        suggestions.append("Enflasyon var ama katman analizi icin score_breakdown verisi gerekli.")

    return suggestions


def format_score_debug_report(summary: dict, inflation: dict, suggestions: List[str]) -> str:
    """Console / Telegram icin okunabilir rapor."""
    if summary.get("count", 0) == 0:
        return "Score Debug Report\nVeri yok."

    seg_counts = summary.get("segment_counts", {})
    seg_ratio = summary.get("segment_ratio", {})
    total = summary["count"]
    drivers = summary.get("top_breakdown_drivers", {})

    def seg_line(name: str) -> str:
        count = seg_counts.get(name, 0)
        pct = round(seg_ratio.get(name, 0) * 100)
        return f"  {name}: {count} (%{pct})"

    driver_lines = "\n".join(
        f"  {k}: {v}" for k, v in sorted(drivers.items(), key=lambda x: -x[1]) if v > 0
    ) or "  (score_breakdown verisi yok)"

    suggestion_lines = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(suggestions))
    reasons_text = "\n".join(f"  - {r}" for r in inflation.get("reasons", [])) or "  Yok"

    return (
        f"Score Distribution Report\n"
        f"{'=' * 40}\n"
        f"Toplam lead   : {total}\n"
        f"Ortalama skor : {summary['mean_final']}\n"
        f"Median skor   : {summary['median_final']}\n"
        f"Min / Max     : {summary['min_final']} / {summary['max_final']}\n"
        f"Ort. Opportunity : {summary.get('mean_opportunity', '-')}\n"
        f"Ort. Intent      : {summary.get('mean_intent', '-')}\n"
        f"\nSegment dagilimi:\n"
        f"{seg_line('HOT')}\n{seg_line('WARM')}\n"
        f"{seg_line('LOW')}\n{seg_line('REJECTED')}\n"
        f"\nEn guclu skor suruculeri:\n{driver_lines}\n"
        f"\nEnflasyon riski: {inflation['inflation_risk'].upper()}\n"
        f"Nedenler:\n{reasons_text}\n"
        f"\nOneriler:\n{suggestion_lines}"
    )
