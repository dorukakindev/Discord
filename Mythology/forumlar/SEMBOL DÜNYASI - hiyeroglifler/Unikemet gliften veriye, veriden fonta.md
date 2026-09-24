-# CODEX MYTHICA · Hiyeroglif Rehberi · Kayıt
# Unikemet: gliften veriye, veriden fonta
> **Dönem:** Unicode 17.0 dönemi · **Whyitmatters:** Dijital hiyeroglif desteği yalnızca karakter kodu değildir; işaret kimliği, açıklama, fonksiyon, kaynak ve quadrat düzeni birlikte modellenir.

### Okuma Odağı
- Temel blok Gardiner tabanlı adlandırmaya, Extended-A ise algoritmik kod noktası adlarına dayanır.
- Format kontrolleri yatay/dikey bağlama, ekleme, segment, hasar ve kayıp işaret düzenini temsil eder.
- UTF-8/NFC veri, font eksikliği yüzünden ekranda bozulmuş gibi görünebilir.

### Ne Kontrol Edilmeli
- Görünen glif, Unicode karakteri ve Egyptological transliterasyonu ayrı ayrı doğrula.
- Quadrat düzeni gerekiyorsa düz işaret dizisiyle yetinme.
- Extended-A işaretlerinde Unikemet açıklamasını kontrol et.

### Kaynak No
- Unicode Chapter 11
- UAX #57
- Unikemet.txt