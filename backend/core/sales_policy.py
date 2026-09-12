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
    "teklif_durumu": "Görüşmeye sunulan çalışma önerisi",
    "fiyat_araligi": "İhtiyacınıza uygun kapsamı birlikte seçtikten sonra ücret ve ödeme planını yazılı olarak paylaşacağız.",
    "teslim_suresi": "İçerik ve erişim ihtiyaçlarını netleştirerek başlangıç ve teslim tarihlerini birlikte belirleyeceğiz.",
    "bakim_destek": "Yayın sonrası güncelleme, revizyon ve destek seçeneklerini ihtiyacınıza göre ayrıca belirleyeceğiz.",
    "kapsam_siniri": "Bu belge bir çalışma önerisidir; kesin kapsam ve ticari şartlar karşılıklı onayla belirlenir. Reklam ve dış servis giderleri ayrıca değerlendirilir. Arama sıralaması veya müşteri artışı taahhüt edilmez.",
}


def missing_site_proposal(lead: dict) -> dict:
    name = (lead.get("isim") or "İşletmeniz").split(",", 1)[0]
    return {
        **PROPOSAL_TERMS,
        "baslik": f"{name} — dijital görünürlük ve iletişim önerisi",
        "giris": "Sizi araştıran kişilerin hizmetlerinizi tanıyabileceği ve iletişim bilgilerinize kolayca ulaşabileceği bir dijital yapı üzerine konuşmak isteriz. İncelediğimiz işletme kaydında site bağlantınızı göremedik; mevcut bir siteniz varsa önerimizi onu inceleyerek şekillendirebiliriz.",
        "durum_ozeti": "İlk adımımız mevcut sitenizi ve Google İşletme Profilinizdeki bağlantıyı kontrol etmek. Böylece gerçekten ihtiyaç duyduğunuz çalışmayı seçebiliriz.",
        "cozum": "Siteniz varsa mevcut yapıyı inceleyerek gerekli çalışmayı belirleyebiliriz. Yoksa hizmetlerinizi açıklayan, Google ve yapay zekâ destekli aramalarda keşfedilmeyi destekleyen ve ziyaretçinin iletişime geçmesini kolaylaştıran bir site planlayabiliriz.",
        "baslangic_odaklari": ["Resmi siteyi ve Google İşletme Profili bağlantısını doğrulamak.", "Hizmet içeriklerini, işletme bilgilerini ve telefon/yol tarifi akışını planlamak.", "Teknik erişilebilirlik ve uygun ölçüm kurulumunun kapsamını belirlemek."],
        "beklenen_sonuclar": "Çalışmanın hedefi; hizmetlerinizi anlaşılır biçimde sunmak, telefondan rahat kullanılan bir deneyim hazırlamak ve iletişime geçişi kolaylaştırmak. Yayın sonrasında, erişim izninizle oluşturacağımız başlangıç ölçümünü esas alarak hangi alanları geliştireceğimizi değerlendirebiliriz.",
        "bir_sonraki_adim": "Mevcut site adresini veya site ihtiyacınızı netleştirip kapsamı birlikte belirleyelim.",
        "cta": "İsterseniz işletmenize uygun sayfa yapısını içeren kısa bir öneri paylaşalım.",
    }
