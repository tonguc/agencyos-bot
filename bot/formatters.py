from core.icp_filter import get_filter_summary


def format_lead_collect_summary(stats: dict, skor_dagilim: dict, elendi_ornek: str = "") -> str:
    toplam = stats.get("gecen", 0)
    lines = [
        f"Tamamlandi! {toplam} lead bulundu ve kaydedildi.",
        f"Yuksek oncelik (70+): {skor_dagilim.get('yuksek', 0)}",
        f"Orta oncelik (40-69): {skor_dagilim.get('orta', 0)}",
        f"Dusuk oncelik (<40): {skor_dagilim.get('dusuk', 0)}",
        f"Elendi: {stats.get('elenen', 0)}" + (f" ({elendi_ornek})" if elendi_ornek else ""),
        "",
        "Sonraki adim: /audit toplu",
    ]
    return "\n".join(lines)


def format_icp_summary(result: dict) -> str:
    return get_filter_summary(result)


def format_audit(lead: dict, audit: dict, hook: dict) -> str:
    killer = audit.get("killer_insight") or {}
    ilk = audit.get("ilk_izlenim") or {}
    skorlar = audit.get("skorlar") or {}
    ux_list = audit.get("ux_hatalar") or [{}]
    seo_list = audit.get("seo_aciklar") or [{}]
    donusum = audit.get("donusum_engelleri") or []
    kazanimlar = audit.get("hizli_kazanimlar") or []
    page_id = lead.get("page_id") or ""
    warnings = audit.get("_validation_warnings") or []

    bulgu = killer.get("bulgu") or "-"
    etki = killer.get("etki") or ""
    rakam = killer.get("rakam") or ""
    killer_line = bulgu
    if etki:
        killer_line += f" → {etki}"
    if rakam:
        killer_line += f"  [{rakam}]"

    urgency_emoji = {"yuksek": "🔴", "orta": "🟡", "dusuk": "🟢"}.get(audit.get("urgency", ""), "⚪")
    kalite_emoji = {"sicak": "🔥", "ilik": "☀", "soguk": "❄"}.get(audit.get("lead_kalitesi", ""), "")

    lines = [
        f"AUDIT — {lead.get('isim', '-')}",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    if ilk.get("ne_yapiyor"):
        guven = ilk.get("guven_seviyesi", "-")
        deger = ilk.get("deger_onerisi", "-")
        lines += [
            f"ILK IZLENIM: {ilk['ne_yapiyor']}",
            f"Deger onerisi: {deger}  |  Guven: {guven}",
        ]
        if ilk.get("ilk_surtunum"):
            lines.append(f"Ilk surtunum: {ilk['ilk_surtunum']}")
        lines.append("")

    lines += [
        "KILLER INSIGHT:",
        f"• {killer_line}",
        "",
        f"HOOK ({hook.get('tip', '-')}):",
        f"• {hook.get('hook', '-')}",
        "",
        "UX SORUNLARI:",
    ]
    for ux in ux_list[:3]:
        siddet = f"[{ux.get('siddet', '')}] " if ux.get("siddet") else ""
        line = f"• {siddet}{ux.get('sorun', '-')}"
        if ux.get("etki"):
            line += f" → {ux['etki']}"
        if ux.get("cozum"):
            line += f"\n  Fix: {ux['cozum']}"
        lines.append(line)

    lines += ["", "SEO ACIKLARI:"]
    for seo in seo_list[:2]:
        line = f"• {seo.get('sorun', '-')}"
        if seo.get("etki"):
            line += f" → {seo['etki']}"
        if seo.get("cozum"):
            line += f"\n  Fix: {seo['cozum']}"
        lines.append(line)

    if donusum:
        lines += ["", "DONUSUM ENGELI:"]
        for d in donusum[:2]:
            lines.append(f"• {d.get('engel', '-')} → {d.get('kayip', '')}")

    if kazanimlar:
        lines += ["", "HIZLI KAZANIMLAR (max 1 hafta):"]
        for k in kazanimlar[:3]:
            lines.append(f"• {k}")

    lines += [
        "",
        f"Skor → UX:{skorlar.get('ux', 0)}  SEO:{skorlar.get('seo', 0)}  Donusum:{skorlar.get('donusum', 0)}  Genel:{audit.get('genel_skor', 0)}/100",
        f"{urgency_emoji} Urgency: {audit.get('urgency', '-')}  {kalite_emoji} Lead: {audit.get('lead_kalitesi', '-')}",
        "",
        f"En acitan: {audit.get('en_acitan_nokta', '-')}",
    ]
    if audit.get("kisisel_insight"):
        lines += ["", f"Kisisel gozlem: {audit['kisisel_insight']}"]
    if warnings:
        lines += ["", f"⚠ {', '.join(warnings[:3])}"]
    lines += ["", f"Sonraki adim: /mesaj {page_id}".rstrip()]
    return "\n".join(lines)


def format_outreach(lead: dict, hook_tipi: str, msgs: dict) -> str:
    page_id = lead.get("page_id", "")
    onerilen = msgs.get("onerilen", "v4")
    return "\n".join([
        f"Mesajlar: {lead.get('isim')} ({hook_tipi})",
        "",
        f"V1 (Merakli):\n{msgs.get('v1', '')}",
        "---",
        f"V2 (Dogrudan):\n{msgs.get('v2', '')}",
        "---",
        f"V3 (Nazik):\n{msgs.get('v3', '')}",
        "---",
        f"V4 (Proof-based + Behance):\n{msgs.get('v4', '')}",
        "",
        f"Onerilen: {onerilen} | Gondermek icin: /gonder {page_id} {onerilen}",
    ])


def format_pipeline(counts: dict) -> str:
    return "\n".join([
        "Pipeline Durumu:",
        f"Yeni: {counts.get('Yeni', 0)} | Audit: {counts.get('Audit', 0)} | Mesaj: {counts.get('Mesaj', 0)}",
        f"Cevap: {counts.get('Cevap', 0)} | Demo: {counts.get('Demo', 0)} | Teklif: {counts.get('Teklif', 0)}",
        f"Kapandi: {counts.get('Kapandi', 0)} | Soguk: {counts.get('Soguk', 0)}",
        "",
        "Sonraki adim: /audit toplu",
    ])


def format_yardim() -> str:
    return "\n".join([
        "Phase 1A Komutlari:",
        "/lead <sektor> <sehir> [ilce] [limit=20] — Google Maps'ten lead topla",
        "/audit <lead_id | toplu>              — Lead icin audit + hook uret",
        "/mesaj <lead_id>                      — 3 versiyon outreach mesaji uret",
        "/gonder <lead_id> <v1|v2|v3>          — Secilen versiyonu gonderildi olarak kaydet",
        "/followup <lead_id>                   — Takip mesaji uret",
        "/durum                                — Pipeline ozeti",
        "/yardim                               — Bu menu",
    ])
