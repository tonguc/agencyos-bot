"""Telegram message formatters — pure functions, no I/O."""


def format_scrape_result(result: dict) -> str:
    saved = result.get("saved", 0)
    stats = result.get("stats") or {}
    gecen = stats.get("gecen", saved)
    elenen = stats.get("elenen", 0)
    lines = [
        f"Tamamlandi! {saved} lead kaydedildi.",
        f"ICP'den gecen: {gecen}  |  Elenen: {elenen}",
        "",
        "Sonraki adim: /audit toplu",
    ]
    return "\n".join(lines)


def format_lead_list(leads: list, status: str | None = None) -> str:
    if not leads:
        return "Lead bulunamadi." + (f" (filtre: {status})" if status else "")
    header = f"Lead'ler ({status or 'tumu'}):"
    lines = [header, ""]
    for lead in leads:
        score = lead.get("opportunity_score")
        score_str = f"  skor:{score}" if score is not None else ""
        lines.append(
            f"• {lead['name']} — {lead.get('status', '?')}{score_str}\n"
            f"  ID: {lead['id']}"
        )
    return "\n".join(lines)


def format_audit(lead: dict, audit: dict) -> str:
    killer = audit.get("killer_insight") or ""
    metric = audit.get("killer_metric") or ""
    killer_line = killer + (f"  [{metric}]" if metric else "")

    urgency_emoji = {"yuksek": "🔴", "orta": "🟡", "dusuk": "🟢"}.get(audit.get("urgency") or "", "⚪")
    kalite_emoji = {"sicak": "🔥", "ilik": "☀", "soguk": "❄"}.get(audit.get("lead_quality") or "", "")

    result = audit.get("result") or {}
    ux_list = result.get("ux_hatalar") or []
    seo_list = result.get("seo_aciklar") or []
    hook_text = audit.get("hook_text") or ""
    hook_type = audit.get("hook_type") or "-"

    lines = [
        f"AUDIT — {lead.get('name', '-')}",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        "KILLER INSIGHT:",
        f"• {killer_line or '-'}",
        "",
        f"HOOK ({hook_type}):",
        f"• {hook_text or '-'}",
        "",
        "UX SORUNLARI:",
    ]
    for ux in ux_list[:3]:
        siddet = f"[{ux.get('siddet', '')}] " if ux.get("siddet") else ""
        line = f"• {siddet}{ux.get('sorun', '-')}"
        if ux.get("etki"):
            line += f" → {ux['etki']}"
        lines.append(line)

    if not ux_list:
        lines.append("• —")

    lines += ["", "SEO ACIKLARI:"]
    for seo in seo_list[:2]:
        lines.append(f"• {seo.get('sorun', '-')}")
    if not seo_list:
        lines.append("• —")

    ux_s = audit.get("ux_score") or 0
    seo_s = audit.get("seo_score") or 0
    conv_s = audit.get("conversion_score") or 0
    gen_s = audit.get("general_score") or 0

    lines += [
        "",
        f"Skor → UX:{ux_s}  SEO:{seo_s}  Donusum:{conv_s}  Genel:{gen_s}/100",
        f"{urgency_emoji} Urgency: {audit.get('urgency', '-')}  {kalite_emoji} Lead: {audit.get('lead_quality', '-')}",
    ]
    if audit.get("personal_insight"):
        lines += ["", f"Kisisel: {audit['personal_insight']}"]

    lines += ["", f"Sonraki: /mesaj {lead.get('id', '')}"]
    return "\n".join(lines)


def format_outreach(lead: dict, outreach: dict) -> str:
    lead_id = lead.get("id", "")
    recommended = outreach.get("recommended") or "v4"
    lines = [
        f"Mesajlar: {lead.get('name', '-')}",
        "",
        f"V1 (Merakli):\n{outreach.get('v1') or '—'}",
        "---",
        f"V2 (Dogrudan):\n{outreach.get('v2') or '—'}",
        "---",
        f"V3 (Nazik):\n{outreach.get('v3') or '—'}",
        "---",
        f"V4 (Proof-based):\n{outreach.get('v4') or '—'}",
        "",
        f"Onerilen: {recommended} | Gondermek icin: /gonder {lead_id} {recommended}",
    ]
    return "\n".join(lines)


def format_followup(text: str) -> str:
    return f"Followup:\n\n{text}"


def format_teklif_summary(lead: dict, content: dict) -> str:
    lines = [
        f"Teklif: {lead.get('name', '-')}",
        f"{content.get('paket_adi', '')} — {content.get('fiyat_araligi', '')}",
        "",
        content.get("neden_simdi", ""),
        "",
        content.get("cta", ""),
    ]
    return "\n".join(l for l in lines if l is not None)


def format_pipeline(counts: dict) -> str:
    total = sum(counts.values())
    lines = [
        f"Pipeline — {total} lead",
        "",
        f"Yeni: {counts.get('Yeni', 0)}  |  Audit: {counts.get('Audit', 0)}  |  Mesaj: {counts.get('Mesaj', 0)}",
        f"Cevap: {counts.get('Cevap', 0)}  |  Demo: {counts.get('Demo', 0)}  |  Teklif: {counts.get('Teklif', 0)}",
        f"Kapandi: {counts.get('Kapandi', 0)}  |  Soguk: {counts.get('Soguk', 0)}",
        "",
        "/audit toplu — bekleyen leadleri isle",
    ]
    return "\n".join(lines)


def format_yardim() -> str:
    return "\n".join([
        "AgencyOS Komutlari:",
        "",
        "/lead <sektor> <sehir> [ilce] [limit]  — Lead topla",
        "/liste [status]                         — Lead listesi (UUID ile)",
        "/audit <id | toplu>                     — Audit baslat",
        "/mesaj <lead_id>                        — Outreach mesaji uret",
        "/gonder <lead_id> <v1|v2|v3|v4>         — Gonderildi kaydet",
        "/followup <lead_id>                     — Takip mesaji uret",
        "/teklif <lead_id>                       — PDF teklif olustur",
        "/durum                                  — Pipeline ozeti",
        "/yardim                                 — Bu menu",
    ])
