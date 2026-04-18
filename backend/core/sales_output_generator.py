"""
Sales Output Generator — teknik audit'i müşteri satış diline çevirir.
Framework-agnostic: sadece dict alır, dict döner.
"""

import json
import logging
import re

import anthropic

logger = logging.getLogger(__name__)

_BLACKLIST = re.compile(
    r"\b(meta\s*description|h1|seo|ux|pagespeed|schema|title\s*tag|"
    r"optimize\s*et|görünürlüğünüzü\s*artır|yardımcı\s*olabiliriz|"
    r"hizmet\s*sunuyoruz|tespit\s*edildi|mevcut\s*değil|iyileştirme\s*fırsatı)\b",
    re.IGNORECASE | re.UNICODE,
)

_SEKTOR_DIL: dict[str, str] = {
    "ev_hizmetleri": "müşteri / çağrı / acil arama / telefon / bölge / müdahale",
    "klinik":        "hasta / danışan / randevu / güven / ilk temas / doktora ulaşma",
    "avukat":        "kişi / müvekkil / danışma / güven sinyali / uzmanlık / hukuki destek",
    "egitim":        "kayıt / öğrenci / güven / içerik / eğitimci / karar",
    "guzellik":      "randevu / işlem / karar verme / güven / hizmet kalitesi",
    "emlak":         "ilanı gören kişi / portföy / danışmana ulaşma / mülk",
    "kadin_dogum":   "hasta / randevu / güven / doktora erişim / sağlık / karar",
}

_PROMPT = """Teknik audit ciktisini musteriye gidecek satis ozetine cevir. Bu bir satis metni - teknik rapor degil.

KESINLIKLE KULLANMA: meta description, H1, SEO, UX, title, PageSpeed, schema, "optimize etmek", "gorunurlugunu artir", "yardimci olabiliriz", "hizmet sunuyoruz", "tespit edildi", "mevcut degil"

TERCIH ET: "musteri sizi bulamadan gidiyor", "guven son adimda kayboluyor", "talep var ama size donmuyor", "birkac kritik eksik yuzunden", "son adimda kaybediliyor"

SEKTORE OZGU DIL ({sektor}): {sektor_dil}

LEAD: {isim} | {adres} | Sektor: {sektor}

AUDIT OZETI:
Killer bulgu: {killer_bulgu} [{killer_rakam}]
En acitan nokta: {en_acitan}
Kisisel gozlem: {kisisel_insight}
UX sorunlari: {ux_hatalar}
SEO sorunlari: {seo_aciklar}
Donusum engelleri: {donusum_engelleri}
Lead kalitesi: {lead_kalitesi} | Urgency: {urgency}

AUDIT SATIS CEVIRME ORNEKLERI:
- "Form yok" -> "Musteri sizi aramadan cikabiliyor"
- "Meta local degil" -> "Komsu bolgede sizi arayan size ulasmiyor"
- "Yorumlar sitede yok" -> "Maps'teki guven sitede kayboluyor"
- "Hiz dusuk" -> "Site yavas acilinca musteri gitmis oluyor"
- "Tel link yok" -> "Sizi aramak isteyen bir tiklama fazla yapmak zorunda"

CIKTI: Sadece valid JSON. Preamble, markdown, kod blogu YASAK. Ilk karakter {{ olmali.
{{
  "headline": "{isim} icin kisa bir analiz yaptim.",
  "demand_block": "2-3 cumle. Talep var ama gorünurluk/donusum eksik. Bolge ve sektor referansi kullan. Teknik kelime yok.",
  "top_3_problems": [
    "emoji sorun kisaca → kayip etkisi",
    "emoji sorun kisaca → kayip etkisi",
    "emoji sorun kisaca → kayip etkisi"
  ],
  "insight_block": "2 cumle max. Guclu taraf var ama son adimda kayip var icgoru.",
  "solution_block": [
    "teknik jargon olmadan cozum 1",
    "teknik jargon olmadan cozum 2",
    "teknik jargon olmadan cozum 3"
  ],
  "cta_block": "Dusuk surtuenmeli kapalis. 1 gorusme onerisi. Alternatifli zaman teklifi.",
  "full_text": "Tum bloklar sirali tek metin halinde."
}}"""


def _build_prompt(lead: dict, audit: dict, playbook: dict) -> str:
    sector = playbook.get("sektor", lead.get("sektor", "genel"))
    top_sector = sector.split("_")[0] if "_" in sector else sector
    sektor_dil = _SEKTOR_DIL.get(top_sector, _SEKTOR_DIL.get(sector, "müşteri / güven / karar"))

    killer = audit.get("killer_insight") or {}
    ux = audit.get("ux_hatalar") or []
    seo = audit.get("seo_aciklar") or []
    donusum = audit.get("donusum_engelleri") or []

    ux_str = "; ".join(h.get("sorun", "") for h in ux[:3]) or "(yok)"
    seo_str = "; ".join(s.get("sorun", "") for s in seo[:3]) or "(yok)"
    don_str = "; ".join(d.get("engel", "") for d in donusum[:2]) or "(yok)"

    return _PROMPT.format(
        sektor=sector,
        sektor_dil=sektor_dil,
        isim=lead.get("isim") or "",
        adres=lead.get("adres") or "",
        killer_bulgu=killer.get("bulgu", ""),
        killer_rakam=killer.get("rakam", ""),
        en_acitan=audit.get("en_acitan_nokta", ""),
        kisisel_insight=audit.get("kisisel_insight", ""),
        ux_hatalar=ux_str,
        seo_aciklar=seo_str,
        donusum_engelleri=don_str,
        lead_kalitesi=audit.get("lead_kalitesi", "ilik"),
        urgency=audit.get("urgency", "orta"),
    )


def _build_full_text(out: dict) -> str:
    problems = "\n".join(f"- {p}" for p in out.get("top_3_problems", []))
    solutions = "\n".join(f"- {s}" for s in out.get("solution_block", []))
    return (
        f"{out.get('headline', '')}\n\n"
        f"{out.get('demand_block', '')}\n\n"
        f"Sitenizde 3 kritik nokta dikkatimi çekti:\n{problems}\n\n"
        f"{out.get('insight_block', '')}\n\n"
        f"Bu genelde birkaç net değişiklikle toparlanabiliyor:\n{solutions}\n\n"
        f"{out.get('cta_block', '')}"
    )


def validate_sales_output(output: dict) -> dict:
    """Validate and sanitize sales output. Returns dict with 'valid', 'issues', 'output'."""
    issues = []

    if len(output.get("top_3_problems", [])) < 3:
        issues.append("top_3_problems eksik (3 gerekli)")

    if not output.get("cta_block", "").strip():
        issues.append("cta_block bos")

    full = output.get("full_text", "")
    if len(full) < 150:
        issues.append(f"full_text cok kisa ({len(full)} karakter)")

    blacklist_hits = []
    for key, val in output.items():
        text = " ".join(val) if isinstance(val, list) else str(val)
        if _BLACKLIST.search(text):
            blacklist_hits.append(key)
    if blacklist_hits:
        issues.append(f"Teknik kelime gecen alanlar: {blacklist_hits}")

    if not output.get("full_text"):
        output["full_text"] = _build_full_text(output)

    return {"valid": len(issues) == 0, "issues": issues, "output": output}


async def generate_sales_output(lead: dict, audit: dict, playbook: dict) -> dict:
    """
    Teknik audit'i müşteriye gidecek satış özetine çevirir.

    Döner:
    {
      "headline": str,
      "demand_block": str,
      "top_3_problems": [str, str, str],
      "insight_block": str,
      "solution_block": [str, str, str],
      "cta_block": str,
      "full_text": str,
      "_valid": bool,
      "_issues": list[str],
    }
    """
    prompt = _build_prompt(lead, audit, playbook)

    client = anthropic.AsyncAnthropic()
    try:
        msg = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=900,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()

        # JSON fence temizle
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

        output = json.loads(raw)
    except Exception as e:
        logger.exception("Sales output generation failed: %s", e)
        output = _fallback_output(lead, audit)

    # full_text eksikse oluştur
    if not output.get("full_text"):
        output["full_text"] = _build_full_text(output)

    validation = validate_sales_output(output)
    output["_valid"] = validation["valid"]
    output["_issues"] = validation["issues"]

    if not validation["valid"]:
        logger.warning("Sales output validation issues: %s | lead=%s",
                       validation["issues"], lead.get("isim", "?"))

    return output


def _fallback_output(lead: dict, audit: dict) -> dict:
    killer = audit.get("killer_insight") or {}
    isim = lead.get("isim") or "İşletme"
    return {
        "headline": f"{isim} için kısa bir analiz yaptım.",
        "demand_block": (
            "Bölgenizde ciddi bir talep var. "
            "Ancak birkaç kritik eksik yüzünden bu talebin bir kısmı size gelmeden "
            "başka işletmelere gidiyor."
        ),
        "top_3_problems": [
            f"⚠️ {killer.get('bulgu', 'Kritik eksik tespit edildi')} → müşteri kaybı",
            "📞 Müşteri ile ilk temas zor → karar rakibe kayıyor",
            "🔍 Bölge aramasında görünürlük eksik → talep size ulaşmıyor",
        ],
        "insight_block": (
            f"{audit.get('en_acitan_nokta', 'Güçlü bir başlangıç noktanız var.')} "
            "Ama son adımda bazı eksikler müşteri kararını olumsuz etkiliyor."
        ),
        "solution_block": [
            "Müşteri ile ilk teması kolaylaştırmak",
            "Bölge odaklı görünürlüğü güçlendirmek",
            "Güven unsurlarını ön plana taşımak",
        ],
        "cta_block": (
            "İsterseniz bunu sizin özelinizde 10–15 dakikada net şekilde gösterebilirim. "
            "Yarın mı daha uygun olur, perşembe mi?"
        ),
        "full_text": "",
    }
