"""
Proposal Generator — Audit verisinden kişiselleştirilmiş PDF teklif üretir.
Her cümle gerçek bulgulara dayanır. Rakipler genel template gönderir, biz gerçek veri.
"""

import asyncio
import logging
import os
import re
import tempfile
from datetime import datetime

from core.utils import safe_json_parse, API_SEMAPHORE, claude_api_call

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

PROPOSAL_PROMPT = """Sen, gelir odakli dijital ajans tekliflerinde uzman bir stratejist olarak calisiyorsun.
Asagidaki audit verilerini kullanarak bir isletme sahibini ikna edecek teklif icerigi uret.

KURAL:
- Her cumle audit verisine atif yapmali. Jenerik ifade YASAK.
- Rakam kullanmak ZORUNLU (audit'ten alinan spesifik metrikler).
- Dil: Turkce, profesyonel ama soguk degil. Guven veren, baskici degil.
- Fiyat mant: Turk piyasasi, kobiyet olcegi, is hacmiyle orantili.

LEAD:
Isim: {isim}
Adres: {adres}
Sektor: {display_name}
Lead kalitesi: {lead_kalitesi}
Urgency: {urgency}

AUDIT OZETI:
Genel skor: {genel_skor}/100
UX: {ux_skoru}  SEO: {seo_skoru}  Donusum: {donusum_skoru}
Killer insight: {killer_bulgu} [{killer_rakam}]
En acitan nokta: {en_acitan}
Kisisel gozlem: {kisisel_insight}
Hizli kazanimlar: {hizli_kazanimlar}
Donusum engeli: {donusum_engeli}
Ilk surtunum: {ilk_surtunum}

ISTENEN CIKTI (sadece valid JSON, preamble yasak):
{{
  "baslik": "tek cumle, rakam iceren, isletme ozelinde kapan baslik",
  "giris": "2 cumle: kisisel_gozlem'i dogal kullanan, isletme sahibinin dikkati ceken acilis",
  "durum_ozeti": "3 madde liste — mevcut durumun en kritik 3 problemi (audit verisinden, rakamli)",
  "cozum": "2-3 cumle: ne yapilacak, neden bu isletme icin dogru cozum (spesifik)",
  "haftalik_plan": {{
    "1": "Audit bulgularindan quick win'lerin uygulamasi",
    "2": "UX ve donusum iyilestirmeleri",
    "3": "SEO ve icerik optimizasyonu",
    "4": "Test, olcum, raporlama"
  }},
  "beklenen_sonuclar": [
    "somut sonuc 1 (rakamli tahmin)",
    "somut sonuc 2",
    "somut sonuc 3"
  ],
  "neden_simdi": "1 cumle — bu isletme icin gecikmenin maliyeti (rakamli veya somut)",
  "paket_adi": "kisa paket adi (ornek: 'Dijital Buyume Paketi')",
  "fiyat_araligi": "X.000 - Y.000 TL (is kapsamina gore Turk piyasasi gercekci aralik)",
  "cta": "tek cumle — net, baski olmayan harekete gecirici"
}}
"""


async def generate_proposal_content(lead: dict, audit: dict, playbook: dict) -> dict:
    async with API_SEMAPHORE:
        skorlar = audit.get("skorlar") or {}
        kazanimlar = audit.get("hizli_kazanimlar") or []
        donusum = (audit.get("donusum_engelleri") or [{}])[0]
        ilk = audit.get("ilk_izlenim") or {}
        killer = audit.get("killer_insight") or {}

        prompt = PROPOSAL_PROMPT.format(
            isim=lead.get("isim") or "",
            adres=lead.get("adres") or "",
            display_name=playbook.get("display_name", ""),
            lead_kalitesi=audit.get("lead_kalitesi", "ilik"),
            urgency=audit.get("urgency", "orta"),
            genel_skor=audit.get("genel_skor", 0),
            ux_skoru=skorlar.get("ux", 0),
            seo_skoru=skorlar.get("seo", 0),
            donusum_skoru=skorlar.get("donusum", 0),
            killer_bulgu=killer.get("bulgu", ""),
            killer_rakam=killer.get("rakam", ""),
            en_acitan=audit.get("en_acitan_nokta", ""),
            kisisel_insight=audit.get("kisisel_insight", ""),
            hizli_kazanimlar=", ".join(kazanimlar[:3]),
            donusum_engeli=donusum.get("engel", ""),
            ilk_surtunum=ilk.get("ilk_surtunum", ""),
        )

        fallback = {
            "baslik": f"{lead.get('isim', '')} icin Dijital Buyume Teklifiniz",
            "giris": "Sitenizi inceledim ve birkac kritik alan dikkatimi cekti.",
            "durum_ozeti": [audit.get("en_acitan_nokta", "Analiz bekleniyor")],
            "cozum": "Audit bulgularini temel alan kapsamli bir iyilestirme paketi sunuyorum.",
            "haftalik_plan": {"1": "Quick wins", "2": "UX", "3": "SEO", "4": "Test"},
            "beklenen_sonuclar": ["Donusum artisi", "SEO gorunurlugu", "Kullanici deneyimi"],
            "neden_simdi": "Her gecen gun potansiyel musteri kaybediliyor.",
            "paket_adi": "Dijital Buyume Paketi",
            "fiyat_araligi": "5.000 - 15.000 TL",
            "cta": "15 dakikalik bir gorusme ayarlayalim.",
        }

        resp = await claude_api_call(prompt, max_tokens=1200, temperature=0.2)
        return safe_json_parse(resp, fallback=fallback)


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

def _score_bar(score: int) -> str:
    color = "#22c55e" if score >= 65 else ("#f97316" if score >= 35 else "#ef4444")
    return (
        f'<div class="bar-wrap">'
        f'<div class="bar" style="width:{score}%;background:{color}"></div>'
        f'</div>'
        f'<span class="bar-val">{score}/100</span>'
    )


def _severity_badge(siddet: str) -> str:
    colors = {"yuksek": ("#fef2f2", "#ef4444"), "orta": ("#fff7ed", "#f97316"), "dusuk": ("#f8fafc", "#94a3b8")}
    bg, fg = colors.get(siddet, ("#f8fafc", "#94a3b8"))
    labels = {"yuksek": "KRİTİK", "orta": "ORTA", "dusuk": "DÜŞÜK"}
    return f'<span class="badge" style="background:{bg};color:{fg}">{labels.get(siddet, siddet.upper())}</span>'


def _kalite_label(k: str) -> str:
    return {"sicak": ("🔥 Sıcak Fırsat", "#f97316"), "ilik": ("☀ İyi Fırsat", "#eab308"), "soguk": ("❄ Potansiyel", "#64748b")}.get(k, (k, "#64748b"))


def build_proposal_html(lead: dict, audit: dict, content: dict, playbook: dict) -> str:
    isim = lead.get("isim") or "İşletme"
    tarih = datetime.now().strftime("%d %B %Y")
    skorlar = audit.get("skorlar") or {}
    killer = audit.get("killer_insight") or {}
    ux_list = audit.get("ux_hatalar") or []
    seo_list = audit.get("seo_aciklar") or []
    kazanimlar = audit.get("hizli_kazanimlar") or []
    ilk = audit.get("ilk_izlenim") or {}
    genel = audit.get("genel_skor", 0)
    kalite_label, kalite_color = _kalite_label(audit.get("lead_kalitesi", "ilik"))

    # --- UX issues ---
    ux_html = ""
    for ux in ux_list[:4]:
        siddet = ux.get("siddet", "orta")
        ux_html += f"""
        <div class="issue-card">
          <div class="issue-header">
            {_severity_badge(siddet)}
            <span class="issue-title">{ux.get('sorun', '')}</span>
          </div>
          {'<p class="issue-impact">→ ' + ux.get("etki", "") + '</p>' if ux.get("etki") else ""}
          {'<p class="issue-fix">✓ ' + ux.get("cozum", "") + '</p>' if ux.get("cozum") else ""}
        </div>"""

    # --- SEO issues ---
    seo_html = ""
    for seo in seo_list[:3]:
        seo_html += f"""
        <div class="issue-card">
          <div class="issue-header">
            <span class="issue-title">{seo.get('sorun', '')}</span>
          </div>
          {'<p class="issue-impact">→ ' + seo.get("etki", "") + '</p>' if seo.get("etki") else ""}
          {'<p class="issue-fix">✓ ' + seo.get("cozum", "") + '</p>' if seo.get("cozum") else ""}
        </div>"""

    # --- Quick wins ---
    kazanim_html = "".join(f'<li>{k}</li>' for k in kazanimlar[:3])

    # --- Durum ozeti ---
    durum_items = content.get("durum_ozeti", [])
    if isinstance(durum_items, str):
        durum_items = [durum_items]
    durum_html = "".join(f'<li>{d}</li>' for d in durum_items[:3])

    # --- Sonuclar ---
    sonuc_items = content.get("beklenen_sonuclar", [])
    if isinstance(sonuc_items, str):
        sonuc_items = [sonuc_items]
    sonuc_html = "".join(f'<li>{s}</li>' for s in sonuc_items[:3])

    # --- Haftalik plan ---
    plan = content.get("haftalik_plan") or {}
    plan_html = "".join(
        f'<tr><td class="week-num">Hafta {h}</td><td>{plan.get(str(h), "")}</td></tr>'
        for h in range(1, 5)
    )

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<style>
  @page {{ margin: 18mm 16mm; size: A4; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: DejaVu Sans, Liberation Sans, Arial, sans-serif; font-size: 10pt; color: #1e293b; line-height: 1.55; }}

  /* Header */
  .cover {{ background: #0f172a; color: #fff; padding: 32px 36px 28px; border-radius: 0 0 12px 12px; margin-bottom: 28px; }}
  .cover-label {{ font-size: 8pt; letter-spacing: 2px; text-transform: uppercase; color: #94a3b8; margin-bottom: 6px; }}
  .cover-title {{ font-size: 20pt; font-weight: bold; color: #fff; line-height: 1.2; }}
  .cover-sub {{ font-size: 10pt; color: #cbd5e1; margin-top: 8px; }}
  .cover-meta {{ margin-top: 18px; display: flex; gap: 24px; }}
  .meta-pill {{ background: #1e3a5f; color: #93c5fd; font-size: 8pt; padding: 4px 12px; border-radius: 20px; }}

  /* Sections */
  h2 {{ font-size: 12pt; font-weight: bold; color: #0f172a; border-left: 4px solid #f97316; padding-left: 10px; margin: 26px 0 12px; }}
  h3 {{ font-size: 10pt; font-weight: bold; color: #334155; margin: 14px 0 6px; }}
  p {{ margin-bottom: 8px; color: #334155; }}

  /* Callout */
  .callout {{ background: #fff7ed; border-left: 4px solid #f97316; padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 12px 0; }}
  .callout-label {{ font-size: 7.5pt; font-weight: bold; text-transform: uppercase; color: #ea580c; letter-spacing: 1px; margin-bottom: 4px; }}
  .callout-text {{ font-size: 10.5pt; font-weight: bold; color: #1e293b; }}
  .callout-sub {{ font-size: 9pt; color: #7c3aed; margin-top: 4px; }}

  /* Scores */
  .scores-grid {{ display: flex; gap: 14px; margin: 12px 0; }}
  .score-box {{ flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; }}
  .score-label {{ font-size: 7.5pt; text-transform: uppercase; letter-spacing: 1px; color: #64748b; margin-bottom: 6px; }}
  .bar-wrap {{ background: #e2e8f0; border-radius: 4px; height: 7px; width: 100%; margin-bottom: 4px; }}
  .bar {{ height: 7px; border-radius: 4px; }}
  .bar-val {{ font-size: 9pt; font-weight: bold; color: #1e293b; }}
  .genel-box {{ background: #0f172a; color: #fff; border-radius: 8px; padding: 10px 14px; text-align: center; min-width: 80px; }}
  .genel-num {{ font-size: 22pt; font-weight: bold; color: #f97316; line-height: 1; }}
  .genel-lbl {{ font-size: 7.5pt; color: #94a3b8; margin-top: 2px; }}

  /* Issue cards */
  .issue-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; }}
  .issue-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }}
  .issue-title {{ font-size: 9.5pt; font-weight: bold; color: #1e293b; }}
  .issue-impact {{ font-size: 9pt; color: #b45309; margin: 2px 0; }}
  .issue-fix {{ font-size: 9pt; color: #15803d; margin: 2px 0; }}
  .badge {{ font-size: 7pt; font-weight: bold; padding: 2px 7px; border-radius: 12px; letter-spacing: 0.5px; }}

  /* Lists */
  ul, ol {{ padding-left: 18px; margin: 6px 0; }}
  li {{ margin-bottom: 5px; color: #334155; font-size: 9.5pt; }}

  /* Timeline */
  .timeline-table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
  .timeline-table tr {{ border-bottom: 1px solid #e2e8f0; }}
  .timeline-table td {{ padding: 8px 10px; font-size: 9.5pt; vertical-align: top; }}
  .week-num {{ font-weight: bold; color: #f97316; white-space: nowrap; width: 70px; }}

  /* Investment */
  .invest-box {{ background: #0f172a; color: #fff; border-radius: 12px; padding: 20px 24px; margin: 14px 0; }}
  .invest-pkg {{ font-size: 11pt; font-weight: bold; color: #f97316; margin-bottom: 6px; }}
  .invest-price {{ font-size: 20pt; font-weight: bold; color: #fff; }}
  .invest-note {{ font-size: 8.5pt; color: #94a3b8; margin-top: 6px; }}

  /* CTA */
  .cta-box {{ background: #f0fdf4; border: 2px solid #22c55e; border-radius: 10px; padding: 14px 18px; margin-top: 18px; text-align: center; }}
  .cta-text {{ font-size: 11pt; font-weight: bold; color: #15803d; }}
  .cta-neden {{ font-size: 8.5pt; color: #166534; margin-top: 4px; }}

  /* Kalite pill */
  .kalite-pill {{ display: inline-block; font-size: 8pt; font-weight: bold; padding: 3px 12px; border-radius: 20px; color: {kalite_color}; background: {kalite_color}22; border: 1px solid {kalite_color}55; }}

  /* Footer */
  .footer {{ margin-top: 28px; padding-top: 12px; border-top: 1px solid #e2e8f0; display: flex; justify-content: space-between; font-size: 8pt; color: #94a3b8; }}
  .page-break {{ page-break-before: always; }}
</style>
</head>
<body>

<!-- COVER -->
<div class="cover">
  <div class="cover-label">Dijital Büyüme Analizi &amp; Teklif</div>
  <div class="cover-title">{content.get("baslik", isim + " — Büyüme Teklifiniz")}</div>
  <div class="cover-sub">{playbook.get("display_name", "")} · {lead.get("adres", "")}</div>
  <div class="cover-meta">
    <span class="meta-pill">{tarih}</span>
    <span class="meta-pill kalite-pill">{kalite_label}</span>
    <span class="meta-pill">Hazırlayan: AgencyOS</span>
  </div>
</div>

<!-- KILLER CALLOUT -->
<div class="callout">
  <div class="callout-label">En Kritik Bulgu</div>
  <div class="callout-text">{killer.get("bulgu", "")} — {killer.get("rakam", "")}</div>
  <div class="callout-sub">{audit.get("kisisel_insight", "")}</div>
</div>

<!-- GİRİŞ -->
<h2>Neden Bu Teklifi Hazırladım?</h2>
<p>{content.get("giris", "")}</p>

<!-- MEVCUT DURUM -->
<h2>Mevcut Durum Analizi</h2>

<div class="scores-grid">
  <div class="score-box">
    <div class="score-label">UX / Kullanılabilirlik</div>
    {_score_bar(skorlar.get("ux", 0))}
  </div>
  <div class="score-box">
    <div class="score-label">SEO / Görünürlük</div>
    {_score_bar(skorlar.get("seo", 0))}
  </div>
  <div class="score-box">
    <div class="score-label">Dönüşüm</div>
    {_score_bar(skorlar.get("donusum", 0))}
  </div>
  <div class="genel-box">
    <div class="genel-num">{genel}</div>
    <div class="genel-lbl">Genel Skor</div>
  </div>
</div>

<p style="color:#7c3aed;font-weight:bold">{audit.get("en_acitan_nokta", "")}</p>

<ul>{durum_html}</ul>

<!-- UX BULGULARI -->
<h2>Kullanıcı Deneyimi Sorunları</h2>
{ux_html}

<!-- SEO BULGULARI -->
<h2>SEO &amp; Görünürlük Açıkları</h2>
{seo_html}

<!-- HIZLI KAZANIMLAR -->
{'<h2>Hızlı Kazanımlar (Max 1 Hafta)</h2><ul>' + kazanim_html + '</ul>' if kazanimlar else ""}

<!-- ÖNERILEN ÇÖZÜM -->
<div class="page-break"></div>
<h2>Önerilen Çözüm</h2>
<p>{content.get("cozum", "")}</p>

<!-- HAFTALIK PLAN -->
<h2>Uygulama Takvimi</h2>
<table class="timeline-table">
  {plan_html}
</table>

<!-- BEKLENEN SONUÇLAR -->
<h2>Beklenen Sonuçlar</h2>
<ul>{sonuc_html}</ul>

<!-- YATIRIM -->
<h2>Yatırım</h2>
<div class="invest-box">
  <div class="invest-pkg">{content.get("paket_adi", "Dijital Büyüme Paketi")}</div>
  <div class="invest-price">{content.get("fiyat_araligi", "")}</div>
  <div class="invest-note">KDV hariç · Aylık yönetim ve raporlama dahil · Sözleşme yok, esnek çalışma</div>
</div>

<!-- NEDEN ŞİMDİ -->
<p style="font-size:9.5pt;color:#b45309"><strong>Neden şimdi?</strong> {content.get("neden_simdi", "")}</p>

<!-- CTA -->
<div class="cta-box">
  <div class="cta-text">{content.get("cta", "15 dakikalık bir görüşme ayarlayalım.")}</div>
</div>

<!-- FOOTER -->
<div class="footer">
  <span>AgencyOS · behance.net/tonguc</span>
  <span>{tarih} · {isim}</span>
</div>

</body>
</html>"""


def render_pdf(html: str) -> bytes:
    import weasyprint
    return weasyprint.HTML(string=html).write_pdf()


async def generate_proposal(lead: dict, audit: dict, playbook: dict) -> tuple[str, dict]:
    """Returns (pdf_path, content_dict)."""
    content = await generate_proposal_content(lead, audit, playbook)
    html = build_proposal_html(lead, audit, content, playbook)

    pdf_bytes = await asyncio.to_thread(render_pdf, html)

    isim_slug = re.sub(r"[^\w]", "_", (lead.get("isim") or "teklif").lower())[:30]
    tarih = datetime.now().strftime("%Y%m%d")
    fname = f"teklif_{isim_slug}_{tarih}.pdf"

    tmp_dir = tempfile.mkdtemp(prefix="agencyos_")
    path = os.path.join(tmp_dir, fname)
    with open(path, "wb") as f:
        f.write(pdf_bytes)

    logger.info("Teklif PDF uretildi: %s (%d bytes)", fname, len(pdf_bytes))
    return path, content
