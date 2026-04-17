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
    ux = (audit.get("ux_hatalar") or [{}])[0]
    seo = (audit.get("seo_aciklar") or [{}])[0]
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

    lines = [
        f"AUDIT — {lead.get('isim', '-')}",
        "━━━━━━━━━━━━━━━━━━━━",
        "KILLER INSIGHT:",
        f"• {killer_line}",
        "",
        f"HOOK ({hook.get('tip', '-')}):",
        f"• {hook.get('hook', '-')}",
        "",
        "UX:",
        f"• {ux.get('sorun', '-')}"
        + (f" → {ux.get('etki')}" if ux.get('etki') else "")
        + (f" | {ux.get('cozum')}" if ux.get('cozum') else ""),
        "SEO:",
        f"• {seo.get('sorun', '-')}"
        + (f" → {seo.get('etki')}" if seo.get('etki') else "")
        + (f" | {seo.get('cozum')}" if seo.get('cozum') else ""),
        "",
        f"En acitan nokta: {audit.get('en_acitan_nokta', '-')}",
        f"Genel skor: {audit.get('genel_skor', 0)}/100",
    ]
    if warnings:
        lines += ["", f"⚠ Uyari: {', '.join(warnings[:3])}"]
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
