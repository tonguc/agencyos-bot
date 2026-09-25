"""force_refresh ile taze arama kontrolü."""
import requests

r = requests.post(
    "https://agencyos-bot-production.up.railway.app/api/search",
    headers={"Content-Type": "application/json", "X-API-Key": "test123"},
    json={"query": "restoran Kadikoy Istanbul", "limit": 5, "force_refresh": True},
    timeout=200,
)
d = r.json()
print("cache_hit:", d.get("cache_hit"), "| error:", d.get("error"))
for x in d["results"]:
    print(
        f"{x['name']}: comp={x['competition_density_score']} "
        f"ppc={x['ppc_waste_score']} social={x['social_mismatch_score']} "
        f"ecom={x['ecommerce_urgency_score']} score={x['score']} seg={x['segment']}"
    )
