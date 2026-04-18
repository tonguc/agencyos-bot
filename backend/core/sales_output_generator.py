"""
Sales Output Generator — teknik audit'i müşteri satış mesajlarına çevirir.
SHORT = direkt gönderilir | FULL = follow-up / detay için kullanılır.
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

_CTA_SIGNALS = re.compile(
    r"(isterseniz|gösterebilirim|konuşalım|görüşelim|ulaşın|yazın|çağrı|"
    r"dakikada|uygun|yarın|perşembe|pazartesi|zaman|toplantı)",
    re.IGNORECASE | re.UNICODE,
)

_SEKTOR_DIL: dict[str, dict[str, str]] = {
    "ev_hizmetleri": {"service": "müşteri",  "call": "arama / çağrı",        "unit": "kişi"},
    "klinik":        {"service": "hasta",    "call": "randevu",               "unit": "danışan"},
    "avukat":        {"service": "kişi",     "call": "danışma",               "unit": "müvekkil"},
    "egitim":        {"service": "öğrenci",  "call": "kayıt",                 "unit": "kayıt"},
    "guzellik":      {"service": "randevu",  "call": "işlem",                 "unit": "müşteri"},
    "emlak":         {"service": "müşteri",  "call": "ilan / danışmaya ulaşma", "unit": "portföy"},
    "kadin_dogum":   {"service": "hasta",    "call": "randevu",               "unit": "danışan"},
}

_PROMPT = """Teknik audit ciktisini IKI FARKLI satis mesajina cevir.

SHORT MESSAGE KURALLARI (EN KRITIK):
- Tam olarak 4 cumle. Fazlasi yasak.
- 400-500 karakter arasi
- YAPI: kisisel giris (isim/bolge) → spesifik gozlem (audit'ten) → musteri kaybi etkisi → dusuk surtuenmeli CTA
- KESINLIKLE KULLANMA: SEO, UX, meta, H1, PageSpeed, teknik terim, "optimizasyon", "gorunurluk artirma"
- KULLAN: "musteri sizi bulamadan gidiyor", "sizi arayan kisi", "karar rakibe kayiyor", "talep size gelmeden baska yere gidiyor"

FULL MESSAGE KURALLARI:
- 8-12 satir, sadece \\n ile ayr
- Baslik KULLANMA, emoji max 3 adet
- YAPI: giris → talep blogu → "3 kritik nokta:" listesi (mutlaka 3 madde - ile) → icgoru → cozum cercevesi (3 madde - ile) → CTA
- Teknik kelime yok, her cumle farkli olmali
- Ornek akis:
  "[isim] icin biraz daha detayli baktim.\\n\\n[bolge/sektor talep aciklamasi]\\n\\n3 kritik nokta:\\n- ...\\n- ...\\n- ...\\n\\n[icgoru cumle]\\n\\nBu genelde birkas net degisiklikle toparlanabiliyor:\\n- ...\\n- ...\\n- ...\\n\\n[CTA]"

SEKTORE OZGU DIL ({sektor}): {sektor_dil}

LEAD: {isim} | {adres} | Sektor: {sektor}

AUDIT OZETI:
Killer bulgu: {killer_bulgu} [{killer_rakam}]
En acitan nokta: {en_acitan}
Kisisel gozlem: {kisisel_insight}
UX sorunlari: {ux_hatalar}
Donusum engelleri: {donusum_engelleri}
Lead kalitesi: {lead_kalitesi} | Urgency: {urgency}

DONUSTURMELER:
"Form yok" → "musteri sizi aramadan cikabiliyor"
"Hiz dusuk" → "site yavas acilinca musteri gitmis oluyor"
"Tel link yok" → "sizi aramak isteyen bir tiklama fazla yapmak zorunda"
"Yorumlar yok" → "Maps'teki guven sitede kayboluyor"

CIKTI: Sadece valid JSON. Preamble yok, markdown yok, kod blogu yok. Ilk karakter {{ olmali.
{{
  "short_message": "4 cumle. Tek blok. Hic baslik/format yok. Direkt gonderilebilir.",
  "full_message": "Cok satirli metin. Sadece \\n satirlari. Hic baslik yok.",
  "meta": {{"sector": "{sektor}", "tone": "direkt"}}
}}"""


def _sektor_dil_str(sector: str) -> str:
    top = sector.split("_")[0] if "_" in sector else sector
    dil = _SEKTOR_DIL.get(sector) or _SEKTOR_DIL.get(top)
    if dil:
        return f"{dil['service']} / {dil['call']} / {dil['unit']}"
    return "müşteri / güven / karar"


def _build_prompt(lead: dict, audit: dict, playbook: dict) -> str:
    sector = playbook.get("sektor", lead.get("sektor", "genel"))
    killer = audit.get("killer_insight") or {}
    ux = audit.get("ux_hatalar") or []
    donusum = audit.get("donusum_engelleri") or []

    return _PROMPT.format(
        sektor=sector,
        sektor_dil=_sektor_dil_str(sector),
        isim=lead.get("isim") or "",
        adres=lead.get("adres") or "",
        killer_bulgu=killer.get("bulgu", ""),
        killer_rakam=killer.get("rakam", ""),
        en_acitan=audit.get("en_acitan_nokta", ""),
        kisisel_insight=audit.get("kisisel_insight", ""),
        ux_hatalar="; ".join(h.get("sorun", "") for h in ux[:3]) or "(yok)",
        donusum_engelleri="; ".join(d.get("engel", "") for d in donusum[:2]) or "(yok)",
        lead_kalitesi=audit.get("lead_kalitesi", "ilik"),
        urgency=audit.get("urgency", "orta"),
    )


def _auto_trim_short(text: str) -> str:
    """500 karakter aşıyorsa en uzun cümleyi çıkar."""
    if len(text) <= 500:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sentences) <= 1:
        return text[:500]
    longest = max(range(len(sentences)), key=lambda i: len(sentences[i]))
    sentences.pop(longest)
    return " ".join(sentences)


def validate_sales_messages(output: dict) -> dict:
    """
    Returns {'valid': bool, 'issues': list[str]}

    SHORT: ≤4 cümle, ≤500 karakter, teknik kelime yok, CTA var
    FULL: ≥6 satır, ≥3 madde (-), CTA var
    """
    issues = []
    short = output.get("short_message", "")
    full = output.get("full_message", "")

    sentence_count = len(re.split(r"(?<=[.!?])\s+", short.strip()))
    if sentence_count > 4:
        issues.append(f"short_message 4 cümleden fazla ({sentence_count} cümle)")
    if len(short) > 500:
        issues.append(f"short_message 500 karakterden uzun ({len(short)})")
    if _BLACKLIST.search(short):
        issues.append("short_message teknik kelime içeriyor")
    if not _CTA_SIGNALS.search(short):
        issues.append("short_message CTA içermiyor")

    lines = [l for l in full.splitlines() if l.strip()]
    if len(lines) < 6:
        issues.append(f"full_message 6 satırdan kısa ({len(lines)} satır)")
    bullet_count = len(re.findall(r"^\s*-\s+", full, re.MULTILINE))
    if bullet_count < 3:
        issues.append(f"full_message 3 problem içermiyor ({bullet_count} madde)")
    if not _CTA_SIGNALS.search(full):
        issues.append("full_message CTA içermiyor")

    return {"valid": len(issues) == 0, "issues": issues}


async def generate_sales_output(lead: dict, audit: dict, playbook: dict) -> dict:
    """
    Returns:
    {
      "short_message": str,   # direkt gönderilir (WhatsApp / DM / e-mail)
      "full_message":  str,   # follow-up / detay için
      "meta": {"sector": str, "tone": str},
      "_valid": bool,
      "_issues": list[str],
    }
    """
    prompt = _build_prompt(lead, audit, playbook)
    client = anthropic.AsyncAnthropic()

    output: dict | None = None
    for attempt in range(2):
        try:
            msg = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-z]*\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
            output = json.loads(raw)
        except Exception as e:
            logger.exception("Sales output generation failed (attempt %s): %s", attempt + 1, e)
            output = _fallback_output(lead, audit)
            break

        if output.get("short_message") and len(output["short_message"]) > 500:
            output["short_message"] = _auto_trim_short(output["short_message"])

        validation = validate_sales_messages(output)
        if validation["valid"] or attempt == 1:
            break
        logger.warning("Sales output retry (attempt 1 failed): %s", validation["issues"])

    if output is None:
        output = _fallback_output(lead, audit)

    if output.get("short_message") and len(output["short_message"]) > 500:
        output["short_message"] = _auto_trim_short(output["short_message"])

    validation = validate_sales_messages(output)
    output["_valid"] = validation["valid"]
    output["_issues"] = validation["issues"]

    if not validation["valid"]:
        logger.warning("Sales output final issues: %s | lead=%s",
                       validation["issues"], lead.get("isim", "?"))

    return output


def _fallback_output(lead: dict, audit: dict) -> dict:
    killer = audit.get("killer_insight") or {}
    isim = lead.get("isim") or "İşletmeniz"
    adres = lead.get("adres") or "bölgenizde"

    short = (
        f"{isim} için kısa bir analiz yaptım. "
        f"{killer.get('bulgu', 'Birkaç kritik nokta dikkatimi çekti')} — "
        f"bu durum sizi arayan kişilerin kararını olumsuz etkileyebilir. "
        f"İsterseniz bunu 10–15 dakikada net şekilde gösterebilirim."
    )

    full = (
        f"{isim} için biraz daha detaylı baktım.\n\n"
        f"{adres} bölgesinde ciddi bir talep var ama birkaç kritik eksik yüzünden "
        f"bu talebin bir kısmı size gelmeden başka işletmelere gidiyor.\n\n"
        f"3 kritik nokta:\n"
        f"- {killer.get('bulgu', 'Kritik eksik tespit edildi')} → müşteri kaybı\n"
        f"- Müşteri ile ilk temas zor → karar rakibe kayıyor\n"
        f"- Bölge aramasında görünürlük eksik → talep size ulaşmıyor\n\n"
        f"{audit.get('en_acitan_nokta', 'Güçlü bir başlangıç noktanız var.')} "
        f"Ama son adımda bazı eksikler müşteri kararını olumsuz etkiliyor.\n\n"
        f"Bu genelde birkaç net değişiklikle toparlanabiliyor:\n"
        f"- Müşteri ile ilk teması kolaylaştırmak\n"
        f"- Güven unsurlarını ön plana taşımak\n"
        f"- Bölge odaklı erişimi güçlendirmek\n\n"
        f"İsterseniz bunu sizin örneğinizde kısa bir görüşmede gösterebilirim. "
        f"Yarın mı daha uygun olur, perşembe mi?"
    )

    return {
        "short_message": short,
        "full_message": full,
        "meta": {"sector": lead.get("sektor", "genel"), "tone": "direkt"},
    }
