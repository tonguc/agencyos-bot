"""
Lead Scorer — 4-boyutlu scoring pipeline.

  Hard Filter        → elenenler (anlamsız lead'ler)
  Opportunity  (0-100) → problemin büyüklüğü (biz ne kadar fark yaratabiliriz?)
  Buyer Intent (0-100) → alıcı şimdi satın alır mı? (aktiflik, reklam baskısı)
  Fit          (0-100) → ICP uyumu (boyut, erişilebilirlik, canlılık)
  Pattern Boost        → çoklu sinyal kombinasyonları (IG aktif + booking yok gibi)

final = 0.50·opportunity + 0.30·intent + 0.20·fit + pattern_boost   (0-100 cap)

Segmentler: HOT (≥75) | WARM (≥55) | LOW (<55)

lead["score_breakdown"] → sıralı string listesi (ör. "+12 IG aktif + booking yok")
lead["score_layers"]   → debugger için eski katmanlı dict (maps/audit/conversion…)
lead["signals"]        → her boyutun tam sinyal listesi (audit için)

Tüm sinyal ağırlıkları playbook["feature_weights"] üzerinden gelir.
weight = 0.0 → sinyal tamamen kapalı
weight < 1.0 → etki azaltılmış
weight = 1.0 → tam etki
weight > 1.0 → sektörde ekstra kritik sinyal
"""

import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)

CHANNEL_FIELDS = [
    "instagram_post_90d", "instagram_last_post_days",
    "youtube_video_180d", "youtube_last_video_days",
    "linkedin_url", "linkedin_active_30d", "linkedin_followers",
    "market_ads_pressure", "competitor_ads_count", "self_ads_visible",
    "gmb_photo_count", "gmb_last_photo_days", "gmb_has_description", "gmb_has_qa",
    "has_cta", "has_whatsapp", "has_online_booking",
    "has_blog", "last_blog_days",
    "has_service_pages", "has_faq", "has_about_depth",
    # Clinic aesthetic signals
    "has_before_after", "has_visual_gallery",
    # Clinic trust signals
    "has_doctor_profile",
    # Lawyer signals
    "has_legal_articles", "has_practice_areas", "has_case_examples",
    "has_contact_clear", "has_linkedin_profile",
    # Real estate signals
    "has_property_listings", "listing_count", "has_price_info",
    "has_photos_quality", "has_video_tour", "has_location_info", "has_call_button",
    # Beauty signals
    "has_visual_quality", "has_service_list", "has_instagram_link",
    # Education signals
    "has_course_details", "has_curriculum", "has_success_stories",
    "has_testimonials", "has_free_content", "has_video_content",
    "has_clear_pricing", "has_cta_clear",
    # Review velocity
    "review_last_30d", "review_last_90d",
    # Update detection
    "last_website_update_days", "website_update_confidence",
]

DEFAULT_FEATURE_WEIGHTS = {
    "blog_signal": 1.0,
    "content_depth_signal": 1.0,
    "linkedin_signal": 1.0,
    "youtube_signal": 1.0,
    "instagram_signal": 1.0,
    "online_booking_signal": 1.0,
    "ads_signal": 1.0,
    "trust_signal": 1.0,
}

SEGMENT_TO_PRIORITY = {
    "HOT": "yuksek",
    "WARM": "orta",
    "LOW": "dusuk",
}


def _fw(playbook: dict) -> dict:
    """Playbook'tan feature_weights oku, eksikleri default ile doldur."""
    w = DEFAULT_FEATURE_WEIGHTS.copy()
    w.update(playbook.get("feature_weights", {}))
    return {k: float(v) for k, v in w.items()}


# --------------------------------------------------
# 1. HARD FILTER
# --------------------------------------------------

def hard_filter(lead: dict, playbook: dict) -> Tuple[bool, str]:
    """
    Return:
    (True, reason) → ELENDİ
    (False, "")    → DEVAM
    """
    isim = (lead.get("isim") or "").lower()
    yorum = lead.get("yorum_sayisi") or 0
    telefon = lead.get("telefon")
    son_yorum = lead.get("son_yorum_gun")

    if any(x in isim for x in ["hastane", "devlet", "group", "merkez"]):
        return True, "kurumsal / zincir"

    puan = lead.get("puan") or 0
    website = lead.get("website")
    if yorum > 150 and puan > 4.5 and website:
        return True, "zaten güçlü"

    if not telefon:
        return True, "telefon yok"

    if son_yorum is not None and son_yorum > 365:
        return True, "ölü profil"

    return False, ""


# --------------------------------------------------
# 2. OPPORTUNITY SCORE (0–100)
# --------------------------------------------------

def calc_opportunity(lead: dict, audit: dict, playbook: dict) -> tuple[int, list[str]]:
    """Returns (score, signals). Each signal entry: 'Label → +N'."""
    score = 40
    signals: list[str] = []
    fw = _fw(playbook)
    sub = lead.get("clinic_subsector")

    def add(delta: int, label: str) -> None:
        nonlocal score
        score += delta
        if delta != 0:
            signals.append(f"{label} → {'+' if delta > 0 else ''}{delta}")

    # ── Google Maps / Temel veriler ──────────────────
    yorum = lead.get("yorum_sayisi") or 0
    puan = lead.get("puan") or 0
    website = lead.get("website")
    site_durumu = lead.get("site_durumu")

    # yorum <10 = az (opportunity); yorum 10-100 = uygun boyut → fit'te sayılır
    if yorum < 10:
        add(15, f"Yorum az ({yorum})")
    elif yorum > 100:
        add(-8, f"Yorum çok ({yorum})")

    if 3.8 <= puan <= 4.1:
        add(10, f"Puan orta ({puan})")
    elif puan < 3.8:
        add(5, f"Puan düşük ({puan})")
    elif puan > 4.6:
        add(-10, f"Puan yüksek ({puan})")

    if not website:
        add(20, "Website yok")
    elif site_durumu == "zayif":
        add(10, "Site zayıf")
    elif site_durumu == "iyi":
        add(-5, "Site iyi")

    # ── Audit verileri ───────────────────────────────
    audit_skor = audit.get("genel_skor", 50)
    pagespeed = audit.get("pagespeed", 60)
    ssl = audit.get("ssl", True)

    if audit_skor < 35:
        add(15, f"Audit çok zayıf ({audit_skor})")
    elif audit_skor < 55:
        add(8, f"Audit zayıf ({audit_skor})")
    elif audit_skor > 75:
        add(-10, f"Audit güçlü ({audit_skor})")

    if pagespeed < 40:
        add(10, f"PageSpeed çok yavaş ({pagespeed})")
    elif pagespeed < 60:
        add(5, f"PageSpeed yavaş ({pagespeed})")
    elif pagespeed > 85:
        add(-5, f"PageSpeed hızlı ({pagespeed})")

    if not ssl:
        add(8, "SSL yok")

    # ── Google Ads pressure ──────────────────────────
    ads_w = fw["ads_signal"]
    ads_pressure = lead.get("market_ads_pressure")
    competitor_ads_count = lead.get("competitor_ads_count")
    self_ads_visible = lead.get("self_ads_visible")

    if ads_w > 0:
        if ads_pressure is True:
            add(round(4 * ads_w), "Ads pressure var")
        if competitor_ads_count is not None:
            if competitor_ads_count >= 3:
                add(round(4 * ads_w), f"Rakip reklam: {competitor_ads_count}")
            elif competitor_ads_count >= 1:
                add(round(2 * ads_w), f"Rakip reklam: {competitor_ads_count}")
        if ads_pressure is True and self_ads_visible is False:
            add(round(4 * ads_w), "Rakip var, self yok → açık")
        elif self_ads_visible is True:
            add(-3, "Self ads görünüyor")

    # ── GMB derinliği ────────────────────────────────
    photo_count = lead.get("gmb_photo_count")
    last_photo = lead.get("gmb_last_photo_days")

    if photo_count is not None:
        if photo_count < 5:
            add(6, f"GMB fotoğraf az ({photo_count})")
        elif photo_count < 15:
            add(3, f"GMB fotoğraf orta ({photo_count})")
    if last_photo is not None and last_photo > 90:
        add(4, f"GMB son fotoğraf eski ({last_photo}g)")
    if lead.get("gmb_has_description") is False:
        add(4, "GMB açıklama yok")
    if lead.get("gmb_has_qa") is False:
        add(3, "GMB Q&A yok")

    # ── Website conversion gap (sadece website varsa) ─
    if website:
        if lead.get("has_cta") is False:
            add(8, "CTA yok")
        if lead.get("has_whatsapp") is False:
            add(5, "WhatsApp yok")

        booking_w = fw["online_booking_signal"]
        if booking_w > 0 and lead.get("has_online_booking") is False:
            add(round(10 * booking_w), "Online booking yok")

        blog_w = fw["blog_signal"]
        if blog_w > 0:
            if lead.get("has_blog") is False:
                add(round(6 * blog_w), "Blog yok")
            elif lead.get("last_blog_days") is not None and lead["last_blog_days"] > 120:
                add(round(8 * blog_w), f"Blog eski ({lead['last_blog_days']}g)")

        cd_w = fw["content_depth_signal"]
        if cd_w > 0:
            if lead.get("has_service_pages") is False:
                add(round(5 * cd_w), "Servis sayfası yok")
            if lead.get("has_faq") is False:
                add(round(3 * cd_w), "SSS yok")
            if lead.get("has_about_depth") is False:
                add(round(4 * cd_w), "Hakkında derinliği yok")

    # ── Website güncellik ────────────────────────────
    update_days = lead.get("last_website_update_days")
    update_conf = lead.get("website_update_confidence") or 0.0
    if update_days is not None and update_conf >= 0.3 and update_days > 180:
        add(4, f"Site eski ({update_days}g, conf={update_conf:.1f})")

    # ── Clinic subsector sinyalleri ──────────────────
    if sub == "aesthetic":
        # Görsel içerik eksikliği estetik hastası için deal-breaker
        if lead.get("has_before_after") is False:
            add(10, "Before/after yok (estetik)")
        if lead.get("has_visual_gallery") is False:
            add(5, "Görsel galeri yok (estetik)")

    elif sub == "trust":
        # Otorite içeriği eksikliği güven kırıcı
        trust_w = fw.get("trust_signal", 1.0)
        if trust_w > 0 and lead.get("has_doctor_profile") is False:
            add(round(8 * trust_w), "Doktor profili yok (güven)")

    # "general" için mevcut GMB + pagespeed sinyalleri yeterli

    # ── Lawyer subsector sinyalleri ──────────────────
    sub_sector = lead.get("sub_sector")

    if sub_sector == "litigation":
        if lead.get("has_legal_articles") is False:
            add(8, "Hukuki içerik yok (dava)")
        if lead.get("has_practice_areas") is False:
            add(6, "Uzmanlık alanları yok (dava)")
        if lead.get("has_case_examples") is False:
            add(6, "Dava örnekleri yok (dava)")
        if lead.get("has_contact_clear") is False:
            add(6, "İletişim belirsiz (dava)")

    elif sub_sector == "corporate":
        if lead.get("has_linkedin_profile") is False:
            add(8, "LinkedIn profil yok (kurumsal)")
        if lead.get("has_practice_areas") is False:
            add(6, "Uzmanlık alanları yok (kurumsal)")
        if lead.get("has_contact_clear") is False:
            add(6, "İletişim belirsiz (kurumsal)")

    # ── Real estate subsector sinyalleri ─────────────
    elif sub_sector == "luxury":
        if lead.get("has_video_tour") is False:
            add(8, "Video tur yok (lüks emlak)")
        if lead.get("has_photos_quality") is False:
            add(8, "Profesyonel fotoğraf yok (lüks emlak)")
        if lead.get("has_property_listings") is False:
            add(10, "Online ilan yok (lüks emlak)")
        if lead.get("has_price_info") is False:
            add(6, "Fiyat bilgisi yok (lüks emlak)")

    elif sub_sector == "local":
        if lead.get("has_property_listings") is False:
            add(10, "Online ilan yok (yerel emlak)")
        # listing_count: sadece ilanlar var ama az ise (0 ise zaten üstte +10 aldı)
        listing_count = lead.get("listing_count")
        if listing_count is not None and 0 < listing_count < 5:
            add(6, f"İlan az ({listing_count} adet)")
        if lead.get("has_location_info") is False:
            add(5, "Bölge bilgisi yok (yerel emlak)")
        # has_call_button: has_whatsapp'tan bağımsız yeni sinyal
        if lead.get("has_call_button") is False:
            add(5, "Arama butonu yok (yerel emlak)")

    # ── Beauty subsector sinyalleri ──────────────────
    elif sub_sector == "aesthetic":
        # Öncesi/sonrası: klinikte de kullanılan sinyal, güzellik için de geçerli
        if lead.get("has_before_after") is False:
            add(10, "Before/after yok (estetik güzellik)")
        if lead.get("has_visual_quality") is False:
            add(8, "Görsel kalite düşük (estetik güzellik)")
        if lead.get("has_price_info") is False:
            add(6, "Fiyat bilgisi yok (estetik güzellik)")
        # has_online_booking generic bloğu zaten hallediyor (online_booking_signal:1.0)

    elif sub_sector == "routine":
        if lead.get("has_service_list") is False:
            add(6, "Hizmet listesi yok (rutin güzellik)")
        if lead.get("has_price_info") is False:
            add(5, "Fiyat bilgisi yok (rutin güzellik)")
        # has_whatsapp generic conversion bloğunda zaten +5 veriyor — tekrar etme

    # ── Ev hizmetleri subsector sinyalleri ──────────────
    elif sub_sector in ("tesisat", "elektrik"):
        if lead.get("has_call_button") is False:
            add(10, f"Arama butonu yok ({sub_sector})")
        if lead.get("has_location_info") is False:
            add(5, f"Hizmet bölgesi belirsiz ({sub_sector})")

    elif sub_sector == "tadilat":
        if lead.get("has_before_after") is False:
            add(10, "Öncesi-sonrası fotoğraf yok (tadilat)")
        if lead.get("has_visual_gallery") is False:
            add(6, "Proje galerisi yok (tadilat)")
        if lead.get("has_cta_clear") is False:
            add(6, "Keşif CTA'sı yok (tadilat)")

    # ── Education subsector sinyalleri ───────────────
    elif sub_sector == "course":
        if lead.get("has_course_details") is False:
            add(8, "Kurs detay sayfası yok (kurs)")
        if lead.get("has_curriculum") is False:
            add(8, "Müfredat yok (kurs)")
        if lead.get("has_success_stories") is False:
            add(6, "Başarı hikayesi yok (kurs)")
        if lead.get("has_clear_pricing") is False:
            add(6, "Net fiyat yok (kurs)")
        if lead.get("has_cta_clear") is False:
            add(6, "CTA belirsiz (kurs)")

    elif sub_sector == "coaching":
        if lead.get("has_testimonials") is False:
            add(8, "Müşteri yorumu yok (koçluk)")
        if lead.get("has_video_content") is False:
            add(6, "Video içerik yok (koçluk)")
        if lead.get("has_free_content") is False:
            add(6, "Ücretsiz içerik yok (koçluk)")
        if lead.get("has_cta_clear") is False:
            add(6, "CTA belirsiz (koçluk)")

    return max(0, min(score, 100)), signals


# --------------------------------------------------
# 3. BUYER INTENT SCORE (0–100)
# --------------------------------------------------

def calc_buyer_intent(lead: dict, audit: dict, playbook: dict) -> tuple[int, list[str]]:
    """Returns (score, signals)."""
    score = 50
    signals: list[str] = []
    fw = _fw(playbook)
    sub = lead.get("clinic_subsector")

    def add(delta: int, label: str) -> None:
        nonlocal score
        score += delta
        if delta != 0:
            signals.append(f"{label} → {'+' if delta > 0 else ''}{delta}")

    # ── Google Maps aktivitesi ───────────────────────
    son_yorum = lead.get("son_yorum_gun")
    if son_yorum is not None:
        if son_yorum < 30:
            add(15, f"Son yorum yakın ({son_yorum}g)")
        elif son_yorum < 90:
            add(8, f"Son yorum orta ({son_yorum}g)")
        elif son_yorum > 180:
            add(-15, f"Son yorum eski ({son_yorum}g)")

    # ── Rakip reklam sinyali (audit) ─────────────────
    rakip = audit.get("reklam_firsati", {}).get("rakip_durum", "")
    if rakip == "aktif":
        add(10, "Rakip reklam aktif")

    # ── Instagram ────────────────────────────────────
    ig_w = fw["instagram_signal"]
    post_90 = lead.get("instagram_post_90d")
    last_post_days = lead.get("instagram_last_post_days")

    if ig_w > 0 and post_90 is not None:
        if post_90 == 0:
            add(round(-6 * ig_w), f"Instagram 90g post: {post_90}")
        elif post_90 <= 3:
            add(round(-2 * ig_w), f"Instagram 90g post: {post_90}")
        elif post_90 <= 10:
            add(round(4 * ig_w), f"Instagram 90g post: {post_90}")
        else:
            add(round(6 * ig_w), f"Instagram 90g post: {post_90}")

    if ig_w > 0 and last_post_days is not None:
        if last_post_days < 14:
            add(round(4 * ig_w), f"Instagram son post: {last_post_days}g")
        elif last_post_days < 60:
            add(round(2 * ig_w), f"Instagram son post: {last_post_days}g")
        elif last_post_days > 60:
            add(round(-4 * ig_w), f"Instagram son post: {last_post_days}g")

    # ── YouTube ──────────────────────────────────────
    yt_w = fw["youtube_signal"]
    yt_180 = lead.get("youtube_video_180d")
    yt_last_days = lead.get("youtube_last_video_days")

    if yt_w > 0 and yt_180 is not None:
        if yt_180 == 0:
            pass  # yoksa ceza yok
        elif yt_180 <= 2:
            add(round(1 * yt_w), f"YouTube 180g video: {yt_180}")
        elif yt_180 <= 6:
            add(round(3 * yt_w), f"YouTube 180g video: {yt_180}")
        else:
            add(round(4 * yt_w), f"YouTube 180g video: {yt_180}")

    if yt_w > 0 and yt_last_days is not None:
        if yt_last_days < 30:
            add(round(2 * yt_w), f"YouTube son video: {yt_last_days}g")
        elif yt_last_days < 90:
            add(round(1 * yt_w), f"YouTube son video: {yt_last_days}g")

    # ── LinkedIn ─────────────────────────────────────
    li_w = fw["linkedin_signal"]
    if li_w > 0:
        if lead.get("linkedin_active_30d") is True:
            add(round(10 * li_w), "LinkedIn aktif (30g)")
        elif lead.get("linkedin_url"):
            add(round(2 * li_w), "LinkedIn profil var")

    # ── Review velocity ──────────────────────────────
    rev_30 = lead.get("review_last_30d")
    rev_90 = lead.get("review_last_90d")

    if rev_30 is not None:
        if rev_30 >= 5:
            add(12, f"Son 30g yorum: {rev_30}")
        elif rev_30 >= 2:
            add(6, f"Son 30g yorum: {rev_30}")
    if rev_90 is not None and rev_90 >= 10:
        add(8, f"Son 90g yorum: {rev_90}")

    # ── Clinic subsector intent sinyalleri ───────────
    if sub == "aesthetic":
        # Estetik hasta Instagram'dan karar veriyor — düşük aktiflik = düşük intent
        ig_followers = lead.get("instagram_followers")
        if ig_followers is not None and ig_followers < 500:
            add(-5, f"Instagram takipçi az ({ig_followers}, estetik)")

    elif sub == "trust":
        # Güven segmenti için son yorum puanı extra kritik
        puan = lead.get("puan") or 0
        if 3.0 <= puan < 3.8:
            add(8, f"Puan kritik aralık ({puan}, güven segmenti)")

    # ── Lawyer subsector intent sinyalleri ───────────
    sub_sector = lead.get("sub_sector")
    if sub_sector in ("litigation", "corporate"):
        li_w = fw["linkedin_signal"]
        # has_linkedin_profile boolean flag (avukat için ek kontrol)
        if lead.get("has_linkedin_profile") is True and not lead.get("linkedin_url"):
            add(round(4 * li_w), "LinkedIn profil var (avukat)")
        elif lead.get("has_linkedin_profile") is False and not lead.get("linkedin_url"):
            add(round(-4 * li_w), "LinkedIn yok (avukat)")
        # Review velocity extra boost for lawyers (danışman güveni için kritik)
        if rev_30 is not None and 3 <= rev_30 < 5:
            add(2, f"Avukat yorum hız bonusu ({rev_30}/30g)")

    # ── Real estate subsector intent sinyalleri ──────
    # Instagram sinyali feature_weights ile generic bloğa zaten giriyor.
    # Burada sadece emlak'a özgü EK sinyaller: aktif ilan varlığı ve iletişim.
    if sub_sector in ("luxury", "local"):
        if lead.get("has_property_listings") is True:
            add(5, "Online ilan mevcut")

    # ── Beauty subsector intent sinyalleri ───────────
    # instagram_post_90d ve review_last_30d generic scorer'da zaten var.
    # Burada sadece güzelliğe özgü EK sinyal: Instagram linki dönüşüm yolunu açar.
    elif sub_sector in ("aesthetic", "routine"):
        ig_w = fw["instagram_signal"]
        # Instagram profil linki sitede varsa dönüşüm kanalı açık demek
        if ig_w > 0 and lead.get("has_instagram_link") is True:
            add(round(3 * ig_w), "Instagram linki mevcut (güzellik)")
        elif ig_w > 0 and lead.get("has_instagram_link") is False:
            add(round(-3 * ig_w), "Instagram linki yok (güzellik)")

    # ── Ev hizmetleri subsector intent sinyalleri ────
    # Review velocity ev hizmetlerinde karar verme sürecinin tamamı.
    # Generic rev_30 bloğuna ek: yüksek hız ekstra boost alır.
    elif sub_sector in ("tesisat", "elektrik", "tadilat"):
        if rev_30 is not None and rev_30 >= 5:
            add(6, f"Aktif yorum hızı ({sub_sector})")
        if lead.get("has_call_button") is True:
            add(5, f"Arama butonu var ({sub_sector})")

    # ── Education subsector intent sinyalleri ────────
    # instagram/youtube/review generic scorer'da feature_weights ile hallediliyor.
    # Burada sadece eğitime özgü EK sinyal: ücretsiz içerik lead magnet olarak çalışır.
    elif sub_sector in ("course", "coaching"):
        li_w = fw["linkedin_signal"]
        # Koçluk için LinkedIn aktifliği doğrudan müşteri niyeti göstergesi
        if sub_sector == "coaching" and li_w > 0:
            if lead.get("linkedin_active_30d") is True and not lead.get("linkedin_url"):
                add(round(5 * li_w), "LinkedIn aktif (koçluk)")
        # Ücretsiz içerik varsa → lead sıcak, dönüşme ihtimali yüksek
        if lead.get("has_free_content") is True:
            add(5, "Ücretsiz içerik mevcut (eğitim)")

    return max(0, min(score, 100)), signals


# --------------------------------------------------
# 4. FIT SCORE (0–100)
# --------------------------------------------------

def calc_fit(lead: dict, audit: dict, playbook: dict) -> tuple[int, list[str]]:
    """
    ICP erişilebilirlik ve boyut uyumu.
    Sinyal sahipliği (opportunity/intent ile örtüşme yok):
      telefon       → sadece burada (intent'ten kaldırıldı)
      yorum 10-100  → sadece burada (opportunity <10 ve >100 ile aralık örtüşmez)
      oncelikli_ilce→ sadece burada (intent'ten taşındı)
    """
    score = 30
    signals: list[str] = []

    def add(delta: int, label: str) -> None:
        nonlocal score
        score += delta
        if delta != 0:
            signals.append(f"{label} → {'+' if delta > 0 else ''}{delta}")

    if lead.get("telefon"):
        add(20, "Telefon erişilebilir")

    yorum = lead.get("yorum_sayisi") or 0
    if 10 <= yorum <= 100:
        add(15, f"Yorum hacmi uygun ({yorum})")

    if lead.get("oncelikli_ilce"):
        add(15, "Öncelikli ilçe")

    return max(0, min(score, 100)), signals


# --------------------------------------------------
# 5. PATTERN BOOSTS
# --------------------------------------------------

def calc_pattern_boosts(lead: dict, audit: dict, playbook: dict) -> tuple[int, list[str]]:
    """
    Çoklu sinyal kombinasyonları. Tek başına orta olan sinyaller,
    birlikte geldiğinde "bu kesin satılır" göstergesine döner.
    Return (toplam_boost, sinyal_listesi) — her sinyal "+N label" formatında.
    """
    total = 0
    signals: list[str] = []

    def fire(delta: int, label: str) -> None:
        nonlocal total
        total += delta
        signals.append(f"{'+' if delta > 0 else ''}{delta} {label}")

    website = lead.get("website")
    site_durumu = lead.get("site_durumu")
    telefon = lead.get("telefon")
    yorum = lead.get("yorum_sayisi") or 0
    puan = lead.get("puan") or 0

    ig_post_90 = lead.get("instagram_post_90d")
    has_booking = lead.get("has_online_booking")
    has_cta = lead.get("has_cta")
    rev_30 = lead.get("review_last_30d")
    competitor_ads = lead.get("competitor_ads_count")
    self_ads = lead.get("self_ads_visible")

    # IG aktif + booking kanalı yok → para hazır, yakalama aracı yok
    if ig_post_90 is not None and ig_post_90 > 5 and has_booking is False:
        fire(12, "IG aktif + booking kanalı yok")

    # Maps güçlü + site zayıf/yok → organik trafik var, dönüşüm kırık
    if yorum > 20 and puan >= 4.0 and (not website or site_durumu == "zayif"):
        fire(10, "Maps güçlü ama site zayıf")

    # Telefon var + website yok → acil dijital varlık ihtiyacı
    if telefon and not website:
        fire(6, "Telefon var ama website yok")

    # Taze yorum akışı + CTA yok → trafik var, CTA eksikliği kayıp
    if rev_30 is not None and rev_30 >= 3 and has_cta is False:
        fire(8, "Taze yorum var ama CTA yok")

    # Rakip reklam basıyor + kendisi basmıyor → açık pazar
    if competitor_ads is not None and competitor_ads >= 2 and self_ads is False:
        fire(8, "Rakip reklam basıyor, kendisi yok")

    total = min(total, 20)  # max +20 boost — birden fazla pattern baskıyı önler
    return total, signals


# --------------------------------------------------
# 6. FINAL SCORE
# --------------------------------------------------

_SIGNAL_DELTA_RE = re.compile(r"→\s*([+-]?\d+)\s*$")


def _parse_delta(signal: str) -> tuple[int, str]:
    """'Yorum az (3) → +15' → (15, 'Yorum az (3)'). Unknown → (0, signal)."""
    m = _SIGNAL_DELTA_RE.search(signal)
    if not m:
        return 0, signal.strip()
    try:
        delta = int(m.group(1))
    except ValueError:
        return 0, signal.strip()
    label = signal[: m.start()].rstrip(" →").strip()
    return delta, label


def _build_breakdown_list(
    opp_signals: list[str],
    intent_signals: list[str],
    fit_signals: list[str],
    boost_signals: list[str],
    limit: int = 12,
) -> list[str]:
    """
    Tüm sinyalleri 'signed N label' formatında tek listeye düzleştir.
    Mutlak değere göre sırala, en etkili limit kadar sinyali döndür.
    Pattern boost sinyalleri zaten doğru formatta (ör. '+12 IG aktif...').
    """
    items: list[tuple[int, str]] = []

    for s in opp_signals + intent_signals + fit_signals:
        delta, label = _parse_delta(s)
        if delta == 0 or not label:
            continue
        items.append((delta, f"{'+' if delta > 0 else ''}{delta} {label}"))

    for s in boost_signals:
        m = re.match(r"\s*([+-]?\d+)\s+(.+)", s)
        if not m:
            continue
        try:
            delta = int(m.group(1))
        except ValueError:
            continue
        items.append((delta, f"{'+' if delta > 0 else ''}{delta} {m.group(2).strip()}"))

    items.sort(key=lambda x: -abs(x[0]))
    return [label for _, label in items[:limit]]


def _build_score_layers(
    opp_signals: list[str],
    intent_signals: list[str],
    fit_signals: list[str],
    boost_sum: int,
) -> dict:
    """Debugger için eski katmanlı dict — score_debugger.py bunu okuyor."""

    def _sum(signals: list[str], keywords: list[str]) -> float:
        total = 0.0
        for s in signals:
            if any(k in s for k in keywords):
                delta, _ = _parse_delta(s)
                total += delta
        return total

    return {
        "maps":       _sum(opp_signals, ["Yorum", "Puan", "GMB"]),
        "audit":      _sum(opp_signals, ["Audit", "PageSpeed", "SSL"]),
        "conversion": _sum(opp_signals, ["CTA", "WhatsApp", "booking", "Blog", "Website yok", "Site", "Servis", "SSS", "Hakkında", "Before", "Görsel", "Doktor"]),
        "ads":        _sum(opp_signals, ["Ads", "Rakip reklam", "Self ads"]),
        "social":     _sum(intent_signals, ["Instagram", "YouTube", "LinkedIn"]),
        "intent":     _sum(intent_signals, ["yorum", "Rakip reklam aktif"]),
        "fit":        float(sum(_parse_delta(s)[0] for s in fit_signals)),
        "boost":      float(boost_sum),
    }


def calculate_final_score(lead: dict, audit: dict, playbook: dict) -> dict:
    """Full scoring pipeline. audit can be {} at scrape time."""
    is_blocked, reason = hard_filter(lead, playbook)
    if is_blocked:
        return {"status": "rejected", "reason": reason}

    opportunity, opp_signals = calc_opportunity(lead, audit, playbook)
    intent, intent_signals = calc_buyer_intent(lead, audit, playbook)
    fit, fit_signals = calc_fit(lead, audit, playbook)
    boost_sum, boost_signals = calc_pattern_boosts(lead, audit, playbook)

    weighted = (opportunity * 0.50) + (intent * 0.30) + (fit * 0.20)
    final = round(max(0.0, min(100.0, weighted + boost_sum)), 1)

    if final >= 80:
        segment = "HOT"
    elif final >= 60:
        segment = "WARM"
    else:
        segment = "LOW"

    fw = _fw(playbook)
    active_weights = {k: v for k, v in fw.items() if v != 1.0}

    score_breakdown = _build_breakdown_list(opp_signals, intent_signals, fit_signals, boost_signals)
    score_layers = _build_score_layers(opp_signals, intent_signals, fit_signals, boost_sum)

    result = {
        "status": "ok",
        "opportunity": opportunity,
        "buyer_intent": intent,
        "fit": fit,
        "pattern_boost": boost_sum,
        "final_score": final,
        "segment": segment,
        "priority": SEGMENT_TO_PRIORITY[segment],
        "signals": {
            "opportunity": opp_signals,
            "intent": intent_signals,
            "fit": fit_signals,
            "pattern": boost_signals,
        },
        "score_breakdown": score_breakdown,
        "score_layers": score_layers,
        "active_weights": active_weights,
        "clinic_subsector": lead.get("clinic_subsector"),
    }

    logger.info(
        "Score: %s | final=%.1f segment=%s opp=%d intent=%d fit=%d boost=%d subsector=%s",
        lead.get("isim"), final, segment, opportunity, intent, fit, boost_sum,
        lead.get("clinic_subsector", "-"),
    )
    return result


# --------------------------------------------------
# 5. EXPLAIN / DEBUG
# --------------------------------------------------

def explain_score(result: dict, lead: dict | None = None) -> str:
    if result["status"] == "rejected":
        return f"ELENDI: {result['reason']}"

    boost = result.get("pattern_boost", 0)
    lines = [
        f"Skor: {result['final_score']} ({result['segment']})",
        f"  = 0.50·{result['opportunity']} + 0.30·{result['buyer_intent']} + 0.20·{result.get('fit', 0)} + {boost:+d} boost",
        "",
        f"Opportunity : {result['opportunity']}",
        f"Buyer Intent: {result['buyer_intent']}",
        f"Fit         : {result.get('fit', 0)}",
        f"Pattern Boost: {boost:+d}",
    ]

    sub = result.get("clinic_subsector")
    if sub:
        lines.append(f"Klinik alt sektör: {sub}")

    breakdown = result.get("score_breakdown") or []
    if breakdown:
        lines.append("\nEn etkili sinyaller:")
        lines.extend(f"  {s}" for s in breakdown)

    signals = result.get("signals", {})
    if signals.get("pattern"):
        lines.append("\nPattern boost sinyalleri:")
        lines.extend(f"  {s}" for s in signals["pattern"])
    if signals.get("opportunity"):
        lines.append("\nOpportunity sinyalleri:")
        lines.extend(f"  {s}" for s in signals["opportunity"])
    if signals.get("intent"):
        lines.append("\nIntent sinyalleri:")
        lines.extend(f"  {s}" for s in signals["intent"])
    if signals.get("fit"):
        lines.append("\nFit sinyalleri:")
        lines.extend(f"  {s}" for s in signals["fit"])

    active_w = result.get("active_weights", {})
    if active_w:
        lines.append("\nSektör ağırlıkları (1.0'dan farklı):")
        for k, v in active_w.items():
            status = "KAPALI" if v == 0.0 else f"x{v}"
            lines.append(f"  {k}: {status}")

    return "\n".join(lines)


# --------------------------------------------------
# 6. COVERAGE STATS
# --------------------------------------------------

def apply_hot_limiter(
    results: list[dict],
    hot_cap_ratio: float = 0.20,
) -> list[dict]:
    """
    Batch scoring sonrası çalıştır.
    HOT oranı hot_cap_ratio'yu (varsayılan %20) geçerse,
    en düşük final_score'lu HOT lead'ler WARM'a düşürülür.
    _hot_limiter_applied=True işareti eklenir, log yazılır.
    """
    ok_results = [r for r in results if r.get("status") == "ok"]
    total_ok = len(ok_results)
    if total_ok == 0:
        return results

    hot_results = [r for r in ok_results if r.get("segment") == "HOT"]
    max_hot = max(1, int(total_ok * hot_cap_ratio))

    if len(hot_results) <= max_hot:
        return results

    hot_sorted = sorted(hot_results, key=lambda r: r.get("final_score", 0))
    to_demote = len(hot_results) - max_hot
    demote_set = {id(r) for r in hot_sorted[:to_demote]}

    for r in results:
        if id(r) in demote_set:
            r["segment"] = "WARM"
            r["priority"] = SEGMENT_TO_PRIORITY["WARM"]
            r["_hot_limiter_applied"] = True
            logger.info("HOT limiter: %s → WARM (final=%.1f)", r.get("isim"), r.get("final_score", 0))

    return results


def coverage_stats(leads: list[dict]) -> dict:
    """Kaç lead'de kanal verisi var/yok."""
    total = len(leads)
    if total == 0:
        return {}
    stats: dict[str, dict] = {}
    for field in CHANNEL_FIELDS:
        present = sum(1 for l in leads if l.get(field) is not None)
        stats[field] = {
            "present": present,
            "missing": total - present,
            "coverage_pct": round(present / total * 100, 1),
        }
    return {"total_leads": total, "fields": stats}
