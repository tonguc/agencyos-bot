# Arama doğruluğu ve hekim kimliği — 13 Eylül 2026

Yayınlar: PR19 bdcb97522e209526ed8d925d93b638cac5731e74; PR20 5e5c65746dc9487880e8d38b1705779ab3e00e82. GitHub CI, Vercel ve Railway başarılı.

Kontroller: 123 backend testi geçti; DB entegrasyon testleri hariç. Frontend TypeScript ve değişen iki ekran için ESLint başarılı.

Canlı aynı sorgu/limit karşılaştırması: İstanbul Beylikdüzü doktor, limit 10. Önce: Sonuç bulunamadı. İlk düzeltme sonrası: sağlayıcı liste döndürmedi. Tek place_results desteği sonrası: 1 sonuç, Beylikdüzü Doktorları Kliniği; çoklu kategori alanı okunuyor; 3.8/90 yorum, Beylikdüzü adresi. Bu ilçe envanterinin tamamlandığını göstermez. Maps sorguyu tek işletmeye yönlendirebilir.

Diğer değişiklikler: doktor eşdeğerleri; belirsiz konum notları; provider hata/boş/filtrelenmiş ayrımı; kimlik notlarının ICP aşamasında korunması; hekim/klinik sahipliği açıklaması; yeni cache sürümü. Sıfır sonuç veren doktor sorgusuna aynı konumda en çok bir hekim sorgusu eklenir, aday notunda açıklanır. Ek sorgu yalnızca boş yanıtta sağlayıcı kullanımını artırabilir. Skor ağırlıkları değiştirilmedi.

Sınırlamalar: kurum bağı otomatik kaynak doğrulaması henüz yok. Osman Nuri Akbulut araştırması ayrı raporda. Eski kayıtlar değiştirilmedi; aday detayındaki genel açıklama eski kayıtlarda da görünür. Konumu doğrulanamayan kayıt farklı ilçeden olabilir ve bu notu kontrol etmek gerekir.
