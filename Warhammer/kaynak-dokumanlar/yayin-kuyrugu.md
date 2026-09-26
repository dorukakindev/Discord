### KANAL: yayin-kuyrugu
## Yayın Kuyruğu — İş Akışı

Bu kanal, taslakların hangi aşamada olduğunu izlemek ve yayın sırasını yönetmek için kullanılır. Her taslak aynı anda yalnızca bir durumda bulunur; durum değişikliklerini editörler yapar ve her geçiş `bot-log`'a kaydedilir.

**Durumlar**
- **Hazır:** Taslak şablona uygun biçimde açılmış, validate denetiminden geçmiş ve denetime alınmayı bekliyor. Henüz hiçbir içerik incelemesi yapılmamıştır.
- **Kaynak Bekliyor:** Kaynak denetimi bir veya daha fazla eksik tespit etmiş; iddiaya birincil kaynak eklenmesi ya da ifadenin yumuşatılması gerekiyor.
- **Kanon Kontrolünde:** Kaynak denetimi geçilmiş, kanon denetçisi metni etiketliyor.
- **Revizyon Gerekli:** Kaynak veya kanon denetimi düzeltme gerektiren bir sorun bulmuş; yazar yeni sürüm hazırlıyor.
- **Yayına Hazır:** Tüm denetimler geçilmiş; metin ilgili kanala yapıştırılmayı bekliyor.

**Geçiş kuralları**
1. Hazır, Kaynak Bekliyor'a veya doğrudan Kanon Kontrolünde'ye geçer.
2. Kaynak Bekliyor, eksikler giderilince Kanon Kontrolünde'ye geçer; yazar düzeltmeyi yapamıyorsa Revizyon Gerekli'ye düşer.
3. Kanon Kontrolünde, sonuca göre Yayına Hazır'a veya Revizyon Gerekli'ye geçer; yeni kaynak eksiği bulunursa Kaynak Bekliyor'a döner.
4. Revizyon Gerekli, yazar yeni sürümü yükleyince yeniden Hazır'a döner ve denetim baştan yapılır.
5. Yayına Hazır bir metinde yayından önce değişiklik yapılırsa taslak Hazır'a geri alınır.
6. Yayın gerçekleştiğinde kayıt kuyruktan kaldırılır ve `degisiklik-gunlugu`na işlenir.
---MSG---
## Kuyruk Tablosu ve Öncelik

Kuyruk, editörler tarafından sabitlenmiş tek bir mesajda güncel tutulur. Her satır bir taslağı temsil eder.

```
YAYIN KUYRUĞU — Güncelleme: GG.AA.YYYY

Öncelik | Kanal / Kayıt         | Tür       | Sürüm | Durum              | Sorumlu   | Not
--------|-----------------------|-----------|-------|--------------------|-----------|-----
P1      | kanal-adi             | Yeni      | v1    | Hazır              | @yazar    | 
P2      | kanal-adi             | Revizyon  | v2    | Kaynak Bekliyor    | @denetci  | msg 4 kaynaksız sayı
P2      | kanal-adi             | Yeni      | v1    | Kanon Kontrolünde  | @denetci  | 
P3      | forum > Kayıt Adı     | Koleksiyon| v3    | Revizyon Gerekli   | @yazar    | evren-içi iddia
P1      | kanal-adi             | Yeni      | v2    | Yayına Hazır       | @editor   | 
```

**Öncelik düzeyleri**
- **P1:** Başlatma sırasındaki çekirdek kanallar (dizin kanalları ve ana A–Z maddeleri) ile yayımlanmış metindeki olgusal hataların düzeltilmesi.
- **P2:** Standart A–Z kanalları ve tam revizyonlar.
- **P3:** Koleksiyon kayıtları, kaynakça ve editoryal kanal güncellemeleri.

**Kurallar**
- Aynı kanal için kuyrukta aynı anda yalnızca bir açık taslak bulunabilir.
- **Revizyon Gerekli** durumunda uzun süre işlem görmeyen taslaklar editör tarafından sorumlusuna hatırlatılır; yanıt gelmezse kuyruktan çıkarılıp `taslak-kuyrugu`nda arşivlenir.
- Yayın sırası öncelik düzeyini, aynı düzeyde ise **Yayına Hazır** durumuna ulaşma sırasını izler.
