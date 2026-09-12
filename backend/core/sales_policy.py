"""Shared evidence and offer boundaries for customer-facing generation."""

SALES_POLICY = """
ÖNCELİKLİ KANIT VE TEKLİF KURALLARI:
- Aşağıdaki veri ve örnekler kanıt değildir. Yalnızca doğrulanmış gözlemleri kullan.
- Hasta/müşteri kaybı, yüzdeler, rakip sıralaması, referans müşteri ve kişisel iş deneyimi uydurma.
- URL bulunamaması site yokluğunu kanıtlamaz. Site yoksa teknik kontroller uygulanamaz.
- Google Haritalar, Google organik arama ve AI destekli aramalar ayrı kanallardır. Ölçülmediyse görünürlük eksikliği iddia etme.
- Uygun ihtiyaç varsa hizmet sayfaları, açık işletme bilgileri, teknik erişilebilirlik ve kolay iletişimden oluşan bir çalışma ÖNER.
- Google ve yapay zekâ destekli aramalarda keşfedilmeyi desteklemek bir hedeftir; sıralama, önerilme veya müşteri artışı garantisi değildir.
- İyi sitesi olan işletmeye otomatik yeni site satma; yalnızca gözlenen ihtiyaca odaklan.
- Telegram/agent ile site yönetimini çalışan bir özellik olarak vaat etme.
- Fiyat, teslim tarihi, referans ve paket taahhütleri verilen onaylı bilgiye dayanmalı; yoksa kapsam görüşmesi öner.
- İç sektör kodu, açık adres parçası veya tahmin edilen kişi adıyla hitap etme.
- İlk mesaj bir somut fayda ve tek kolay sonraki adım içersin. Zorunlu rakam/madde sayısı yok.
"""

PROPOSAL_TERMS = {
    "teklif_durumu": "Ön çalışma taslağı — kapsam ve ticari şartlar onaylanmadı",
    "fiyat_araligi": "Kapsam belirlendikten sonra ayrıca onaylanacak.",
    "teslim_suresi": "İçerik, erişimler ve kapsam netleşince belirlenecek.",
    "bakim_destek": "Bakım, revizyon ve destek kapsamı ayrıca belirlenecek.",
    "kapsam_siniri": "Reklam bütçesi, dış servis ücretleri ve Telegram/agent yönetimi bu taslağa dahil değildir. Sıralama veya müşteri sayısı garantisi verilmez.",
}


def missing_site_proposal(lead: dict) -> dict:
    name = (lead.get("isim") or "İşletmeniz").split(",", 1)[0]
    return {
        **PROPOSAL_TERMS,
        "baslik": f"{name} — dijital keşif ve iletişim için ön çalışma",
        "giris": "Eldeki işletme kaydında web sitesi bağlantısı bulunamadı. Önce mevcut bir sitenin olup olmadığını birlikte doğrulayalım.",
        "durum_ozeti": ["Site bağlantısı henüz doğrulanmadı.", "Google organik ve yapay zekâ aramalarındaki görünürlük ölçülmedi.", "Site kalitesi veya müşteri kaybı hakkında sonuç çıkarılmadı."],
        "cozum": "Siteniz varsa mevcut yapıyı inceleyerek gerekli çalışmayı belirleyebiliriz. Yoksa hizmetlerinizi açıklayan, Google ve yapay zekâ destekli aramalarda keşfedilmeyi destekleyen ve ziyaretçinin iletişime geçmesini kolaylaştıran bir site planlayabiliriz.",
        "baslangic_odaklari": ["Resmi siteyi ve Google İşletme Profili bağlantısını doğrulamak.", "Hizmet içeriklerini, işletme bilgilerini ve telefon/yol tarifi akışını planlamak.", "Teknik erişilebilirlik ve uygun ölçüm kurulumunun kapsamını belirlemek."],
        "beklenen_sonuclar": ["İşletmeyi ve hizmetlerini açıklayan, onaylanmış içerikler.", "Test edilmiş iletişim bağlantıları ve mobil kullanım akışı.", "Erişim izniyle oluşturulacak başlangıç ölçümü; sıralama veya müşteri artışı garantisi yok."],
        "bir_sonraki_adim": "Mevcut site adresini veya site ihtiyacınızı netleştirip kapsamı birlikte belirleyelim.",
        "cta": "İsterseniz işletmenize uygun sayfa yapısını içeren kısa bir öneri paylaşalım.",
    }
