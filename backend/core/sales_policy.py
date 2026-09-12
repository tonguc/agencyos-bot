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
