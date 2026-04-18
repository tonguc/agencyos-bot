"""Merkezi Claude prompt şablonları. Tüm LLM çağrıları buradan import eder."""


AUDIT_PROMPT = """Sen gelir odakli bir buyume operatoru olarak calisiyorsun. Gorev: {display_name} sektorundeki bu isletmeyi analiz et ve dogrudan satis kapatabilen bir zeka raporu uret. Teknik rapor degil, isletme sahibinin canini yakan SOMUT bulgular.

===========================
SIKI KURALLAR
===========================

YASAK KELIMELER → bu kelimeleri kullanirsan yanit reddedilir:
{yasak_kelimeler}
Ayrica su jenerik kaliplar da yasak: "zayif gorunuyor", "gelistirilebilir", "iyilestirme firsati", "elenebilirsiniz", "kaydirabilir", "potansiyel var".

RAKAM ZORUNLULUGU:
- killer_insight.bulgu + etki + rakam: somut sayi icermeli (%X, N kisi/ay, N TL tahmini)
- en_acitan_nokta: mutlaka bir rakam icermeli
- kisisel_insight: isletme sahibinin "bunu nasil fark etti?" dedirtmeli, 1-2 cumle max

DERINLIK KURALLARI:
- ux_hatalar: en az 2, max 4 madde. siddet alani: "yuksek"/"orta"/"dusuk"
- seo_aciklar: en az 2 madde
- donusum_engelleri: en az 1 madde (CTA eksikligi, guven sinyali yoklugu vs.)
- hizli_kazanimlar: 2-3 madde, max 1 haftada uygulanabilir quick win

===========================
BU SEKTORDE ODAKLANILACAK KPI'LAR
===========================
{kpi_listesi}

===========================
SEKTORE OZGU DEGERLENDIR KRITERLERI (agirlikli — yuksek agirlik = daha kritik)
===========================
{audit_kriterleri}

===========================
ZORUNLU CIKTI FORMATI
===========================
{zorunlu_format}

KAYIP DILI — bulgulari bu cercevede yaz:
{kayip_dili}

===========================
SEKTORE OZGU TARZ ORNEKLERI (ICERIK DEGIL, TARZ KOPYALANACAK)
===========================
{killer_ornekleri}

===========================
LEAD VERISI
===========================
Isim: {isim}
Adres: {adres}
Yorum sayisi: {yorum_sayisi}  |  Puan: {puan}
Site URL: {url}
PageSpeed mobil skoru: {hiz_skoru}/100
Form var mi: {form_var}  |  Tel link: {tel_var}  |  SSL: {ssl}
Title: {title}
Meta: {meta}
H1: {h1}

===========================
CIKTI FORMATI — KESINLIKLE UYULACAK
===========================
ILK KARAKTER `{{` OLMALI. SON KARAKTER `}}` OLMALI.
Preamble, aciklama, markdown, kod blogu KESINLIKLE YASAK.
Sadece valid JSON don.

{{
  "ilk_izlenim": {{
    "ne_yapiyor": "3 saniyede anlasilan is tanimi",
    "deger_onerisi": "net|belirsiz|yok",
    "guven_seviyesi": "dusuk|orta|yuksek",
    "ilk_surtunum": "ziyaretcinin karsilastigi ilk engel, tek cumle"
  }},
  "killer_insight": {{
    "bulgu": "tek cumle, spesifik ariza",
    "etki": "tek cumle, sayisal kayip ifadesi",
    "rakam": "%X veya N birim"
  }},
  "ux_hatalar": [
    {{"sorun": "...", "etki": "...", "siddet": "yuksek|orta|dusuk", "cozum": "1 cumlelik quick win"}}
  ],
  "seo_aciklar": [
    {{"sorun": "...", "etki": "...", "cozum": "..."}}
  ],
  "donusum_engelleri": [
    {{"engel": "...", "kayip": "tahmini kayip ifadesi"}}
  ],
  "hizli_kazanimlar": ["max 1 haftada yapilabilir fix #1", "fix #2", "fix #3"],
  "reklam_firsati": {{
    "kanal": "Google Ads|Meta Ads|Google LSA",
    "aciklama": "...",
    "rakip_durum": "yok|var|aktif"
  }},
  "skorlar": {{"ux": 0, "seo": 0, "donusum": 0}},
  "urgency": "dusuk|orta|yuksek",
  "lead_kalitesi": "soguk|ilik|sicak",
  "genel_skor": 0,
  "en_acitan_nokta": "tek cumle, rakam icermeli",
  "kisisel_insight": "1-2 cumle, isletme sahibinin fark etmedigi somut gozlem"
}}
"""


DATA_HOOK_PROMPT = (
    "Hook sablon: {sablon}\n"
    "Bilgiler: ilce={ilce}, sektor={sektor}, rakip_durumu=aktif, aciklama={rakip_aciklama}.\n"
    "2 cumlede sablonu doldur. Rakam kullan (ornek: '3 rakip ads yapiyor'). "
    "Sadece hook metnini don, baska aciklama yazma."
)


GAP_HOOK_PROMPT = (
    "Hook sablon: {sablon}\n"
    "Bilgiler: ilce={ilce}, sektor={sektor}, somut_sorun={sorun}.\n"
    "2 cumlede sablonu doldur. Genel ifadelerden kacin ('zayif goruyor' yasak). "
    "Sadece hook metnini don."
)


OUTREACH_PROMPT = """Sen {display_name} sektorunde is gelistirme uzmanisin.

KANAL: {kanal}
TON: {ton}
KESIN YASAK ACILIS: {giris_yasak}
TERCIH EDILEN ACILIS: {giris_onerilen}
HOOK TIPI: {hook_tip}
LEAD KALITESI: {lead_kalitesi}
URGENCY: {urgency}

LEAD: {isim}
HOOK CUMLESI: {hook_cumlesi}
KILLER INSIGHT: {killer_bulgu}  [{killer_rakam}]
EN ACITAN NOKTA: {en_acitan}
KISISEL GOZLEM: {kisisel_insight}
ILCE/SEHIR: {adres}

KURALLAR:
- V1=MERAKLI: soru ile baslar, rakam icerir. Maks 6 satir.
- V2=DOGRUDAN: hook cumlesi ile baslar, 1 veri parcasi. Maks 6 satir.
- V3=NAZIK: ortak zemin + sorun + teklif. Maks 6 satir.
- V4=PROOF_BASED: benzer uzman gozleminden baslar
  ("Son donemde birkac {sektor} sitesine bakarken..." gibi).
  kisisel_gozlem'i dogal bir sekilde ic.
  killer_insight'tan 1 somut bulgu kullan.
  Behance portfoyunu MUTLAKA ekle: behance.net/tonguc
  CTA: "Isterseniz 2-3 somut madde paylasayim" veya "Kisa bir mini analiz gondereyim".
  Maks 5 satir.
  V4 ICIN EK YASAK: "yardimci olabiliriz", "hizmet sunuyoruz", "cozum uretiyoruz", "ajansimiz".

ORTAK KURALLAR:
- Her versiyonda killer insight bir kez gecmeli
- V1/V2/V3: 15 dk gorusme VEYA somut acik uclu soru ile bitmeli
- Hicbir versiyon jenerik kaliplarla bitmemeli

CIKTI:
ILK KARAKTER `{{`, SON KARAKTER `}}`. Preamble/markdown YASAK.
{{"v1": "...", "v2": "...", "v3": "...", "v4": "...", "onerilen": "{varsayilan_onerilen}"}}
"""


FOLLOWUP_PROMPT_DAY3 = (
    "Takip mesaji (3 gun sonrasi). Kanal={kanal}. Ton={ton}.\n"
    "Onceki mesaj: {onceki}\n"
    "Lead: {isim}.\n"
    "Kurallar: farkli bir aciyi vurgula, 1 ek veri/rakam ekle, "
    "acik uclu bir soru ile bitir. Maks 4 satir. Sadece mesaj metnini don."
)

FOLLOWUP_PROMPT_LAST = (
    "Son takip mesaji. Kanal={kanal}. Ton={ton}.\n"
    "Onceki mesaj: {onceki}\n"
    "Lead: {isim}.\n"
    "Kurallar: kibar cikis + 'dosyayi kapatayim mi?' tarzi soru. "
    "Baski yok. Maks 3 satir. Sadece mesaj metnini don."
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
