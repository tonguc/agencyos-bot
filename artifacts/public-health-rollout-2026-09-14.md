# Kamu kurumu satış uygunluğu — 14 Eylül 2026

PR22, üretim commit f66466b41f241faaf64f1082243d14bc563797d7. GitHub CI, Vercel ve Railway başarılı. 137 backend testi (DB entegrasyon testleri hariç) ve TypeScript başarılı.

Canlı İstanbul büyükçekmece doktor / limit25: 13 kayıt korunuyor, Öncelikli 10'dan 9'a indi, Aktif satış dışı 1. Opr. Dr. Sarper Polat kaydı, Mimar Sinan / Devlet Hastanesi adres sinyaliyle 13. sırada, puan0, açık gerekçeyle gösterildi. Filtre seçilebiliyor.

Kural yalnız mevcut kayıt isim/adres/kategori alanlarını tarar; hukuki veya güncel istihdam doğrulaması iddiasında bulunmaz. Eğitim ve araştırma kurumları istisna sayılmaz. Hastane caddesi/karşısı gibi adres tarifleri kamu görevi sayılmaz. Özel kurumlar bu kuralla satış dışına alınmaz.

Arama normalizasyonu, scorer (manuel audit dahil), eski DB skorlarının aramaya eklenmesi ve cache sürümü güncellendi. Sayısal skor katmanlarının ağırlıkları değişmedi; son satış uygunluğu kararı finali0/LOW yapıyor. Veritabanında toplu güncelleme/silme, mesaj gönderme veya outreach engeli uygulanmadı. Eski CRM detay skorları yeniden değerlendirmeye kadar kalabilir. Üniversite veya bilinmeyen kurumlar otomatik hukuki sınıflandırmaya tabi değil.
