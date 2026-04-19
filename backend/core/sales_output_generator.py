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
    "restoran":      {"service": "müşteri",  "call": "rezervasyon",           "unit": "masa"},
}

_PROMPT = """Teknik audit ciktisini IKI FARKLI satis mesajina ve 3 alternatif giris cumlesine cevir.

=== TON (KESINLIKLE UYULACAK) ===
- Kisa ve keskin cumle (7-12 kelime). Uzun paragraflar yasak.
- Aktif ses. Pasif kip yasak. ("goruldu", "tespit edildi" → yasak)
- Ingilizce terim yok. SEO/UX/PageSpeed/meta/H1 asla yazma.
- Ozguven var, baski yok. Bulguyu paylas, ittirme.
- Her cumle somut gozlem icermeli — genel kalip yasak.
- Muhatabi "siz/sizi/sizin" diye hitap et (samimi ama saygin).

=== SHORT MESSAGE (WhatsApp/SMS) ===
- Tam 3 cumle. Fazlasi yasak.
- 280-380 karakter.

CUMLE 1 — OLUMLU GIRIS (zorunlu):
  Isim ile BASLAMAZ. Somut bir guc noktasi ile baslar.
  Kullan: puan, yorum sayisi, konum avantaji, kisisel_insight'tan gozlem.
  Ornek: "404 yorumunuz Beylikduzu'nde guclu bir itibar kaniti —"
  Ornek: "Ege mutfagi aramasinda cogu rakibin ustune cikacak bir konumunuz var —"
  YASAK: "kisa bir analiz yaptim", "{isim} —", "size ulasiyorum"

CUMLE 2 — SPESIFIK SORUN (tek, somut):
  Killer insight veya en acitan noktadan. Rakam varsa ic.
  Ornek: "ama teras araması yapan musteri sizi bulamadan rakibe gidiyor (%65 terk)."
  YASAK: listeleme (birden fazla sorun), teknik terim

CUMLE 3 — CTA (soru formunda, secenekli):
  Her zaman soru ile biter. Alternatif zaman teklifi.
  Ornek: "10 dakikada somut olarak gosterebilirim — yarin mi uygun, persembe mi?"
  YASAK: "isterseniz", "yardimci olabilirim", noktayla bitmek

=== FULL MESSAGE (e-posta / detaylı WhatsApp) ===
AMAÇ: "Ben para kaybediyorum" hissi — bilgi vermek değil, aksiyona itmek.
Her paragraf şu soruya hizmet etmeli: "Bu kişi neden hemen konuşmak ister?"

YAPI (bu 6 blok, bu sırada, başka şey ekleme):

BLOK 1 — GİRİŞ (1-2 cümle):
  Olumlu gözlemle başla (puan/yorum/konum). Ismi kullanma.
  YASAK: "biraz daha detaylı baktım", "analiz yaptım", "size ulaşıyorum"

BLOK 2 — TALEP VAR AMA SIZE GELMİYOR (1-2 cümle):
  Sektördeki talebi somutlaştır. Müşterinin sizi nasıl aradığını yaz.
  Sonra o talebin rakibe gittiğini belirt.

BLOK 3 — 3 KRİTİK NOKTA (maksimum 3 madde, - ile):
  Her madde PARA DİLİNDE olacak:
  YASAK: "rezervasyon linki yok"
  KULLAN: "rezervasyon yapmak isteyen müşteriler masaya dönüşmeden çıkıyor"
  Mümkünse rakam ekle: "ayda tahminen 60-80 rezervasyon kaybı" gibi.
  Her madde FARKLI açıdan, tekrar yok.

BLOK 4 — EN GÜÇLÜ INSIGHT (1-2 cümle):
  kisisel_insight veya killer_bulgu'dan. Para kaybını hissettir, dramatize etme.
  Mini proof ekle: "Benzer bir {sektor}da [tek değişiklik] ile [somut sonuç] gördük."
  Proof kısa, satış kokmasın, güven versin.

BLOK 5 — ÇÖZÜM ÇERÇEVESİ (3 madde max, - ile):
  "Bu genelde 3 adımda toparlanıyor:" → her madde 1 satır, teknik terim yok.

BLOK 6 — CTA (son, sabit format):
  "Bunu 10–15 dakikada net şekilde gösterebilirim. Yarın mı daha uygun olur, perşembe mi?"
  CTA kelimesi kelimesine bu format. Değiştirme.

KISITLAMALAR:
- Max 250-300 kelime. Daha uzun olursa kes.
- Sadece \\n satır ayırıcı. Başlık, emoji, markdown yasak.
- SEO/UX/PageSpeed/H1/meta/optimize yasak.
- Aynı insight 1 kez geçer. Tekrar = sil.
- Ton: deneyimli danışman. Ne çok resmi, ne çok samimi.

=== ACILIS ALTERNATIFLERI ===
- 3 farkli giris cumlesi. Her biri max 1 cumle.
- V1: somut rakam ile baslar (puan veya tahmini kisi sayisi)
- V2: bolge/arama davranisi ile baslar
- V3: karsilastirma/tespitle baslar ("Son donemde birka {sektor} baktigimda...")
- Hicbiri "size ulasiyorum", "gorunurluk" veya teknik terim icermemeli.

=== SEKTORE OZGU DIL ({sektor}): {sektor_dil} ===

LEAD: {isim} | {adres} | Sektor: {sektor}

AUDIT OZETI:
Killer bulgu: {killer_bulgu} [{killer_rakam}]
En acitan nokta: {en_acitan}
Kisisel gozlem: {kisisel_insight}
UX sorunlari: {ux_hatalar}
Donusum engelleri: {donusum_engelleri}
Lead kalitesi: {lead_kalitesi} | Urgency: {urgency}

DONUSTURMELER (teknik → satis dili):
"Form yok" → "{service} sizi aramadan cikabiliyor"
"Hiz dusuk" → "site yavas acilinca {service} gitmis oluyor"
"Tel link yok" → "sizi aramak isteyen bir tiklama fazla yapmak zorunda"
"Yorumlar yok" → "Maps'teki guven sitede kayboluyor"
"Web sitesi yok" → "Google Maps disinda sizi bulamiyorlar"

CIKTI: Sadece valid JSON. Preamble yok, markdown yok, kod blogu yok. Ilk karakter {{ olmali.
{{
  "short_message": "3 cumle. 300-400 karakter. Direkt gonderilebilir.",
  "full_message": "Cok satirli metin. Sadece \\n satirlari. Baslik/emoji yok.",
  "acilis_alternatifleri": ["rakam ile", "bolge/arama ile", "karsilastirma ile"],
  "meta": {{"sector": "{sektor}", "tone": "keskin-ozguveli"}}
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

    top = sector.split("_")[0] if "_" in sector else sector
    dil = _SEKTOR_DIL.get(sector) or _SEKTOR_DIL.get(top) or {}

    return _PROMPT.format(
        sektor=sector,
        sektor_dil=_sektor_dil_str(sector),
        service=dil.get("service", "müşteri"),
        call=dil.get("call", "iletişim"),
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
    """450 karakter aşıyorsa en uzun cümleyi çıkar."""
    if len(text) <= 450:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sentences) <= 1:
        return text[:450]
    longest = max(range(len(sentences)), key=lambda i: len(sentences[i]))
    sentences.pop(longest)
    return " ".join(sentences)


def validate_sales_messages(output: dict) -> dict:
    """
    Returns {'valid': bool, 'issues': list[str]}

    SHORT: ≤3 cümle, 300-400 karakter, teknik kelime yok, CTA var
    FULL: ≥6 satır, ≥3 madde (-), CTA var
    """
    issues = []
    short = output.get("short_message", "")
    full = output.get("full_message", "")

    sentence_count = len(re.split(r"(?<=[.!?])\s+", short.strip()))
    if sentence_count > 3:
        issues.append(f"short_message 3 cümleden fazla ({sentence_count} cümle)")
    if len(short) > 450:
        issues.append(f"short_message 450 karakterden uzun ({len(short)})")
    if _BLACKLIST.search(short):
        issues.append("short_message teknik kelime içeriyor")
    if not _CTA_SIGNALS.search(short):
        issues.append("short_message CTA içermiyor")

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
                max_tokens=1500,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-z]*\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
            output = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(
                "Sales output JSON parse failed (attempt %s) lead=%s: %s | raw=%r",
                attempt + 1, lead.get("isim", "?"), e, (raw if "raw" in dir() else "")[:200],
            )
            if attempt == 1:
                output = _fallback_output(lead, audit)
                break
            continue
        except Exception as e:
            logger.exception("Sales output generation failed (attempt %s) lead=%s: %s",
                             attempt + 1, lead.get("isim", "?"), e)
            output = _fallback_output(lead, audit)
            break

        if output.get("short_message") and len(output["short_message"]) > 450:
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
    adres = (lead.get("adres") or "").split(",")[0].strip() or "bölgenizde"
    bulgu = killer.get("bulgu") or "birkaç kritik nokta dikkatimi çekti"
    rakam = killer.get("rakam", "")
    en_acitan = audit.get("en_acitan_nokta", "")

    rakam_str = f" ({rakam})" if rakam else ""
    short = (
        f"{isim} — {bulgu}{rakam_str}. "
        f"Sizi arayan müşteri bu noktada rakibe gidiyor. "
        f"10 dakikada somut olarak gösterebilirim — yarın mı uygun olur?"
    )

    full = (
        f"{adres.split(',')[0].strip()} bölgesinde bu sektörde ciddi bir arama hacmi var.\n\n"
        f"Ama {bulgu.lower() if bulgu else 'birkaç kritik nokta'} — "
        f"sizi arayan müşteri son adımda başka bir yere gidiyor.\n\n"
        f"3 kritik nokta:\n"
        f"- {bulgu or 'Dijital temas noktası eksik'} — müşteri masaya dönüşmeden çıkıyor\n"
        f"- {en_acitan or 'Karar anında rakip önde bitiriyor'}\n"
        f"- Bölge aramasında görünürlük boşluğu — talep size ulaşmadan kayıyor\n\n"
        f"Bu genelde 3 adımda toparlanıyor:\n"
        f"- İlk temas anını kolaylaştırmak\n"
        f"- Güven sinyallerini öne çıkarmak\n"
        f"- Doğru kanalda görünür olmak\n\n"
        f"Bunu 10–15 dakikada net şekilde gösterebilirim. "
        f"Yarın mı daha uygun olur, perşembe mi?"
    )

    return {
        "short_message": short,
        "full_message": full,
        "meta": {"sector": lead.get("sektor", "genel"), "tone": "direkt"},
    }
