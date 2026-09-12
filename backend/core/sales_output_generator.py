"""
Sales Output Generator — teknik audit'i müşteri satış mesajlarına çevirir.
SHORT = direkt gönderilir | FULL = follow-up / detay için kullanılır.
"""

import logging
import re

from core.sales_policy import SALES_POLICY

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
    "Merhaba,\n"
    "{isim} için internetteki bilgileri incelerken bir nokta dikkatimi çekti. "
    "{gozlem} "
    "İsterseniz bununla ilgili kısa bir öneri paylaşabilirim. Uygun olur mu?"
)

# Claude'a sadece gözlem cümlesini ürettiriyoruz
_GOZLEM_PROMPT = """Aşağıdaki audit verisinden sadece EN KRİTİK tek sorunu, sıcak ve doğal bir dille TEK CÜMLE olarak yaz.

KURALLAR:
- "fark ettim" veya "dikkatimi çekti" dili kullan
- Teknik terim YASAK: SSL, H1, meta, PageSpeed, UX, SEO, title tag
- Rakam, yüzde, "kayıp" ifadesi YASAK
- Yalnızca doğrulanan gözlemi söyle; belirsiz "dijital varlığınız eksik" ifadeleri kullanma.
- Hastaların ulaşamadığını, rakibe gittiğini veya gelir kaybedildiğini kanıt olmadan söyleme.
- Sadece cümleyi yaz — başka hiçbir şey ekleme, tırnak işareti koyma

SEKTOR: {sektor} | MÜŞTERİ: {service}
KİLLER INSIGHT: {killer_bulgu}
EN ACITAN: {en_acitan}
KİŞİSEL GÖZLEM: {kisisel_insight}

ÖRNEK ÇIKTILAR (tarzı kopyala, içeriği değil):
- "İncelediğim kayıtta web sitesi bağlantınızı bulamadım; kullandığınız bir site var mı?"
- "Sitenizin telefon bağlantısının mobilde çalışmadığını fark ettim — bu durum potansiyel danışanların sizi aramasını zorlaştırıyor."

Sadece cümleyi yaz:"""

_FULL_PROMPT = """Teknik audit çıktısından FULL satış mesajı yaz.

ÖNEMLİ: Düzgün Türkçe karakterleri kullan (ş, ç, ğ, ü, ö, ı, İ).

YAPI (8-12 satır, sadece \\n ile ayır):
- Giriş: "[isim] için biraz daha detaylı baktım."
- Yalnızca eldeki kanıtları anlat; bölge talebi veya müşteri kaybı uydurma.
- Kanıtlanan bulguları yaz; üç madde doldurmak için sorun üretme.
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
    return _SEKTOR_DIL.get(sector, {}).get("label", "işletme")


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
    if word_count > 350:
        issues.append(f"full_message 350 kelimeden uzun ({word_count} kelime)")
    bullet_count = len(re.findall(r"^\s*-\s+", full, re.MULTILINE))
    if _BLACKLIST.search(full):
        issues.append("full_message teknik kelime içeriyor")
    if not _CTA_SIGNALS.search(full):
        issues.append("full_message CTA içermiyor")

    return {"valid": len(issues) == 0, "issues": issues}


async def generate_sales_output(lead: dict, audit: dict, playbook: dict) -> dict:
    sector = lead.get("sektor", "genel")
    sector_label = _sektor_label(sector)
    killer = audit.get("killer_insight") or {}
    ux = audit.get("ux_hatalar") or []
    donusum = audit.get("donusum_engelleri") or []

    isim = lead.get("isim") or ""
    adres = lead.get("adres") or ""
    # Business names and addresses do not reliably identify a person or city.
    isim = isim.split(",", 1)[0].strip() or "İşletmeniz"

    if not lead.get("website"):
        short = (
            f"Merhaba, {isim} için incelediğim kayıtta web sitesi bağlantısını bulamadım. "
            "Kullandığınız bir web sitesi var mı? Yoksa, isterseniz işletmenizi tanıtan ve iletişim "
            "bilgilerinizi bir arada sunan; Google ve yapay zekâ destekli aramalarda keşfedilmenizi destekleyecek bir site için kısa bir öneri paylaşabilirim."
        )
        full = (
            f"Merhaba,\n{isim} için incelediğim kayıtta web sitesi bağlantısını bulamadım.\n"
            "Kullandığınız bir site varsa bağlantısını paylaşabilir misiniz?\n"
            "Yoksa, hizmetlerinizi açıkça anlatan, Google ve yapay zekâ destekli aramalarda keşfedilmeyi destekleyen ve iletişime geçmeyi kolaylaştıran bir site düşünülebilir.\n"
            "İsterseniz nasıl bir sayfa olabileceğine dair kısa bir öneri paylaşabilirim."
        )
        validation = validate_sales_messages({"short_message": short, "full_message": full})
        return {"short_message": short, "full_message": full,
                "meta": {"sector": sector, "tone": "samimi"},
                "_valid": validation["valid"], "_issues": validation["issues"]}

    if not settings.CLAUDE_API_KEY:
        raise RuntimeError("CLAUDE_API_KEY tanımlı değil")
    client = anthropic.AsyncAnthropic(api_key=settings.CLAUDE_API_KEY, timeout=30, max_retries=1)

    # ── 1. Gözlem cümlesini üret ──
    gozlem_prompt = SALES_POLICY + _GOZLEM_PROMPT.format(
        sektor=sector_label,
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
            extra_body={"temperature": 0},
            messages=[{"role": "user", "content": gozlem_prompt}],
        )
        gozlem = msg.content[0].text.strip().strip('"').strip("'")
        if gozlem and gozlem[-1] not in ".!?":
            gozlem += "."
    except Exception as e:
        logger.exception("Gözlem cümlesi üretilemedi: %s", e)
        gozlem = "Bunu doğrulamak için siteyi birlikte değerlendirebiliriz."

    # ── 2. Short mesajı şablondan oluştur ──
    short = _SHORT_TEMPLATE.format(
        isim=isim,
        gozlem=gozlem,
    )

    # ── 3. Full mesajı üret ──
    full_prompt = SALES_POLICY + _FULL_PROMPT.format(
        sektor=sector_label,
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
            extra_body={"temperature": 0.1},
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
        f"Merhaba, {isim} için site incelemesini tamamlayamadım.\n"
        "Doğrulamadan bir sorun veya müşteri kaybı iddia etmek istemem.\n"
        "İsterseniz siteyi inceleyip doğrulayabildiğim noktaları kısa bir notla paylaşabilirim."
    )
