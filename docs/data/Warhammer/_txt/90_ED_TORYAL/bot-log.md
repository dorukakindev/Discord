-# THE IMPERIAL ARCHIVE
# Bot Log

## Bot Log — Kanal Açıklaması

Bu kanal, arşivin otomatik süreçlerinin ve editör işlemlerinin makine tarafından okunabilir kaydıdır. Buraya yalnızca bot veya editörler, aşağıdaki standart biçimde yazar; sohbet, tartışma ve yorum yapılmaz. İnsan tarafından okunacak ayrıntılı değişiklik gerekçeleri <#1551588115540480020>nda tutulur; bot-log ise yalnızca olayın ne zaman, kim tarafından ve hangi nesne üzerinde gerçekleştiğini kısa satırlarla kaydeder.

**Kaydedilen olaylar**
- `DRAFT_OPEN` — taslak-kuyrugunda yeni taslak açıldı
- `DRAFT_VERSION` — taslağa yeni sürüm yüklendi
- `STATUS_CHANGE` — <#1551588112768045067> durum geçişi
- `TAG_ADD` / `TAG_REMOVE` — kanon etiketi eklendi veya kaldırıldı
- `VALIDATE` — validate.py denetimi çalıştırıldı
- `SOURCE_CHECK` / `CANON_CHECK` — denetim sonucu girildi
- `PUBLISH` — metin kanala yayımlandı
- `EDIT` — yayımlanmış mesaj düzenlendi
- `CHANGELOG` — <#1551588115540480020>na kayıt eklendi
- `ARCHIVE` — taslak arşivlendi veya reddedildi
- `ERROR` — otomatik işlem başarısız oldu
- `CORRECTION` — hatalı bir log satırı düzeltildi

**Kurallar**
- Her olay tek satırdır; çok satırlı açıklama gerekiyorsa ilgili kayıt numarasına bağlantı verilir.
- Kayıtlar silinmez ve düzenlenmez. Hatalı kayıt, `CORRECTION` olayıyla düzeltilir.
- Tarih ve saat ISO 8601 biçiminde ve UTC olarak yazılır.
- Kullanıcılar Discord kullanıcı adıyla değil, sunucu içi kısa editör kodu veya bot adıyla gösterilir.

---

## Log Satırı Biçimi

**Standart biçim**
```
[YYYY-MM-DDTHH:MM:SSZ] OLAY | kanal-adi | sürüm | aktör | ayrıntı | ref
```

- **OLAY:** Yukarıdaki olay kodlarından biri.
- **kanal-adi:** Etkilenen kanal veya `forum>kayit-adi`.
- **sürüm:** v1, v2... Yayımlanmış metin için live.
- **aktör:** Editör kodu veya bot adı.
- **ayrıntı:** Kısa, sabit sözdizimli açıklama (aşağıdaki örneklere bakın).
- **ref:** Varsa değişiklik günlüğü kayıt numarası veya taslak kimliği; yoksa -.

**Örnek satırlar (biçim örneğidir)**
```
[2026-09-21T10:02:11Z] DRAFT_OPEN | kanal-adi | v1 | ED-03 | tur=Yeni derinlik=Orta | T-0142
[2026-09-21T10:03:40Z] VALIDATE | kanal-adi | v1 | archive-bot | sonuc=OK mesaj=6 | T-0142
[2026-09-21T11:15:02Z] SOURCE_CHECK | kanal-adi | v1 | ED-05 | sonuc=KAYNAK_BEKLIYOR eksik=2 | T-0142
[2026-09-21T11:15:03Z] STATUS_CHANGE | kanal-adi | v1 | ED-05 | Hazir>Kaynak_Bekliyor | T-0142
[2026-09-21T14:40:27Z] DRAFT_VERSION | kanal-adi | v2 | ED-03 | onceki=v1 | T-0142
[2026-09-21T15:02:19Z] TAG_ADD | kanal-adi | v2 | ED-07 | etiket=Evren-Ici_Iddia msg=3 | T-0142
[2026-09-21T15:30:55Z] STATUS_CHANGE | kanal-adi | v2 | ED-07 | Kanon_Kontrolunde>Yayina_Hazir | T-0142
[2026-09-21T16:05:12Z] PUBLISH | kanal-adi | live | archive-bot | mesaj=6 | DG-2026-001
[2026-09-21T16:07:44Z] CHANGELOG | kanal-adi | live | ED-01 | tur=Yeni | DG-2026-001
```

---

## Değer Sözlüğü ve Hata Kayıtları

**Değer sözlüğü**
Durum değerleri: `Hazir`, `Kaynak_Bekliyor`, `Kanon_Kontrolunde`, `Revizyon_Gerekli`, `Yayina_Hazir`. Etiket değerleri: `Dogrulandi`, `Kaynak_Gerekli`, `Kaynaklar_Celisiyor`, `Eski_Lore`, `Retcon_Suphesi`, `Fan_Teorisi`, `Kanon_Disi`, `Evren-Ici_Iddia`. Değerlerde boşluk ve Türkçe karakter kullanılmaz; bu, logların otomatik olarak aranabilmesini ve ayrıştırılabilmesini sağlar.

**Hata ve düzeltme kayıtları**
Otomatik bir işlem başarısız olduğunda bot `ERROR` satırı yazar ve işlemi durdurur; yayın, hata giderilip `VALIDATE` yeniden `sonuc=OK` verene dek yapılmaz. Yanlış girilmiş bir satır silinmez, onu işaret eden bir `CORRECTION` satırıyla düzeltilir.
```
[2026-09-21T09:40:12Z] ERROR | kanal-adi | v1 | archive-bot | validate=HATA msg=4 karakter>1800 | T-0143
[2026-09-21T09:52:30Z] CORRECTION | kanal-adi | v1 | ED-01 | hatali_satir=2026-09-21T09:31:05Z neden=yanlis_surum | T-0143
```

**Saklama**
Bot-log kayıtları kalıcıdır. Kanal kalabalıklaştığında editörler dönemsel özet sabitler; eski satırlar yerinde kalır ve arama için kullanılmaya devam eder.

---

This channel has been set up to receive official Discord announcements for admins and moderators of Community servers. We'll let you know about important updates, such as new moderation features or changes to your server's eligibility for Server Discovery, here.

You can change which channel these messages are sent to at any time inside Server Settings. We recommend choosing your staff channel, as some information may be sensitive to your server.

Thanks for choosing Discord as the place to build your community!