"""Merkezi Claude prompt şablonları. Tüm LLM çağrıları buradan import eder."""


AUDIT_PROMPT = """Sen {display_name} sektorunde kidemli bir buyume danismanisin. Gorev: teknik rapor DEGIL, isletme sahibinin canini yakan bulgular bulmak.

===========================
SIKI KURALLAR (UYMAZSAN YANIT REDDEDILIR)
===========================

1) KILLER_INSIGHT ZORUNLU KURALLARI:
   - bulgu: spesifik bir arizadan bahsetmeli (neyin bozuk/eksik)
   - etki: musteri/hasta/is kaybinin SAYISAL ifadesi (%X, N kisi/ay, N TL)
   - rakam: yalniz rakam + birim (ornek: "%70", "15 hasta/ay", "3-5 is/hafta")
   - bulgu + etki birlestiginde "Sorun -> Kayip -> Cozum" akisini saglamali

2) YASAK KELIMELER (kullanmak yanit iptali):
   {yasak_kelimeler}
   Jenerik ifadelerden kacin: "zayif gorunuyor", "geliştirilebilir", "iyilestirme firsati", "elenebilirsiniz", "kaydirabilir".

3) EN_ACITAN_NOKTA:
   - TEK CUMLE
   - Bir rakam icermek ZORUNDA
   - Isletme sahibinin "sikt-, gercekten kayip yasiyorum" dedirtmeli

4) UX_HATALAR ve SEO_ACIKLAR:
   - En az 1 UX ve 1 SEO bulgusu
   - Her biri: sorun (somut), etki (sayisal), cozum (1 cumlelik quick win)

===========================
SEKTORE OZGU ORNEKLER (TARZ KOPYALANACAK, ICERIK DEGIL)
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
CIKTI FORMATI
===========================
ILK KARAKTER `{{` OLMALI. SON KARAKTER `}}` OLMALI.
Preamble, aciklama, markdown, kod blogu YASAK.
Sadece valid JSON don, baska hicbir sey yazma.

Sema (alan isimleri aynen kullanilacak):
{{
  "killer_insight": {{"bulgu": "tek cumle, rakamli", "etki": "tek cumle, rakamli", "rakam": "%X veya N birim"}},
  "ux_hatalar": [{{"sorun": "...", "etki": "...", "cozum": "..."}}],
  "seo_aciklar": [{{"sorun": "...", "etki": "...", "cozum": "..."}}],
  "reklam_firsati": {{"kanal": "Google Ads", "aciklama": "...", "rakip_durum": "yok|var|aktif"}},
  "genel_skor": 45,
  "en_acitan_nokta": "tek cumle, rakam icermeli"
}}

ux_hatalar ve seo_aciklar EN AZ 1 madde icermeli.
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

LEAD: {isim}
HOOK CUMLESI: {hook_cumlesi}
KILLER INSIGHT: {killer_bulgu}
KILLER RAKAMI: {killer_rakam}
EN ACITAN NOKTA: {en_acitan}

KURALLAR:
- V1=MERAKLI: soru ile baslar, rakam icerir. Maks 6 satir.
- V2=DOGRUDAN: hook cumlesi ile baslar, 1 veri parcasi. Maks 6 satir.
- V3=NAZIK: ortak zemin + sorun + teklif. Maks 6 satir.
- V4=PROOF_BASED: benzer klinik/uzman gozleminden baslar
  ("Son donemde birkac klinik sitesine bakarken..." gibi).
  "Sizde de benzer bir durum olabilir" tarzi yumusak gecis yap.
  Audit'ten gelen 1 somut bulgu kullan (killer insight veya rakam).
  Behance portfoyunu MUTLAKA ekle: behance.net/tonguc
  CTA: "Isterseniz 2-3 somut madde paylasayim"
       veya "Kisa bir mini analiz gondereyim".
  Maks 5 satir.
  V4 ICIN EK YASAK: "yardimci olabiliriz", "hizmet sunuyoruz",
                    "cozum uretiyoruz", "ajansimiz".

ORTAK KURALLAR:
- Her versiyonda killer insight bir kez gecmeli
- V1/V2/V3: 15 dk gorusme VEYA somut acik uclu soru ile bitmeli
- Hicbir versiyon "zayif gorunuyor" / "elenebilirsiniz" gibi jenerik kaliplarla bitmemeli

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
    return AUDIT_PROMPT.format(
        display_name=playbook["display_name"],
        yasak_kelimeler=dil.get("yasak", []),
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
        isim=lead.get("isim") or "",
        hook_cumlesi=hook["hook"],
        killer_bulgu=killer.get("bulgu", ""),
        killer_rakam=killer.get("rakam", ""),
        en_acitan=audit.get("en_acitan_nokta", ""),
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
