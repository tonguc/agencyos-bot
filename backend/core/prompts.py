"""Merkezi Claude prompt şablonları. Tüm LLM çağrıları buradan import eder."""


AUDIT_PROMPT = """Sen gelir odaklı bir büyüme operatörü olarak çalışıyorsun. Görev: {display_name} sektöründeki bu işletmeyi analiz et ve doğrudan satış kapatabilen bir zeka raporu üret. Teknik rapor değil, işletme sahibinin canını yakan SOMUT bulgular.

ÖNEMLİ: Tüm metin çıktılarında düzgün Türkçe karakterleri kullan (ş, ç, ğ, ü, ö, ı, İ, Ş, Ç, Ğ, Ü, Ö).

===========================
SIKI KURALLAR
===========================

YASAK KELİMELER → bu kelimeleri kullanırsan yanıt reddedilir:
{yasak_kelimeler}
Ayrıca şu jenerik kalıplar da yasak: "zayıf görünüyor", "geliştirilebilir", "iyileştirme fırsatı", "elenebilirsiniz", "kaydırabilir", "potansiyel var".

FORM VE İLETİŞİM KURALLARI:
- form_var=False ama tel_var=True ise: "iletişim formu yok" bulgusunu DÜŞÜK öncelikli tut veya hiç yazma.
  Ev hizmetleri ve klinik sektörlerde telefon tek/ana kanal olabilir — bu kendi başına kritik bir sorun değil.
- form_var=True ise: "iletişim formu yok" bulgusunu kesinlikle YAZMA.

H1 VE BÖLGE HEDEFLEME KURALLARI:
- Sitede H1 + title + meta birlikte değerlendir. Aralarında en az bir bölge adı varsa "bölgede H1 yok" yazma.
- "Esenyurt için ayrı H1 yok" gibi bulgular YASAK: bu ayrı landing page ister, quick win değildir.
- H1 sorununu sadece şu durumda flag'le: H1 + title + meta hiçbirinde hiçbir bölge/şehir adı YOKSA.
- Meta description farklı şehirler içeriyorsa bu yeterlidir; H1'in de hepsini içermesi gerekmez.

RAKAM ZORUNLULUĞU:
- killer_insight.bulgu + etki + rakam: somut sayı içermeli (%X, N kişi/ay, N TL tahmini)
- en_acitan_nokta: mutlaka bir rakam içermeli
- kisisel_insight: işletme sahibinin "bunu nasıl fark etti?" dedirtmeli, 1-2 cümle max

DERİNLİK KURALLARI:
- ux_hatalar: en az 2, max 4 madde. şiddet alanı: "yuksek"/"orta"/"dusuk"
- seo_aciklar: en az 2 madde
- donusum_engelleri: en az 1 madde (CTA eksikliği, güven sinyali yokluğu vs.)
- hizli_kazanimlar: 2-3 madde, max 1 haftada uygulanabilir quick win

===========================
BU SEKTÖRDE ODAKLANILACAK KPI'LAR
===========================
{kpi_listesi}

===========================
SEKTÖRE ÖZGÜ DEĞERLENDİR KRİTERLERİ (ağırlıklı — yüksek ağırlık = daha kritik)
===========================
{audit_kriterleri}

===========================
ZORUNLU ÇIKTI FORMATI
===========================
{zorunlu_format}

KAYIP DİLİ — bulguları bu çerçevede yaz:
{kayip_dili}

===========================
SEKTÖRE ÖZGÜ TARZ ÖRNEKLERİ (İÇERİK DEĞİL, TARZ KOPYALANACAK)
===========================
{killer_ornekleri}

===========================
LEAD VERİSİ
===========================
İsim: {isim}
Adres: {adres}
Yorum sayısı: {yorum_sayisi}  |  Puan: {puan}
Site URL: {url}
PageSpeed mobil skoru: {hiz_skoru}/100
Form var mı: {form_var}  |  Tel link: {tel_var}  |  SSL: {ssl}
Title: {title}
Meta: {meta}
H1: {h1}

===========================
ÇIKTI FORMATI — KESİNLİKLE UYULACAK
===========================
İLK KARAKTER `{{` OLMALI. SON KARAKTER `}}` OLMALI.
Preamble, açıklama, markdown, kod bloğu KESİNLİKLE YASAK.
Sadece valid JSON dön.

{{
  "ilk_izlenim": {{
    "ne_yapiyor": "3 saniyede anlaşılan iş tanımı",
    "deger_onerisi": "net|belirsiz|yok",
    "guven_seviyesi": "dusuk|orta|yuksek",
    "ilk_surtunum": "ziyaretçinin karşılaştığı ilk engel, tek cümle"
  }},
  "killer_insight": {{
    "bulgu": "tek cümle, spesifik arıza",
    "etki": "tek cümle, sayısal kayıp ifadesi",
    "rakam": "%X veya N birim"
  }},
  "ux_hatalar": [
    {{"sorun": "...", "etki": "...", "siddet": "yuksek|orta|dusuk", "cozum": "1 cümlelik quick win"}}
  ],
  "seo_aciklar": [
    {{"sorun": "...", "etki": "...", "cozum": "..."}}
  ],
  "donusum_engelleri": [
    {{"engel": "...", "kayip": "tahmini kayıp ifadesi"}}
  ],
  "hizli_kazanimlar": ["max 1 haftada yapılabilir fix #1", "fix #2", "fix #3"],
  "reklam_firsati": {{
    "kanal": "Google Ads|Meta Ads|Google LSA",
    "aciklama": "...",
    "rakip_durum": "yok|var|aktif"
  }},
  "skorlar": {{"ux": 0, "seo": 0, "donusum": 0}},
  "urgency": "dusuk|orta|yuksek",
  "lead_kalitesi": "soguk|ilik|sicak",
  "genel_skor": 0,
  "en_acitan_nokta": "tek cümle, rakam içermeli",
  "kisisel_insight": "1-2 cümle, işletme sahibinin fark etmediği somut gözlem"
}}
"""


DATA_HOOK_PROMPT = (
    "Hook şablon: {sablon}\n"
    "Bilgiler: ilçe={ilce}, sektör={sektor}, rakip_durumu=aktif, açıklama={rakip_aciklama}.\n"
    "2 cümlede şablonu doldur. Rakam kullan (örnek: '3 rakip ads yapıyor'). "
    "Sadece hook metnini dön, başka açıklama yazma."
)


GAP_HOOK_PROMPT = (
    "Hook şablon: {sablon}\n"
    "Bilgiler: ilçe={ilce}, sektör={sektor}, somut_sorun={sorun}.\n"
    "2 cümlede şablonu doldur. Genel ifadelerden kaçın ('zayıf görünüyor' yasak). "
    "Sadece hook metnini dön."
)


OUTREACH_PROMPT = """Sen {display_name} sektöründe iş geliştirme uzmanısın.

ÖNEMLİ: Tüm metin çıktılarında düzgün Türkçe karakterleri kullan (ş, ç, ğ, ü, ö, ı, İ).

KANAL: {kanal}
TON: {ton}
KESİN YASAK AÇILIŞ: {giris_yasak}
TERCİH EDİLEN AÇILIŞ: {giris_onerilen}
HOOK TİPİ: {hook_tip}
LEAD KALİTESİ: {lead_kalitesi}
URGENCY: {urgency}

LEAD: {isim}
HOOK CÜMLESİ: {hook_cumlesi}
KİLLER INSIGHT: {killer_bulgu}  [{killer_rakam}]
EN ACITAN NOKTA: {en_acitan}
KİŞİSEL GÖZLEM: {kisisel_insight}
İLÇE/ŞEHİR: {adres}

KURALLAR:
- V1=MERAKLI: soru ile başlar, rakam içerir. Maks 6 satır.
- V2=DOĞRUDAN: hook cümlesi ile başlar, 1 veri parçası. Maks 6 satır.
- V3=NAZİK: ortak zemin + sorun + teklif. Maks 6 satır.
- V4=PROOF_BASED: benzer uzman gözleminden başlar
  ("Son dönemde birkaç {sektor} sitesine bakarken..." gibi).
  kisisel_gozlem'i doğal bir şekilde iç.
  killer_insight'tan 1 somut bulgu kullan.
  Behance portföyünü MUTLAKA ekle: behance.net/tonguc
  CTA: "İsterseniz 2-3 somut madde paylaşayım" veya "Kısa bir mini analiz göndereyim".
  Maks 5 satır.
  V4 İÇİN EK YASAK: "yardımcı olabiliriz", "hizmet sunuyoruz", "çözüm üretiyoruz", "ajansımız".

ORTAK KURALLAR:
- Her versiyonda killer insight bir kez geçmeli
- V1/V2/V3: 15 dk görüşme VEYA somut açık uçlu soru ile bitmeli
- Hiçbir versiyon jenerik kalıplarla bitmemeli

ÇIKTI:
İLK KARAKTER `{{`, SON KARAKTER `}}`. Preamble/markdown YASAK.
{{"v1": "...", "v2": "...", "v3": "...", "v4": "...", "onerilen": "{varsayilan_onerilen}"}}
"""


FOLLOWUP_PROMPT_DAY3 = (
    "Takip mesajı (3 gün sonrası). Kanal={kanal}. Ton={ton}.\n"
    "Önceki mesaj: {onceki}\n"
    "Lead: {isim}.\n"
    "Kurallar: farklı bir acıyı vurgula, 1 ek veri/rakam ekle, "
    "açık uçlu bir soru ile bitir. Maks 4 satır. Sadece mesaj metnini dön."
)

FOLLOWUP_PROMPT_LAST = (
    "Son takip mesajı. Kanal={kanal}. Ton={ton}.\n"
    "Önceki mesaj: {onceki}\n"
    "Lead: {isim}.\n"
    "Kurallar: kibar çıkış + 'dosyayı kapatayım mı?' tarzı soru. "
    "Baskı yok. Maks 3 satır. Sadece mesaj metnini dön."
)


def build_audit_prompt(lead: dict, playbook: dict, site: dict) -> str:
    dil = playbook.get("audit_dil_kurallari", {})

    kriteler = playbook.get("audit_kriterleri", [])
    audit_kriterleri_str = "\n".join(
        f"- [Agirlik {k['agirlik']}] {k['soru']}"
        for k in kriteler
    ) or "(genel kriterler gecerli)"

    kpi_str = ", ".join(playbook.get("kpi_listesi", [])) or "(genel)"

    return AUDIT_PROMPT.format(
        display_name=playbook["display_name"],
        yasak_kelimeler=", ".join(dil.get("yasak", [])) or "(yok)",
        kpi_listesi=kpi_str,
        audit_kriterleri=audit_kriterleri_str,
        zorunlu_format=dil.get("zorunlu_format", "Sorun → Kayip etkisi → Kisa cozum"),
        kayip_dili=dil.get("kayip_dili", "musteri kaybi"),
        killer_ornekleri="\n".join(f"- {x}" for x in playbook.get("killer_insight_ornekleri", [])),
        isim=lead.get("isim") or "",
        adres=lead.get("adres") or "",
        yorum_sayisi=lead.get("yorum_sayisi", 0),
        puan=lead.get("puan", 0),
        url=site.get("url") or "(yok)",
        hiz_skoru=site.get("hiz_skoru", 0),
        form_var=site.get("form_var", False),
        tel_var=site.get("tel_var", False),
        ssl=site.get("ssl", False),
        title=(site.get("title") or "")[:120],
        meta=(site.get("meta") or "")[:200],
        h1=(site.get("h1") or "")[:120],
    )


def build_data_hook_prompt(lead: dict, audit: dict, playbook: dict, ilce: str) -> str:
    return DATA_HOOK_PROMPT.format(
        sablon=playbook["hook_tipleri"]["data_hook"]["sablon"],
        ilce=ilce,
        sektor=playbook["sektor"],
        rakip_aciklama=audit.get("reklam_firsati", {}).get("aciklama", ""),
    )


def build_gap_hook_prompt(lead: dict, audit: dict, playbook: dict, ilce: str) -> str:
    seo = (audit.get("seo_aciklar") or [{}])[0].get("sorun", "gorunurluk sorunu")
    return GAP_HOOK_PROMPT.format(
        sablon=playbook["hook_tipleri"]["gap_hook"]["sablon"],
        ilce=ilce,
        sektor=playbook["sektor"],
        sorun=seo,
    )


def build_outreach_prompt(lead: dict, audit: dict, hook: dict, playbook: dict, varsayilan_onerilen: str) -> str:
    out = playbook["outreach"]
    killer = audit.get("killer_insight", {}) or {}
    return OUTREACH_PROMPT.format(
        display_name=playbook["display_name"],
        kanal=out["kanal"],
        ton=out["ton"],
        giris_yasak=out["giris_yasak"],
        giris_onerilen=out["giris_onerilen"],
        hook_tip=hook["tip"],
        lead_kalitesi=audit.get("lead_kalitesi", "ilik"),
        urgency=audit.get("urgency", "orta"),
        isim=lead.get("isim") or "",
        adres=lead.get("adres") or "",
        sektor=playbook.get("sektor", ""),
        hook_cumlesi=hook["hook"],
        killer_bulgu=killer.get("bulgu", ""),
        killer_rakam=killer.get("rakam", ""),
        en_acitan=audit.get("en_acitan_nokta", ""),
        kisisel_insight=audit.get("kisisel_insight", ""),
        varsayilan_onerilen=varsayilan_onerilen,
    )


def build_followup_prompt(lead: dict, gun: int, onceki: str, playbook: dict) -> str:
    out = playbook["outreach"]
    tmpl = FOLLOWUP_PROMPT_DAY3 if gun <= 3 else FOLLOWUP_PROMPT_LAST
    return tmpl.format(
        kanal=out["kanal"],
        ton=out["ton"],
        onceki=(onceki or "")[:400],
        isim=lead.get("isim") or "",
    )


# ---------------------------------------------------------------------------
# Full Sales Funnel prompts
# ---------------------------------------------------------------------------

INITIAL_MESSAGE_PROMPT = """Sen {display_name} sektorunde is gelistirme uzmanisin.
Kural: ajans dili yasak. Her cumle somut gozlem icerecek.

LEAD: {isim} | {adres}
KANAL: {kanal}
KILLER INSIGHT: {killer_bulgu} [{killer_rakam}]
KISISEL GOZLEM: {kisisel_insight}
HOOK: {hook_cumlesi}

FORMAT (kesinlikle 4 cumle):
1. Kisisel giris — neden bu kişiye yazildigi hissettirmeli
2. Spesifik gozlem — killer insight veya kisisel_insight'tan
3. Kayip/firsat — somut ifade, rakam varsa kullan
4. Dusuk surtuenmeli CTA — "isterseniz 2-3 madde paylasayim" tarzinda

YASAK: "ajansim var", "hizmet sunuyorum", "size ulasiyorum", jenerik kalip.
Sadece mesaj metnini don. Preamble, markdown, tirnak isareti kullanma."""


REPLY_RESPONSE_PROMPT = """Lead bir mesaja cevap verdi. Niyete gore kisa, kisisel yanit uret.

LEAD: {isim}
NIYET: {intent}
KILLER INSIGHT: {killer_bulgu}
EN ACITAN NOKTA: {en_acitan}

NIYET KURALLARI:
- positive  → direk gorusmeye cek, 10-15 dk teklifi, zaman sor. Maks 2 cumle.
- curious   → kisaca acikla + somut ornek ver + gorusme teklif et. Maks 3 cumle.
- price     → fiyati verme; once bulgulari gormek daha dogru oldugunu soylen,
              neden her isletmede farkli oldugunu 1 cumleyle acikla. Maks 2 cumle.

YASAK: "yardimci olabilirim", "hizmet sunuyoruz", uzun paragraflar.
Sadece yanit metnini don."""


CLOSE_PROMPT = """Gorusmeye cekmeyi hedefleyen kisa bir kapanis mesaji yaz.

LEAD: {isim}

KURALLAR:
- Maksimum 2 cumle
- Net ve dusuk surtuenmeli
- Alternatifli zaman teklifi kullan (ornek: "yarin mi, persembe mi?")
- Baski yok, dogal ton
Sadece mesaj metnini don."""


def build_initial_message_prompt(lead: dict, audit: dict, hook: dict, playbook: dict) -> str:
    out = playbook["outreach"]
    killer = audit.get("killer_insight") or {}
    return INITIAL_MESSAGE_PROMPT.format(
        display_name=playbook["display_name"],
        isim=lead.get("isim") or "",
        adres=lead.get("adres") or "",
        kanal=out["kanal"],
        killer_bulgu=killer.get("bulgu", ""),
        killer_rakam=killer.get("rakam", ""),
        kisisel_insight=audit.get("kisisel_insight", ""),
        hook_cumlesi=hook.get("hook", ""),
    )


def build_reply_response_prompt(intent: str, lead: dict, audit: dict) -> str:
    killer = audit.get("killer_insight") or {}
    return REPLY_RESPONSE_PROMPT.format(
        isim=lead.get("isim") or "",
        intent=intent,
        killer_bulgu=killer.get("bulgu", ""),
        en_acitan=audit.get("en_acitan_nokta", ""),
    )


def build_close_prompt(lead: dict) -> str:
    return CLOSE_PROMPT.format(isim=lead.get("isim") or "")
