# AgencyOS hedef müşteri değerlendirmesi — 12 Eylül 2026

## Sonuç ve kapsam

Mevcut yapı işletme keşfi ve özellikle website hizmeti için ön liste üretmeye uygundur. Ödeme yapma olasılığını veya SEO/GEO/conversion hizmetlerine ticari uygunluğu doğruladığı söylenemez. Bu çalışma kod incelemesi ve mevcut fonksiyonlarla 12 sentetik senaryodan oluşur; gerçek satış dönüşümlerine dayalı bir doğruluk ölçümü değildir. Ürün kodu, puanlama, canlı kayıtlar ve deployment değiştirilmedi.

Tekrar çalıştırma: `.venv-audit\Scripts\python.exe artifacts/evaluate_qualification.py`. Test gerçek scorer ve ICP fonksiyonlarını yükler; ortam dosyalarını okumaz, servis çağırmaz. Klinik playbook'u ve geniş ICP modu kullanılır. Altı davranış kontrolü geçti; bu, ticari hedefin doğru olduğu değil bulguların tekrar üretildiği anlamına gelir. Ham giriş ve çıktılar aynı klasördeki `qualification-evaluation-2026-09-12.json` dosyasındadır.

## Ölçülen sonuçlar

| Kontrollü senaryo | Skor | Sonuç |
|---|---:|---|
| 2 yorum, 3.2 puan, telefon var, site yok, aktivite bilinmiyor | 83.1 | HOT; intent 50, veri güveni 0.30 |
| Aynı işletme, son yorum 400 gün önce, Instagram aktivitesi sıfır | 78.1 | REVIEW; zombie kontrolü çalışıyor |
| 318 yorum, 4.8 puan, site var/zayıf; temel veriler | 39.9 | REVIEW |
| Aynı işletme: organik ilk 10 dışında, 5 indeksli sayfa, aktif yorum akışı, audit 30, hız 30 | 84.5 | HOT |
| Önceki işletme, yalnızca yorum sayısı 600 | 84.5 (scorer ayrı çalıştırıldığında) | Gerçek akışta ICP eliyor; geniş mod üst sınır 530 |
| 318 yorum, iyi site, aktif yorumlar, organik görünürlük açığı | 56.5 (scorer ayrı çalıştırıldığında) | ICP site durumundan eliyor |
| 318 yorumlu işletmede site verisi yok | 69.8 | WARM; site var/zayıf senaryosuna göre +29.9 |
| Audit genel skor 55; hız ölçümü bilinmiyor | 44.6 | REVIEW |
| Aynı audit; bilinmeyen hız 0 olarak aktarılıyor | 50.9 | Ölçüm eksikliği +6.3 puan üretiyor |
| Genel audit 55, dönüşüm alt skoru 10 / 90 | 44.6 / 44.6 | Dönüşüm alt skoru tek başına sıralamayı etkilemiyor |
| Kalıcı kapalı işletme | — | Scorer reddediyor |

Bu senaryolardaki alanlar varsayımsaldır. Özellikle 318 yorumlu profil Hilal örneğine benzese de bu test işletmenin güncel durumunu veya satın alma niyetini ölçmez. Veri güveni 0.30, satın alma ihtimali %30 anlamına gelmez.

## Koddan doğrulanan nedenler

1. `backend/core/lead_scorer.py`: Opportunity ağırlığı %75, Intent %25. Sitesizlik +40 ve telefonla +10; az yorum ve düşük puan ek artış alıyor. Alıcı aktivitesi bilinmiyorsa Intent başlangıcı 50. Sitesiz/telefonlu/30'dan az yorumlu aday için 70 tabanı var. Veri güveni sıralamayı sınırlamıyor. Bu nedenle yüksek skor ticari talebin kanıtı değil.
2. `backend/services/search_service.py`: hızlı arama site analizi ve SERP araştırmasını atlıyor; boş audit ile skor hesaplıyor. Kodun bu sinyalleri desteklemesi, aramada toplandıkları anlamına gelmiyor.
3. `backend/core/lead_collector.py`, `_site_durumu`: URL varsa incelemeden `zayif`, yoksa `yok` dönüyor. Site kalitesi gözlem değil varsayım. Kaynakta URL bulunmaması gerçek hayatta site bulunmadığını kanıtlamaz.
4. `backend/core/icp_filter.py` ve `backend/playbooks/clinic_general.json`: yorum üst sınırı ve yalnızca yok/zayıf site kabulü, güçlü adayları puanlamadan eliyor. Arama bunları Elendi olarak gösterebilir; collection kayıt akışına alınmazlar.
5. `backend/services/lead_service.py`, `lead_to_core_dict`: source_data içindeki aktivite/SEO sinyallerini audit girdisine taşımıyor; yalnızca temel işletme alanları kullanılıyor. Audit sonrasında site güncelliği ayrıca ekleniyor, diğer kaydedilmiş sinyaller geri yüklenmiyor.
6. `backend/core/audit_generator.py` ölçülmeyen hızı 0 ve `hiz_veri_var=False` tutuyor. `backend/services/audit_service.py` bu bayrağı kontrol etmeden hızı scorer'a veriyor. Ölçüm yokluğu gerçek yavaşlık gibi puan artırabiliyor.
7. `clinic_general.json` içindeki hasta kaybı aralıkları ve varsayılan 65 güven değeri şablon değerleri. Gerçek trafik, randevu veya satış verisiyle doğrulanmış gelir kaybı ve olasılık olarak kullanılmamalı.

## Önerilen sonraki adım

Önce veri doğruluğu: bilinmeyen ile kötü/yok ayrımı, hız ölçümü bayrağı, audit girdilerinde mevcut kanıtların korunması. Ardından kullanıcı onayıyla ticari skor tasarımı: dijital problem, aktif işletme/ekonomik kapasite, hizmet uyumu, karar vericiye erişim ve kanıt güvenini ayrı gösterme. Rating/yorum sayısından otomatik ödeme isteği sonucu çıkarılmamalı.

Gerçek başarı testi için tek sektör/lokasyonda 30–50 işletmelik pilot hazırlanmalı. Yüksek puanlılar yanında orta puanlı ve elenmiş güçlü işletmeler de örneklenmeli; bütün grupların seçim yöntemi kaydedilmeli. Manuel değerlendirme mümkünse skoru görmeden yapılmalı. Resmi site ve işletme aktifliği doğrulanmalı, her problem somut kanıta bağlanmalı. Ayrı iletişim yetkisi alındıktan sonra görüşme, nitelikli görüşme, teklif, kazanılan müşteri, gelir ve harcanan zaman takip edilmeli. Yalnızca yüksek puanlılara ulaşıp diğerlerini ölçmemek kaçan fırsatları gizler. Küçük pilot yön gösterir; satın alma olasılığını kalibre etmek için daha fazla sonuç gerekir.

Bu çalışma kapsamında işletmelere mesaj gönderilmedi ve ücretli dış API testi yapılmadı.
