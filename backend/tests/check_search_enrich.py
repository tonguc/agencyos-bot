"""Search zenginlestirme alanlarini kontrol et."""
import requests

r = requests.post(
    "https://agencyos-bot-production.up.railway.app/api/search",
    headers={"Content-Type": "application/json", "X-API-Key": "test123"},
    json={"query": "restoran Kadikoy Istanbul", "limit": 5},
    timeout=150,
)
d = r.json()
for x in d["results"]:
    sd = x.get("source_data") or {}
    print(
        f"{x['name']}: site={'var' if x['website'] else 'yok'} "
        f"status={x['site_status']} comp={x['competition_density_score']} "
        f"ppc={x['ppc_waste_score']} social={x['social_mismatch_score']} "
        f"ecom={x['ecommerce_urgency_score']} "
        f"has_cta={sd.get('has_cta')} booking={sd.get('has_online_booking')} "
        f"ig={sd.get('has_instagram')} strong_comp={sd.get('strong_competitor_count')}"
    )
