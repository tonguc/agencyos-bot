"""
Sales Output Generator — teknik audit'i müşteri satış mesajlarına çevirir.
SHORT = direkt gönderilir | FULL = follow-up / detay için kullanılır.
"""

import logging
import re

import anthropic
from config import settings

logger = logging.getLogger(__name__)

_BLACKLIST = re.compile(
    r"\b(meta\s*description|h1|seo|ux|pagespeed|schema|title\s*tag|"
    r"optimize\s*et|görünürlüğünüzü\s*artır|yardımcı\s*olabiliriz|"
    r"hizmet\s*sunuyoruz|tespit\s*edildi|mevcut\s*değil|iyileştirme\s*fırsatı)\b",
    re.IGNORECASE | re.UNICODE,
)

_CTA_SIGNALS = re.compile(
    r"(isterseniz|gösterebilirim|konuşalım|görüşelim|ulaşın|yazın|çağrı|"
    r"dakikada|uygun|yarın|perşembe|pazartesi|zaman|toplantı|"
    r"atabilirim|bakabiliriz|paylaşayım|göndereyim|musunuz|misiniz)",
    re.IGNORECASE | re.UNICODE,
)

_SEKTOR_DIL: dict[str, dict[str, str]] = {
    "ev_hizmetleri": {"service": "müşteri",  "call": "arama / çağrı",        "unit": "kişi",     "label": "ev hizmetleri"},
    "klinik":        {"service": "hasta",    "call": "randevu",               "unit": "danışan",  "label": "klinik"},
    "avukat":        {"service": "kişi",     "call": "danışma",               "unit": "müvekkil", "label": "avukat bürosu"},
    "egitim":        {"service": "öğrenci",  "call": "kayıt",                 "unit": "kayıt",    "label": "eğitim kurumu"},
    "guzellik":      {"service": "randevu",  "call": "işlem",                 "unit": "müşteri",  "label": "güzellik merkezi"},
    "emlak":         {"service": "müşteri",  "call": "ilan / danışmaya ulaşma", "unit": "portföy", "label": "emlak ofisi"},
    "kadin_dogum":   {"service": "hasta",    "call": "randevu",               "unit": "danışan",  "label": "klinik"},
    "restoran":      {"service": "müşteri",  "call": "rezervasyon",           "unit": "masa",     "label": "restoran"},
}

# Sabit short mesaj şablonu — Claude sadece {gozlem} boşluğunu dolduruyor
_SHORT_TEMPLATE = (
    "Merhaba {ad},\n"
    "{sehir}'deki {sektor_label} profillerine bakıyordum, sizinki dikkatimi çekti. "
    "{gozlem} "
    "İsterseniz kısa bir bakış atabilirim — yarın uygun olur musunuz?"
)

# Claude'a sadece gözlem cümlesini ürettiriyoruz
_GOZLEM_PROMPT = """Aşağıdaki audit verisinden sadece EN KRİTİK tek sorunu, sıcak ve doğal bir dille TEK CÜMLE olarak yaz.

KURALLAR:
- "fark ettim" veya "dikkatimi çekti" dili kullan
- Teknik terim YASAK: SSL, H1, meta, PageSpeed, UX, SEO, title tag
- Rakam, yüzde, "kayıp" ifadesi YASAK
- "Siteniz yok" yerine "dijital varlığınızın eksik olduğunu" gibi yumuşak dil kullan
- Sadece cümleyi yaz — başka hiçbir şey ekleme, tırnak işareti koyma

SEKTOR: {sektor} | MÜŞTERİ: {service}
KİLLER INSIGHT: {killer_bulgu}
EN ACITAN: {en_acitan}
KİŞİSEL GÖZLEM: {kisisel_insight}

ÖRNEK ÇIKTILAR (tarzı kopyala, içeriği değil):
- "Mobilde sitenizin yavaş açıldığını fark ettim — sizi arayan hastalar beklememek için başka bir kliniğe yönelebiliyor."
- "Google profilinizde web sitesi bağlantısı olmadığını gördüm — sizi arayan kişiler doğrudan ulaşamıyor olabilir."
- "Sitenizin telefon bağlantısının mobilde çalışmadığını fark ettim — bu durum potansiyel danışanların sizi aramasını zorlaştırıyor."

Sadece cümleyi yaz:"""

_FULL_PROMPT = """Teknik audit çıktısından FULL satış mesajı yaz.

ÖNEMLİ: Düzgün Türkçe karakterleri kullan (ş, ç, ğ, ü, ö, ı, İ).

YAPI (8-12 satır, sadece \\n ile ayır):
- Giriş: "[isim] için biraz daha detaylı baktım."
- Bölge/sektör talebi hakkında 1 cümle
- "Dikkatimi çeken 3 nokta:" + 3 madde (- ile)
- İçgörü cümlesi (kişisel gözlemden)
- "Bunlar genellikle hızlıca düzeltilebiliyor:" + 3 madde (- ile)
- CTA sorusu

TON: Samimi, yardımsever, satışçı değil.
YASAK: Teknik terim (SSL, H1, SEO, UX, PageSpeed), "ajans", "hizmet", "optimizasyon"
YASAK: "Siteniz yok, SSL yok" tarzı bombardıman — her madde ayrı ve yumuşak

SEKTÖRE ÖZGÜ DİL ({sektor}): {sektor_dil}
LEAD: {isim} | {adres}
KİLLER INSIGHT: {killer_bulgu} [{killer_rakam}]
EN ACITAN: {en_acitan}
KİŞİSEL GÖZLEM: {kisisel_insight}
UX SORUNLARI: {ux_hatalar}
DÖNÜŞÜM ENGELLERİ: {donusum_engelleri}

Sadece mesaj metnini döndür. Preamble yok, tırnak yok, açıklama yok."""


def _extract_first_name(full_name: str) -> str:
    """'Klinik Psikolog Başak AKÇA ARSLAN' → 'Başak', 'Op.Dr.Deva Ozdemir' → 'Deva'"""
    TITLE_WORDS = {
        "dr", "op", "prof", "uzm", "av", "mimar", "müh", "ing",
        "doktor", "uzman", "klinik", "psikolog", "avukat", "hemşire",
        "psk", "fzt", "dt", "spec", "uzman",
    }
    cleaned = re.sub(r"[.\-]", " ", full_name)
    parts = cleaned.strip().split()
    for part in parts:
        word = part.strip(".,").lower()
        if word in TITLE_WORDS:
            continue
        if part.isupper() and len(part) > 2:
            continue
        if len(part) < 2:
            continue
        return part[0].upper() + part[1:]
    return parts[0].title() if parts else full_name


def _sektor_dil_str(sector: str) -> str:
    dil = _SEKTOR_DIL.get(sector, {})
    if dil:
        return f"{dil['service']} / {dil['call']} / {dil['unit']}"
    return "müşteri / güven / karar"


def _sektor_label(sector: str) -> str:
    return _SEKTOR_DIL.get(sector, {}).get("label", sector)


def _sektor_service(sector: str) -> str:
    return _SEKTOR_DIL.get(sector, {}).get("service", "müşteri")


def _auto_trim_short(text: str) -> str:
    if len(text) <= 500:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sentences) <= 1:
        return text[:450]
    longest = max(range(len(sentences)), key=lambda i: len(sentences[i]))
    sentences.pop(longest)
    return " ".join(sentences)


def validate_sales_messages(output: dict) -> dict:
    issues = []
    short = output.get("short_message", "")
    full = output.get("full_message", "")

    if len(short) > 520:
        issues.append(f"short_message 520 karakterden uzun ({len(short)})")
    if _BLACKLIST.search(short):
        issues.append("short_message teknik kelime içeriyor")
    if not _CTA_SIGNALS.search(short):
        issues.append("short_message CTA içermiyor")
    if not short.lower().startswith("merhaba"):
        issues.append("short_message 'Merhaba' ile başlamıyor")

    lines = [l for l in full.splitlines() if l.strip()]
    word_count = len(full.split())
    if len(lines) < 5:
        issues.append(f"full_message 5 satırdan kısa ({len(lines)} satır)")
    if word_count > 350:
        issues.append(f"full_message 350 kelimeden uzun ({word_count} kelime)")
    bullet_count = len(re.findall(r"^\s*-\s+", full, re.MULTILINE))
    if bullet_count < 3:
        issues.append(f"full_message 3 madde içermiyor ({bullet_count} madde)")
    if _BLACKLIST.search(full):
        issues.append("full_message teknik kelime içeriyor")
    if "perşembe" not in full.lower() and "yarin" not in full.lower() and "yarın" not in full.lower():
        issues.append("full_message alternatif zaman CTA içermiyor")

    return {"valid": len(issues) == 0, "issues": issues}


async def generate_sales_output(lead: dict, audit: dict, playbook: dict) -> dict:
    sector = playbook.get("sektor", lead.get("sektor", "genel"))
    killer = audit.get("killer_insight") or {}
    ux = audit.get("ux_hatalar") or []
    donusum = audit.get("donusum_engelleri") or []

    isim = lead.get("isim") or ""
    adres = lead.get("adres") or ""
    city = adres.split("/")[0].strip() if "/" in adres else adres.split(",")[0].strip()

    ad = _extract_first_name(isim)

    if not settings.CLAUDE_API_KEY:
        raise RuntimeError("CLAUDE_API_KEY tanımlı değil")
    client = anthropic.AsyncAnthropic(api_key=settings.CLAUDE_API_KEY, timeout=30, max_retries=1)

    # ── 1. Gözlem cümlesini üret ──
    gozlem_prompt = _GOZLEM_PROMPT.format(
        sektor=sector,
        service=_sektor_service(sector),
        killer_bulgu=killer.get("bulgu", ""),
        en_acitan=audit.get("en_acitan_nokta", ""),
        kisisel_insight=audit.get("kisisel_insight", ""),
    )
    gozlem = ""
    try:
        msg = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=120,
            temperature=0,
            messages=[{"role": "user", "content": gozlem_prompt}],
        )
        gozlem = msg.content[0].text.strip().strip('"').strip("'")
        if gozlem and gozlem[-1] not in ".!?":
            gozlem += "."
    except Exception as e:
        logger.exception("Gözlem cümlesi üretilemedi: %s", e)
        gozlem = f"{killer.get('bulgu', 'Birkaç önemli nokta dikkatimi çekti')}."

    # ── 2. Short mesajı şablondan oluştur ──
    short = _SHORT_TEMPLATE.format(
        ad=ad,
        sehir=city or "Bölgenizdeki",
        sektor_label=_sektor_label(sector),
        gozlem=gozlem,
    )

    # ── 3. Full mesajı üret ──
    full_prompt = _FULL_PROMPT.format(
        sektor=sector,
        sektor_dil=_sektor_dil_str(sector),
        isim=isim,
        adres=adres,
        killer_bulgu=killer.get("bulgu", ""),
        killer_rakam=killer.get("rakam", ""),
        en_acitan=audit.get("en_acitan_nokta", ""),
        kisisel_insight=audit.get("kisisel_insight", ""),
        ux_hatalar="; ".join(h.get("sorun", "") for h in ux[:3]) or "(yok)",
        donusum_engelleri="; ".join(d.get("engel", "") for d in donusum[:2]) or "(yok)",
    )
    full = ""
    try:
        msg = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=600,
            temperature=0.1,
            messages=[{"role": "user", "content": full_prompt}],
        )
        full = msg.content[0].text.strip()
    except Exception as e:
        logger.exception("Full mesaj üretilemedi: %s", e)
        full = _fallback_full(isim, adres, killer, audit)

    output = {
        "short_message": short,
        "full_message": full,
        "meta": {"sector": sector, "tone": "samimi"},
    }

    validation = validate_sales_messages(output)
    output["_valid"] = validation["valid"]
    output["_issues"] = validation["issues"]

    if not validation["valid"]:
        logger.warning("Sales output issues: %s | lead=%s", validation["issues"], isim)

    return output


def _fallback_full(isim: str, adres: str, killer: dict, audit: dict) -> str:
    return (
        f"{isim} için biraz daha detaylı baktım.\n\n"
        f"{adres} bölgesinde ciddi bir talep var ama birkaç eksik yüzünden "
        f"bu talebin bir kısmı size gelmeden başka işletmelere gidiyor.\n\n"
        f"Dikkatimi çeken 3 nokta:\n"
        f"- {killer.get('bulgu', 'Dijital erişimde kritik bir eksik var')}\n"
        f"- Müşteri ile ilk temas zorlaşıyor\n"
        f"- Bölge aramalarında görünürlük eksik\n\n"
        f"{audit.get('en_acitan_nokta', 'Güçlü bir başlangıç noktanız var.')}\n\n"
        f"Bunlar genellikle hızlıca düzeltilebiliyor:\n"
        f"- Müşteri ile ilk teması kolaylaştırmak\n"
        f"- Güven unsurlarını ön plana taşımak\n"
        f"- Bölge odaklı erişimi güçlendirmek\n\n"
        f"İsterseniz bunu sizin örneğinizde kısa bir görüşmede gösterebilirim. "
        f"Yarın mı daha uygun olur, perşembe mi?"
    )
