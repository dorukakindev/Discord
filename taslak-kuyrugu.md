### KANAL: taslak-kuyrugu
## Taslak Kuyruğu — Forum Açıklaması

Bu forum, The Imperial Archive'a girecek her yeni kanal metninin, kapsamlı revizyonun ve koleksiyon kaydının yayına çıkmadan önce bekletildiği çalışma alanıdır. Buraya açılan her gönderi tek bir taslağı temsil eder; taslak, kaynak ve kanon denetiminden geçip onay alana dek okuyucuya açık kanallara taşınmaz.

**Bu forum ne için kullanılır**
- Yeni A–Z lore kanalı taslakları
- Mevcut bir kanalın tam revizyonu ("X kanalını revize et" talepleri)
- Koleksiyon forumlarına (30–51) girecek tekil kayıt taslakları
- Dizin ve kaynakça kanallarında yapılacak kapsamlı güncellemeler

**Bu forum ne için kullanılmaz**
- Tek kelimelik yazım düzeltmeleri: doğrudan `degisiklik-gunlugu` üzerinden işlenir.
- Lore tartışması, fan teorisi üretimi veya genel sohbet.
- Kaynaksız "bence böyle" önerileri; her taslak en az bir resmî kaynak göstermelidir.

**Temel kurallar**
1. Her gönderi tek bir kanal ya da tek bir kayıt içindir; birden fazla kanalı aynı başlıkta toplamayın.
2. Gönderi başlığı adlandırma standardına uymalıdır (aşağıdaki şablona bakın).
3. Metin, Discord'a yapıştırılacağı biçimde `---MSG---` ayraçlarıyla bölünmüş ve her mesaj 1800 karakterin altında olmalıdır.
4. Taslak açıldığında durum etiketi **Hazır** ile başlar; etiket değişiklikleri yalnızca editörler tarafından yapılır ve `yayin-kuyrugu` iş akışını izler.
5. Kanon ve kaynak itirazları başlık altında yanıt olarak yazılır; taslak sahibi düzeltmeyi aynı başlıkta yeni sürüm olarak paylaşır.
---MSG---
## Taslak Gönderi Şablonu

Yeni taslak açarken aşağıdaki şablonu kopyalayıp doldurun. Boş kalan alanlar "yok" veya "bilinmiyor" olarak işaretlenmelidir; alan silinmez.

```
BAŞLIK: [TASLAK] kanal-adi — Yeni | Revizyon | Koleksiyon Kaydı

**Kanal / Kayıt:** kanal-adi (veya forum-adi > Kayıt Adı)
**Taslak türü:** Yeni kanal / Tam revizyon / Koleksiyon kaydı
**Derinlik sınıfı:** Büyük (8–12) / Orta (4–7) / Dar (2–4)
**Mesaj sayısı:** 
**Yazar:** @kullanici
**Sürüm:** v1
**Açılış tarihi:** GG.AA.YYYY

**Özet (2–3 cümle):**

**Kullanılan birincil kaynaklar:**
- *Eser — Yazar*
- *Codex: X — Edition (doğrulandıysa)*

**Kanon notları:**
- Evren-içi iddia olarak işaretlenen noktalar:
- Kaynaklar arası çelişkiler:
- Bilerek boş bırakılan / açıklanmamış noktalar:

**Retcon / eski lore uyarısı:** yok / var (açıklama)
**Çapraz kanallar:** `kanal`, `kanal`
**Karakter denetimi (validate.py):** OK / HATA
**Metin:** (ek dosya veya aşağıdaki yanıtlar)
```
---MSG---
## Forum Etiketleri ve Taslak Yaşam Döngüsü

Forum etiketleri iki aileye ayrılır. **Durum etiketleri** taslağın iş akışındaki yerini, **kanon etiketleri** ise içerikte işaretlenmiş sorunları gösterir. Bir taslak aynı anda yalnızca bir durum etiketi, ancak birden fazla kanon etiketi taşıyabilir.

**Durum etiketleri** (ayrıntı: `yayin-kuyrugu`)
Hazır · Kaynak Bekliyor · Kanon Kontrolünde · Revizyon Gerekli · Yayına Hazır

**Kanon etiketleri** (ayrıntı: `kanon-kontrol`)
Doğrulandı · Kaynak Gerekli · Kaynaklar Çelişiyor · Eski Lore · Retcon Şüphesi · Fan Teorisi · Kanon Dışı · Evren-İçi İddia

**Yaşam döngüsü**
1. Yazar şablonla taslağı açar; durum: **Hazır**.
2. Kaynak denetçisi `kaynak-kontrol` listesini uygular; eksik varsa **Kaynak Bekliyor**.
3. Kanon denetçisi metni etiketler; durum: **Kanon Kontrolünde**.
4. Düzeltme gerekiyorsa **Revizyon Gerekli**; yazar yeni sürümü (v2, v3...) aynı başlıkta paylaşır.
5. Tüm denetimler geçildiğinde **Yayına Hazır**; yayın sonrası başlık kilitlenir, arşivlenir ve işlem `degisiklik-gunlugu` ile `bot-log`'a kaydedilir.

**Arşivleme:** Yayımlanan veya reddedilen taslaklar silinmez. Reddedilen taslağın son yanıtına red gerekçesi yazılır ve başlık kapatılır; aynı konu yeniden açılırsa eski başlığa bağlantı verilir.
