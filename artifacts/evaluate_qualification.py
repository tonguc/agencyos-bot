"""Offline counterexamples using unchanged production scoring/filter functions.

Run from repository root. No network, database, credentials or application changes.
Synthetic examples test behavior, not actual willingness to purchase.
"""
import importlib.util
import json
import logging
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
logging.disable(logging.CRITICAL)
# Isolate the filter's only setting so no .env or production services are loaded.
config = ModuleType("config")
config.settings = SimpleNamespace(ICP_STRICT_MODE=False)
sys.modules["config"] = config

def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

scorer = module("qualification_scorer", "backend/core/lead_scorer.py")
icp = module("qualification_filter", "backend/core/icp_filter.py")
pb = json.loads((ROOT / "backend/playbooks/clinic_general.json").read_text(encoding="utf-8"))
base = dict(isim="Ornek Bagimsiz Klinik", telefon="+905550000000",
            website="https://example.invalid", yorum_sayisi=318, puan=4.8,
            site_durumu="zayif", sektor="klinik")
active_gap = dict(in_organic_top10=False, indexed_pages=5, son_yorum_gun=5,
                  review_last_30d=8, review_last_90d=24)
cases = [
    ("unknown_activity_small_no_site", dict(website=None, site_durumu="yok", yorum_sayisi=2, puan=3.2), {}),
    ("known_inactive_small_no_site", dict(website=None, site_durumu="yok", yorum_sayisi=2, puan=3.2, son_yorum_gun=400, instagram_post_90d=0), {}),
    ("established_basic_data", {}, {}),
    ("same_established_verified_gaps", active_gap, dict(genel_skor=30, pagespeed=30, ssl=True)),
    ("active_600_reviews_verified_gaps", dict(active_gap, yorum_sayisi=600), dict(genel_skor=30, pagespeed=30, ssl=True)),
    ("good_site_with_seo_gap", dict(active_gap, site_durumu="iyi"), dict(genel_skor=50, pagespeed=80, ssl=True)),
    ("same_business_website_missing", dict(website=None, site_durumu="yok"), {}),
    ("audit_pagespeed_unknown", {}, dict(genel_skor=55, ssl=True)),
    ("audit_pagespeed_missing_as_zero", {}, dict(genel_skor=55, ssl=True, pagespeed=0)),
    ("poor_conversion_only", {}, dict(genel_skor=55, skorlar=dict(donusum=10))),
    ("good_conversion_only", {}, dict(genel_skor=55, skorlar=dict(donusum=90))),
    ("permanently_closed", dict(permanently_closed=True), {}),
]
results = []
for name, delta, audit in cases:
    lead = dict(base, **delta)
    filtered = icp.filter_leads([lead], pb)
    score = scorer.calculate_final_score(lead, audit, pb)
    row = dict(case=name, lead=lead, audit=audit,
               icp_accepted=bool(filtered["nitelikli"]),
               icp_reasons=[x["neden"] for x in filtered["elendi"]], score=score)
    results.append(row)
    print(name, "ICP=" + str(row["icp_accepted"]),
          "score=" + str(score.get("final_score")), score.get("segment", score["status"]),
          "intent=" + str(score.get("intent_score")), "confidence=" + str(score.get("confidence")))

by_name = {x["case"]: x for x in results}
assert by_name["unknown_activity_small_no_site"]["score"]["segment"] == "HOT"
assert by_name["known_inactive_small_no_site"]["score"]["segment"] == "REVIEW"
assert not by_name["active_600_reviews_verified_gaps"]["icp_accepted"]
assert not by_name["good_site_with_seo_gap"]["icp_accepted"]
assert by_name["poor_conversion_only"]["score"]["final_score"] == by_name["good_conversion_only"]["score"]["final_score"]
assert by_name["permanently_closed"]["score"]["status"] == "rejected"
out = ROOT / "artifacts/qualification-evaluation-2026-09-12.json"
out.write_text(json.dumps(dict(mode="offline synthetic; ICP_STRICT_MODE=false", results=results), ensure_ascii=False, indent=2), encoding="utf-8")
print("6 behavioral assertions passed; 12 scenarios evaluated.")
