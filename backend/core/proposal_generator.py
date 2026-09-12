"""
Proposal Generator — Audit verisinden kişiselleştirilmiş PDF teklif üretir.
Her cümle gerçek bulgulara dayanır. Rakipler genel template gönderir, biz gerçek veri.
"""

from html import escape
from core.sales_policy import SALES_POLICY, PROPOSAL_TERMS, missing_site_proposal

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
    if not lead.get("website"):
        return missing_site_proposal(lead)
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
    """Customer document: scope and narrative, without internal lead scores."""
    labels = [
        ("durum_ozeti", "Başlangıç noktamız"), ("cozum", "Size önerdiğimiz çalışma"),
        ("baslangic_odaklari", "Çalışma kapsamı"), ("beklenen_sonuclar", "Hedeflediğimiz katkı"),
        ("fiyat_araligi", "Ücret ve ödeme"), ("teslim_suresi", "Çalışma takvimi"),
        ("bakim_destek", "Yayın sonrası destek"), ("kapsam_siniri", "Çalışma koşulları"),
        ("bir_sonraki_adim", "Nasıl başlayalım?"),
    ]
    def render_value(value):
        if isinstance(value, list):
            return "<ul>" + "".join("<li>" + escape(str(item)) + "</li>" for item in value) + "</ul>"
        return "<p>" + escape(str(value)) + "</p>"
    sections = "".join(
        "<section><h2>" + title + "</h2>" + render_value(content.get(key, PROPOSAL_TERMS.get(key, ""))) + "</section>"
        for key, title in labels if content.get(key) or PROPOSAL_TERMS.get(key)
    )
    title = escape(str(content.get("baslik") or lead.get("isim") or "Çalışma önerisi"))
    intro = escape(str(content.get("giris") or ""))
    status = escape(str(content.get("teklif_durumu") or PROPOSAL_TERMS["teklif_durumu"]))
    cta = escape(str(content.get("cta") or ""))
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<style>
@page {{ size:A4; margin:18mm; @bottom-right {{ content:counter(page); font-size:9pt; color:#64748b; }} }}
body {{ font-family:'DejaVu Sans',Arial,sans-serif; font-size:9.5pt; line-height:1.4; color:#243247; }}
header {{ border-bottom:2px solid #246b78; padding-bottom:12px; margin-bottom:18px; }}
.brand {{ color:#246b78; font-size:9pt; letter-spacing:1px; }}
h1 {{ font-size:18pt; line-height:1.25; margin:10px 0; color:#163843; }}
h2 {{ font-size:11pt; color:#163843; margin:10px 0 4px; }}
p {{ margin:4px 0 8px; }} ul {{ padding-left:18px; margin:4px 0 8px; }}
li {{ margin:3px 0; }} section {{ break-inside:avoid; }}
.status {{ color:#64748b; font-size:9pt; }}
.cta {{ margin-top:18px; padding:12px; background:#edf5f6; border-left:3px solid #246b78; }}
footer {{ border-top:1px solid #dce4e8; margin-top:20px; padding-top:8px; color:#64748b; font-size:8pt; }}
</style></head><body>
<header><div class="brand">TONGUÇ · DİJİTAL ÇÖZÜMLER</div><h1>{title}</h1><div class="status">{status}</div></header>
<p>{intro}</p>{sections}<div class="cta">{cta}</div>
<footer>Hazırlayan: Tonguç · {datetime.now().strftime('%d.%m.%Y')}</footer>
</body></html>"""


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
