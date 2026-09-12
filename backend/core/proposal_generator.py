"""
Proposal Generator — Audit verisinden kişiselleştirilmiş PDF teklif üretir.
Her cümle gerçek bulgulara dayanır. Rakipler genel template gönderir, biz gerçek veri.
"""

from html import escape
from core.sales_policy import SALES_POLICY, PROPOSAL_TERMS

import asyncio
import logging
from datetime import datetime

from core.utils import safe_json_parse, API_SEMAPHORE, claude_api_call

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

PROPOSAL_PROMPT = """Sen dijital strateji alaninda calisiyorsun. Asagidaki audit verisini kullanarak
isletme sahibinin kendi durumunu fark etmesini saglayan, baski yaratmayan ama harekete geciren
bir teklif icerigi uret.

TON — Jarvis tarzi (ZORUNLU):
- Zeki ve ozguveli. Gozlem paylas, satis yapma.
- "Sizi takip ediyorum ve cozumum var" hissi — ama itmeden.
- Hafif mizahi olabilir, soguk degil.
- Her cumle audit verisine dayali. Jenerik ifade YASAK.
- Baski, FOMO, aciliyet yaratan ifade YASAK.
- Rakam kullan — ama "bu kadar kotu" degil "bu kadar firsat var" cercevesinde.

LEAD:
Isim: {isim}
Adres: {adres}
Sektor: {display_name}
Google puan: {puan} ({yorum_sayisi} yorum)
Lead kalitesi: {lead_kalitesi}

AUDIT OZETI:
Killer insight: {killer_bulgu} [{killer_rakam}]
En acitan nokta: {en_acitan}
Kisisel gozlem: {kisisel_insight}
Hizli kazanimlar: {hizli_kazanimlar}
Donusum engeli: {donusum_engeli}

ISTENEN CIKTI (sadece valid JSON, preamble yasak):
{{
  "baslik": "işletmeye özel çalışma önerisi başlığı",
  "giris": "2 cumle: kisisel_gozlem dogal kullanan, 'Sitenizi inceledim' yasak. Guclu bir olumlu tespitle baslar, sonra gap'e gec.",
  "durum_ozeti": [
    "doğrulanmış gözlem 1",
    "firsat 2",
    "firsat 3"
  ],
  "cozum": "2-3 cumle: ne yapilacak, neden bu isletme icin — spesifik, jargon yok",
  "baslangic_odaklari": [
    "Odak 1: quick win'ler (1-2 hafta)",
    "Odak 2: deneyim iyilestirmeleri",
    "Odak 3: gorunurluk ve olcum"
  ],
  "beklenen_sonuclar": [
    "izlenecek hedef 1; garanti veya uydurma rakam yok",
    "somut sonuc 2",
    "somut sonuc 3"
  ],
  "bir_sonraki_adim": "1 cumle — yumusak gecis: 'ne zaman bir bakalim?' tarzinda, sure belirtme, baski yok",
  "cta": "tek cumle — samimi, Jarvis vibe, 'Kahve icerken bakalim mi?' tarzinda. Asla '15 dakika', 'hizmet', 'ajans' yazma."
}}
"""


async def generate_proposal_content(lead: dict, audit: dict, playbook: dict) -> dict:
    async with API_SEMAPHORE:
        skorlar = audit.get("skorlar") or {}
        kazanimlar = audit.get("hizli_kazanimlar") or []
        donusum = (audit.get("donusum_engelleri") or [{}])[0]
        ilk = audit.get("ilk_izlenim") or {}
        killer = audit.get("killer_insight") or {}

        prompt = SALES_POLICY + PROPOSAL_PROMPT.format(
            isim=lead.get("isim") or "",
            adres=lead.get("adres") or "",
            display_name=playbook.get("display_name", ""),
            lead_kalitesi=audit.get("lead_kalitesi", "ilik"),
            puan=lead.get("puan", ""),
            yorum_sayisi=lead.get("yorum_sayisi", ""),
            killer_bulgu=killer.get("bulgu", ""),
            killer_rakam=killer.get("rakam", ""),
            en_acitan=audit.get("en_acitan_nokta", ""),
            kisisel_insight=audit.get("kisisel_insight", ""),
            hizli_kazanimlar=", ".join(kazanimlar[:3]),
            donusum_engeli=donusum.get("engel", ""),
        )

        isim = lead.get("isim") or "İşletmeniz"
        fallback = {
            "baslik": f"{isim} — Görünmez Kalan Fırsatlar",
            "giris": f"{killer.get('bulgu', 'Birkaç kritik alan dikkatimi çekti')}. "
                     f"{audit.get('kisisel_insight', '')}",
            "durum_ozeti": [
                audit.get("en_acitan_nokta", "Dijital varlık analiz bekleniyor"),
                donusum.get("engel", "Dönüşüm engeli tespit edildi"),
                "Bölge aramasında görünürlük güçlendirilebilir",
            ],
            "cozum": "Audit bulgularından hareketle en hızlı etki yaratacak noktalara odaklanıyoruz.",
            "baslangic_odaklari": [
                "Odak 1: Hızlı kazanımlar — ilk haftada devreye girebilecek değişiklikler",
                "Odak 2: Deneyim iyileştirmeleri — müşteri kararını kolaylaştırmak",
                "Odak 3: Görünürlük ve ölçüm — doğru kanalda, doğru kişilere ulaşmak",
            ],
            "beklenen_sonuclar": [
                "Sizi arayan müşterinin kararı kolaylaşır",
                "Bölge aramalarında daha görünür hale gelirsiniz",
                "Dijital varlık güven sinyali olarak çalışmaya başlar",
            ],
            "bir_sonraki_adim": "Bulgulara bakmak için uygun bir zaman seçebiliriz.",
            "cta": "Ne zaman bir bakalım?",
        }

        resp = await claude_api_call(prompt, max_tokens=1200, temperature=0.2)
        content = safe_json_parse(resp, fallback=fallback)
        content.update(PROPOSAL_TERMS)
        return content


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

def _score_bar(score: int) -> str:
    """Düşük skor = büyük fırsat. Sayıyı gösterme, etiketi göster."""
    if score >= 65:
        color, label = "#22c55e", "Güçlü"
    elif score >= 35:
        color, label = "#f97316", "Gelişme alanı"
    else:
        color, label = "#f97316", "Büyük fırsat"
    fill = max(score, 8)  # bar tamamen kaybolmasın
    return (
        f'<div class="bar-wrap">'
        f'<div class="bar" style="width:{fill}%;background:{color}"></div>'
        f'</div>'
        f'<span class="bar-val" style="color:{color}">{label}</span>'
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

    # --- Baslangic odaklari ---
    odaklar = content.get("baslangic_odaklari") or []
    if not odaklar:
        # geriye dönük uyumluluk: eski haftalik_plan varsa dönüştür
        plan = content.get("haftalik_plan") or {}
        odaklar = [v for v in plan.values() if v]
    odak_html = "".join(
        f'<tr><td class="week-num">→</td><td>{o}</td></tr>'
        for o in odaklar[:4]
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
  <div class="callout-label">Öne Çıkan Fırsat</div>
  <div class="callout-text">{killer.get("bulgu", "")} — {killer.get("rakam", "")}</div>
  <div class="callout-sub">{audit.get("kisisel_insight", "")}</div>
</div>

<!-- GİRİŞ -->
<h2>Bu Analizi Neden Hazırladım?</h2>
<p>{content.get("giris", "")}</p>

<!-- MEVCUT DURUM -->
<h2>Dijital Fırsat Haritası</h2>

<div class="scores-grid">
  <div class="score-box">
    <div class="score-label">Kullanıcı Deneyimi</div>
    {_score_bar(skorlar.get("ux", 0) or 0)}
  </div>
  <div class="score-box">
    <div class="score-label">Arama Görünürlüğü</div>
    {_score_bar(skorlar.get("seo", 0) or 0)}
  </div>
  <div class="score-box">
    <div class="score-label">Dönüşüm Potansiyeli</div>
    {_score_bar(skorlar.get("donusum", 0) or 0)}
  </div>
</div>

<p style="color:#7c3aed;font-weight:bold">{audit.get("en_acitan_nokta", "")}</p>

<ul>{durum_html}</ul>

<!-- UX BULGULARI -->
<h2>Deneyim Fırsatları</h2>
{ux_html}

<!-- SEO BULGULARI -->
<h2>Görünürlük Fırsatları</h2>
{seo_html}

<!-- HIZLI KAZANIMLAR -->
{'<h2>Hızlı Başlangıç Noktaları</h2><ul>' + kazanim_html + '</ul>' if kazanimlar else ""}

<!-- ÖNERILEN ÇÖZÜM -->
<div class="page-break"></div>
<h2>Nasıl Çalışırız?</h2>
<p>{content.get("cozum", "")}</p>

<!-- BAŞLANGIÇ ODAKLARI -->
<h2>Başlangıç Odakları</h2>
<table class="timeline-table">
  {odak_html}
</table>

<!-- BEKLENEN SONUÇLAR -->
<h2>Ne Değişir?</h2>
<ul>{sonuc_html}</ul>

<!-- BİR SONRAKI ADIM -->
<p style="font-size:9.5pt;color:#475569;margin-top:14px">{content.get("bir_sonraki_adim", "")}</p>

<!-- CTA -->
<h2>Kapsam ve ticari şartlar</h2>
{chr(10).join("<p><strong>" + escape(k.replace("_", " ")) + ":</strong> " + escape(str(content.get(k, v))) + "</p>" for k, v in PROPOSAL_TERMS.items())}
<div class="cta-box">
  <div class="cta-text">{content.get("cta", "Ne zaman bir bakalım?")}</div>
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


async def generate_proposal(lead: dict, audit: dict, playbook: dict) -> tuple[bytes, dict]:
    """Returns (pdf_bytes, content_dict). Caller handles persistence."""
    content = await generate_proposal_content(lead, audit, playbook)
    html = build_proposal_html(lead, audit, content, playbook)
    pdf_bytes = await asyncio.to_thread(render_pdf, html)
    logger.info("Teklif PDF uretildi: lead=%s (%d bytes)", lead.get("isim", "?"), len(pdf_bytes))
    return pdf_bytes, content
