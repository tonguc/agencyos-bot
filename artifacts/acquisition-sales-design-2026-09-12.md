# AgencyOS — müşteri edinme ve teklif yapısı

## Karar

AgencyOS'un görevi bütün işletmelere aynı website teklifini göndermek değil; doğrulanmış probleme göre uygun hizmeti seçmek, görüşme başlatmak ve kapsamı belli bir teklife taşımaktır. Google Haritalar, organik arama, AI destekli keşif, güven, iletişim ve işletme yönetimi birlikte düşünülmeli; her adaya bütün paketler önerilmemeli.

Bu belge mevcut kaynak kodu, daha önceki 12 senaryolu değerlendirme ve kullanıcının canlı ekranı üzerinden hazırlanmıştır. Yeni canlı tarama, mesaj gönderimi, kod değişikliği veya deployment yapılmadı. Aşağıdaki paketler ürün tasarımı önerisidir; mevcut teslim kapasitesi doğrulanmış hizmet kataloğu değildir. Fiyat ve teslim tarihi uydurulmadı.

## Mevcut sistemde somut boşluklar

| Bulgu | Sonuç | Kaynak |
|---|---|---|
| Kısa satış mesajı, V1–V4, ilk otomatik mesaj, takip ve teklif ayrı talimatlarla üretiliyor | Bir bölümde düzeltilen iddia diğerinde geri geliyor | backend/core/sales_output_generator.py, prompts.py, outreach_writer.py, proposal_generator.py |
| V1 rakam ister; V4 benzer iş deneyimi çerçevesi verir; teklif tahmini sayısal sonuç ister | Kanıtsız oran, deneyim ve sonuç anlatımı teşvik ediliyor | prompts.py OUTREACH_PROMPT; proposal_generator.py PROPOSAL_PROMPT |
| ONERILEN_MAP bütün hook türlerini V4'e eşliyor | “Önerilen” etiketi müşteriye özgü seçim veya başarı ölçümü değil | outreach_writer.py |
| Audit yokken sentetik audit “müşteri kaybı” ve genel skor 40 oluşturuyor | Eksik bilgi bulgu gibi sonraki metinlere taşınıyor | services/outreach_service.py _synthetic_audit |
| Teklif JSON'u çözüm, başlangıç odakları, beklenen sonuçlar üretiyor; ekran başlık/giriş/CTA ve başka alanlar bekliyor | Üretilen ayrıntının bir kısmı web ekranında görünmüyor | proposal_generator.py; frontend/app/leads/[id]/page.tsx:298 |
| Fiyat, kapsam, revizyon, bakım, onay ve kabul şartları yapılandırılmış teklif girdisi değil | PDF var ama ticari teklif eksik; model bunları kendiliğinden belirlememeli | proposal_generator.py; services/proposal_service.py |
| pricing.py müşteri paket fiyatlarını değil API maliyetlerini tutuyor | Dosya adı bir hizmet fiyat kataloğu olduğu izlenimi vermemeli | core/pricing.py |
| Bot komutları lead/audit/mesaj/teklif/durum işlemleri | Telegram'dan müşteri sitesi yönetimi mevcut yetenek olarak satılamaz | bot/handlers.py; main.py |
| Mesaj veya teklif üretmek lead durumunu Mesaj/Teklif yapıyor | Taslak üretimi ile gerçek gönderim birbirine karışabiliyor | services/outreach_service.py; proposal_service.py |
| Outreach ve proposal audit_id tutuyor; ekran ayrı son kayıtları gösterebiliyor | Yeni audit yanında eski iddialı mesaj/teklif bulunabiliyor | ilgili services ve lead ekranı |
| Site yokken audit sayısal UX/SEO puanları üretiyor | “Ölçülmedi” ile düşük performans karışıyor | audit_generator.py, önceki canlı test |

## Önerilen ortak değerlendirme

Her işletme için tek kısa karar kaydı hazırlanmalı:

- **Gözlem:** Kaynak, tarih ve kontrol edilen URL/sorguyla doğrulanmış bilgi.
- **Bilinmeyen:** Toplanmamış veya doğrulanmamış bilgi; olumsuz bulgu sayılmaz.
- **İhtiyaç:** Problemin işletme için muhtemel anlamı; varsayım olduğu belirtilir.
- **Hizmet eşleşmesi:** Bir ana öneri ve gerekirse bir tamamlayıcı; seçim gerekçesi.
- **Ticari uygunluk:** Aktiflik ve erişim kanıtları; bütçe, satın alma zamanı ve karar verici bilinmiyorsa açıkça bilinmiyor.
- **Sonraki adım:** Doğrulama sorusu, küçük örnek, keşif görüşmesi veya teklif.

Ölçümler müşteriyle temas sonrası erişim izniyle genişletilir. Arama görünürlüğü sorgu/lokasyon/tarih bağlamında, AI görünürlüğü platform/prompt/tarih bağlamında tutulur. Tek cevapta görünmemek genel görünmezlik kanıtı değildir. Arama sıralaması, gelir veya randevu artışı garanti edilmez.

## Paket taslağı ve karar kuralları

| İhtiyaç | Önerilen hizmet | Somut teslimat | Ön koşul / ölçüm |
|---|---|---|---|
| Resmi site bağlantısı bulunamadı | Önce doğrulama; gerçekten site yoksa Dijital Temel | İşletme ve hizmet sayfaları, mobil iletişim/yol tarifi, teknik indekslenebilirlik kontrolü, temel ölçüm kurulumu | İşletme siteyi doğrular; içerikler onaylanır. Teslim kontrolü: sayfalar, bağlantılar ve ölçüm olayları |
| Site var, hizmet aramalarında doğrulanmış açık var | Organik ve Yerel Keşif | Teknik sorun düzeltmeleri, ihtiyaca göre hizmet içerikleri, Google profil bilgi tutarlılığı, başlangıç görünürlük raporu | Alan adı/profil erişimi ve sorgu listesi. Organik gösterim/tıklama, profil etkileşimleri ve nitelikli talep |
| İçerik işletmeyi/uzmanlığı yeterince açıklamıyor | AI destekli keşif için içerik çalışması | Açık işletme/uzmanlık/hizmet bilgisi, gerçek sorulara cevaplar, uygun yapılandırılmış veri ve kaynak tutarlılığı | SEO ile ortak işler iki kez ücretlendirilmez. Sabit örnek sorgularla kaynak/atıf takibi; sonuç garantisi yok |
| Ziyaret var, iletişime geçişte gözlenen engel var | İletişim ve Dönüşüm | Mobil akış düzeltmesi, çalışır telefon/form/randevu yönlendirmesi, mesaj hiyerarşisi, ölçüm olayları | Test edilmiş engel veya erişim izniyle analiz. Tıklama gerçek müşteri değildir; nitelikli başvuru ayrıca izlenir |
| Bilgiler sık değişiyor; işletme güncellemekte zorlanıyor | Bakım ve Kolay Yönetim | İçerik güncelleme süreci, kapsamı belirli bakım/destek | Telegram/agent yalnızca çalışan prototip, yetki, önizleme/onay ve geri alma doğrulandıktan sonra seçenek |

Google Haritalar ve organik sonuçlar ayrı ölçülür. Google'ın AI özellikleri için ayrı sihirli teknik gereklilik yoktur; mevcut SEO temelleri önemlidir. Diğer AI platformları ayrıca değerlendirilmelidir; Google belgesinden bütün platformlara sonuç çıkarılmaz.

Kaynaklar: [Google AI özellikleri](https://developers.google.com/search/docs/appearance/ai-features), [yerel sıralama](https://support.google.com/business/answer/7091?hl=en).

## Sibel örneğinde karar

Kanıt: eldeki kayıtta URL bulunamadı ve telefon mevcut. Yorum sayısı eski lead kaydında 3, ekrandaki Maps kaynağında 11; güncellik farkı çözülmeden metinde sayı kullanmayız. Organik/AI görünürlüğü ölçülmedi. Bütçe ve satın alma niyeti bilinmiyor. Dolayısıyla ilk adım URL doğrulaması, ardından uygunsa küçük sayfa taslağıdır. “Google'da yoksunuz” veya “hastalar rakibe gidiyor” iddiası yok.

Örnek ilk mesaj (taslak hazırlama kapasitesi sağlandıktan sonra):

> Merhaba, ben Tonguç. Muayenehanenizin kaydında web sitesi bağlantısını bulamadım. Kullandığınız bir site var mı? Yoksa, sizi ve hizmetlerinizi tanıtan, Google ve yapay zekâ destekli aramalarda keşfedilmenizi destekleyecek bir yapıyla hazırlanan, iletişim bilgilerinizi kolayca bulduran bir site için küçük bir taslak paylaşabilirim. Görmek ister misiniz?

İlgi gelirse önce kişinin verdiği bilgi doğrulanır ve örnek gösterilir. “Sitemiz zaten var” yanıtında site yapımı otomatik önerilmez; mevcut site üzerinden ihtiyaç araştırılır. “Şu an düşünmüyoruz” yanıtında görüşmeye zorlayan mesaj üretilmez. Fiyat sorulursa onaylı paket fiyatı veya hangi kapsam bilgisinin eksik olduğu açıklanır; mevcut prompttaki koşulsuz fiyat vermeme yaklaşımı kaldırılır.

## Gerçek teklifin içeriği

Teklif tek bir yapıdan hem ekrana hem PDF'e basılmalı:

1. İşletmenin doğrulanmış ihtiyacı ve hedefi.
2. Önerilen paket, seçilme gerekçesi ve teslim edilecek işler.
3. Dahil olmayan işler; müşteriden gereken bilgi/erişim/onaylar.
4. Başlama koşulları, teslim süresi ve kontrol noktaları.
5. Kurulum bedeli, varsa aylık bedel, dış servis maliyetleri, ödeme şartları ve geçerlilik.
6. Revizyon, bakım, hesap/alan adı sahipliği ve destek kapsamı.
7. Teslim kabul ölçütleri; ayrıca izlenecek iş sonuçları.
8. Tek net sonraki adım.

Fiyat ve süre onaylı katalogdan gelir. Yoksa “taslak — kapsam/fiyat belirlenecek” gösterilir; müşteri gönderimine hazır sayılmaz. Portföy örnekleri yalnızca gerçek ve ilgiliyse kullanılır. LLM anlatımı düzenler; ticari taahhüt veya geçmiş başarı yaratmaz.

## Uygulama sırası

**P0 — Güvenilirlik:** Ortak kanıt kuralları tüm mesaj, takip, yanıt, teklif ve fallback yollarına uygulanır. Desteksiz iddialar yalnızca promptla değil çıktı kontrolüyle de engellenir. Site yok/erişilemiyor/ölçüm yok durumları ayrılır. Ekranda taslak ve eski audit'e bağlı içerik ayırt edilir. Üretildi/gönderildi/yanıtlandı ayrımı korunur.

**P1 — Hizmet eşleşmesi ve teklif:** Küçük, sürümlü bir hizmet kataloğu eklenir. Katalog teslim edilebilirlik ve kanıt gereksinimini içerir. Müşteriye özgü bir ana teklif seçilir; mevcut Opportunity Score değişmez. Aynı teklif alanları UI/PDF'e taşınır. Model fiyat üretmez.

**P2 — Öğrenme:** 30–50 adaylık pilot; üst, orta ve elenmiş gruplar dahil. Aday/paket/mesaj sürümü ve sonuç kaydedilir. Olumlu yanıt, nitelikli görüşme, teklif, kazanım, gelir ve emek karşılaştırılır. Gözlem sayısı azsa kazanan ilan edilmez. Gönderim ayrı kullanıcı yetkisiyle yapılır.

**P3 — Telegram yönetimi:** İlk pilotta gerçekten talep görülürse bir müşteri sitesiyle prototip. Yetkisiz değişiklik, yanlış işletme, başarısız yayın ve geri alma testleri tamamlanmadan paket vaadi yapılmaz. Povlex entegrasyonu bu planın dışında.

## Kabul senaryoları

- Sitesiz veya URL'si bilinmeyen aday: tek doğrulama sorusu; teknik puanlar ölçülmüş gibi sunulmaz.
- HTTP hatası: SSL/form eksikliği çıkarılmaz; yeniden kontrol adımı verilir.
- Güçlü Google profili + kanıtlı organik açık: otomatik site yenileme yerine uygun keşif hizmeti.
- İyi site + ölçülmüş iletişim sorunu: yalnızca gerekli dönüşüm işi.
- Hiç ölçülmemiş AI görünürlüğü: yokluk iddiası değil inceleme önerisi.
- Yeni audit + eski mesaj: eski sürüm görünür uyarı taşır; sessizce güncel sayılmaz.
- Bütün üretim yollarında sahte referans, zorunlu kayıp oranı, iç sektör kodu ve onaysız özellik vaadi engellenir.
- UI/PDF kapsam, ücret ve süre bakımından aynı; eksik şartlar taslak durumunu korur.
- Telegram teslim edilebilir değilse müşteri metnine girmez.

## Açık ticari kararlar

Gerçek fiyatlar, haftalık teslim kapasitesi, bakım kapsamı ve kullanılabilecek portföy örnekleri koddan doğrulanamaz. Bunlar uygulamayı tasarlamayı engellemez; katalogda onay bekleyen alanlar olarak tutulabilir. Müşteriye gönderilecek nihai fiyat ve teslim taahhüdü öncesinde işletme sahibi tarafından belirlenmelidir.
