"""Gece testi: restoran arama -> lead kaydet -> audit -> advanced skorlar doluyor mu?"""
import json
import sys
import time

import requests

BASE = "https://agencyos-bot-production.up.railway.app"
KEY = "test123"
HDRS = {"X-API-Key": KEY, "Content-Type": "application/json"}

def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")

def main():
    section("1. Health")
    r = requests.get(f"{BASE}/health", headers=HDRS, timeout=15)
    print(r.json())

    section("2. Restoran arama (Kadikoy)")
    r = requests.post(f"{BASE}/api/search", headers=HDRS,
                      json={"query": "restoran Kadikoy Istanbul", "limit": 3},
                      timeout=120)
    if r.status_code != 200:
        print("FAIL search:", r.status_code, r.text[:500])
        sys.exit(1)
    results = r.json().get("results", [])
    print(f"{len(results)} sonuç")
    for item in results[:3]:
        print(f"  {item['name']}: score={item['score']} seg={item['segment']} "
              f"ecom={item['ecommerce_urgency_score']} comp={item['competition_density_score']} "
              f"ppc={item['ppc_waste_score']} social={item['social_mismatch_score']}")

    # E-ticaret aciliyeti bug'ı fix edilmiş olmalı
    with_site = [i for i in results if i.get("website")]
    no_site = [i for i in results if not i.get("website") and i.get("category", "").lower().find("restoran") >= 0]
    if no_site:
        ecom = no_site[0].get("ecommerce_urgency_score") or 0
        assert ecom >= 60, f"ecommerce urgency should be >=60 for no-site restaurant, got {ecom}"
        print(f"OK: e-commerce urgency {ecom} (website'siz restoran)")

    # En sıcak adayı seç
    if not results:
        print("FAIL: sonuç yok")
        sys.exit(1)
    target = results[0]

    section(f"3. Lead kaydet: {target['name']}")
    # lead_id null ise kaydet
    created_id = target.get("lead_id")
    if not created_id:
        payload = {
            "name": target["name"],
            "sector": "restoran",
            "city": "İstanbul",
            "district": "Kadıköy",
            "address": target.get("address"),
            "phone": target.get("phone"),
            "website": target.get("website"),
            "google_rating": target.get("google_rating"),
            "review_count": target.get("review_count"),
        }
        r = requests.post(f"{BASE}/api/leads", headers=HDRS, json=payload, timeout=30)
        if r.status_code not in (200, 201):
            print("FAIL create:", r.status_code, r.text[:500])
            sys.exit(1)
        created = r.json()
        created_id = created.get("id")
        print(f"Kaydedildi: {created_id}")
    else:
        print(f"Zaten kayıtlı: {created_id}")

    section("4. Audit tetikle")
    r = requests.post(f"{BASE}/api/leads/{created_id}/audit", headers=HDRS, json={}, timeout=30)
    print("Status:", r.status_code, r.text[:400])
    if r.status_code not in (200, 201):
        print("Audit tetiklenemedi — job bekleyebiliriz")
    else:
        body = r.json()
        job_id = body.get("job_id") or (body.get("result") or {}).get("job_id")
        status = body.get("status")
        print(f"job_id={job_id} status={status}")

        if status != "completed" and job_id:
            section("5. Job durumunu bekle (max 180s)")
            for i in range(30):
                time.sleep(6)
                r = requests.get(f"{BASE}/api/jobs/{job_id}", headers=HDRS, timeout=15)
                j = r.json()
                st = j.get("status")
                print(f"  [{i}] {st} {j.get('progress_message') or ''}")
                if st in ("completed", "failed"):
                    break
            if st == "failed":
                print("FAIL job:", j.get("error_message"))
                sys.exit(1)

    section("6. Audit sonucu + advanced skorlar")
    r = requests.get(f"{BASE}/api/leads/{created_id}/audit", headers=HDRS, timeout=30)
    if r.status_code != 200:
        print("FAIL get audit:", r.status_code, r.text[:300])
        sys.exit(1)
    audit = r.json()
    result = audit.get("result") or {}
    adv = result.get("advanced_signals") or {}
    print("genel_skor:", result.get("genel_skor"))
    print("competition_density:", adv.get("competition_density", {}).get("competition_density_score"))
    print("ppc_waste:", adv.get("ppc_waste", {}).get("ppc_waste_score"))
    print("social_mismatch:", adv.get("social_mismatch", {}).get("social_mismatch_score"))
    print("ecommerce_urgency:", adv.get("ecommerce_urgency", {}).get("ecommerce_urgency_score"))
    print("market status:", (result.get("market_evidence") or {}).get("status"))

    # Beklentiler
    ecom = adv.get("ecommerce_urgency", {}).get("ecommerce_urgency_score") or 0
    print(f"\nSONUÇ: e-ticaret={ecom}")
    if ecom >= 60:
        print("OK: advanced signals audit'te çalışıyor")
    else:
        print("UYARI: e-ticaret aciliyeti düşük çıktı")

if __name__ == "__main__":
    main()
