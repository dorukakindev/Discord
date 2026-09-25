# Lexicanum Bot — Hata Raporu ve Düzeltme Planı

- **Tarih:** 2026-09-24
- **Kapsam:** `bot/` klasöründeki tüm Python kodu (`lexicanum.py`, `build_index.py`, `filmarchive/*`, `wh40k/*`) ve yapılandırma dosyaları
- **Yöntem:** Tüm kaynak kod satır satır okundu; `data/index.json` (5.807 kayıt) ve repodaki canlı döküm dosyaları (`FilmArchive/forumlar/...`) ile bulgular doğrulandı; kod üzerinde **hiçbir değişiklik yapılmadı**.
- **Önem ölçeği:** 🔴 Kritik (veri kaybı / temel işlev bozuk) · 🟠 Yüksek · 🟡 Orta · ⚪ Düşük

---

## 1. Yönetici Özeti

| ID | Önem | Konum | Özet |
|----|------|-------|------|
| C1 | 🔴 | `lexicanum.py:30-32` | Arama normalizasyonu `ı` harfini tamamen siliyor — 901 kayıt (`%15,5`) `ı`-yazılan sorguyla bulunamıyor |
| C2 | 🔴 | `lexicanum.py:188-229` | `/kayit-duzenle` uzun kayıtlarda içerik kaybediyor, eski mesajları silmiyor, afiş satırını siliyor |
| C3 | 🔴 | `build_server.py:729-735, 816-830` | `run_bands`/`run_split` tanınmayan thread'leri içeren forumu yine de siliyor — kalıcı veri kaybı riski |
| C4 | 🔴 | `build_server.py:887-908` | `run_relabel` 50+ mesajlı thread'lerde yanlış pencereyle karşılaştırma → toplu PATCH/silme |
| H1 | 🟠 | `lexicanum.py:17`, `build_index.py:7` | README'deki yerel çalıştırma talimatı çalışmıyor: `.env` hiçbir yerde yüklenmiyor |
| H2 | 🟠 | `lexicanum.py:119-120` | DM'de yönetici komutları `AttributeError` ile çöküyor |
| H3 | 🟠 | `build_index.py:14-28` | `req()` None dönebiliyor → çökme; hatalı tarama iyi indeksin üstüne yazıyor |
| H4 | 🟠 | `build_index.py:44, 57` | Aynı adlı thread'ler aynı guild içinde birbirinin üzerine yazılıyor |
| H5 | 🟠 | `wh40k/dapi.py:9-25` | `req()` ağ hatasına karşı korumasız; filmarchive kopyasıyla ayrışmış durumda |
| H6 | 🟠 | `build_server.py:279, 418-431` | Bant dizin satırları fazladan `**` ile bitiyor (canlı sunucuda doğrulandı) |
| H7 | 🟠 | `dump_all.py` (iki kopya) | Döküm thread başına son 100, metin kanalı başına son 500 mesajla sınırlı — sessiz veri kaybı |
| H8 | 🟠 | `dump_all.py` (iki kopya) | Kategori/forum adları sanitize edilmeden klasör adı oluyor; repoda Windows'ta klonlanamayan yol üretti |
| M1-M12 | 🟡 | bkz. §3 | Orta önemli 12 bulgu |
| L1-L13 | ⚪ | bkz. §3 | Düşük önemli 13 bulgu |

---

## 2. Kritik Bulgular

### C1 — Arama normalizasyonu `ı` harfini tamamen siliyor

**Konum:** `lexicanum.py:30-32`

```python
def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', s.lower()).split())
```

**Sorun:** `ç ğ ö ş ü İ` gibi Türkçe harfler NFKD ile Latin temel harflerine doğru ayrışıyor; ancak **`ı` (U+0131, noktasız i) NFKD ayrışmasına sahip değil** ve `encode('ascii','ignore')` bu harfi sessizce atıyor. Kod üzerinde doğrulanan örnekler:

- `"Sadık"` → `"sadk"` · `"Açıklaması"` → `"acklamas"` · `"Işın"` → `"isn"` (ı siliniyor)
- Kullanıcı ASCII yazdığında: `"sadik"` → `"sadik"` ≠ `"sadk"` → **eşleşme yok**. (`"kagit"` ≠ `"kagt"`, `"isin"` ≠ `"isn"`.)

**Etki (ölçüldü):** `data/index.json`'daki 5.807 başlığın **901'i (%15,5)** `ı` harfi içeriyor. Bu kayıtlar, kullanıcı sorguda `ı` yerine `i` yazdığında `/ara`'da ve `/kayit-duzenle` kayıt oto-tamamlamasında (`kayit_ac`, `lexicanum.py:180-183` aynı `norm`'u kullanır) bulunamıyor. Türkçe bir arşivde günlük yaşanacak bir arama hatası.

**Düzeltme önerisi:** NFKD'den *önce* basit bir transliterasyon uygula:

```python
_TR = str.maketrans({'ç':'c','Ç':'c','ğ':'g','Ğ':'g','ı':'i','İ':'i',
                     'ö':'o','Ö':'o','ş':'s','Ş':'s','ü':'u','Ü':'u'})
def norm(s):
    s = s.translate(_TR)
    s = unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode()
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', s.lower()).split())
```

Birim testleri: `norm("sadik") == norm("Sadık")`, `norm("isin") == norm("Işın")`, `norm("kagit") == norm("Kağıt")`.

---

### C2 — `/kayit-duzenle` uzun kayıtları bozuyor ve afiş satırını siliyor

**Konum:** `lexicanum.py:188-229` (`DuzenleModal`, `kayit_duzel`)

**Sorun — üç ayrı kusur bir arada:**

1. **Modal yalnız starter mesajı gösteriyor** (`lexicanum.py:226`, `194`): `old = msg.content` yalnızca ilk mesajdır (Discord mesaj sınırı 2000). `KayitModal` kaydı 2000'lik parçalara bölerek açtığından (`lexicanum.py:148-151`), devam mesajları modalda **görünmez**.
2. **Eski devam mesajları silinmiyor** (`lexicanum.py:197-209`): Kaydedince starter düzenleniyor ve `rest` için **tek yeni** mesaj ekleniyor (`rest[:2000]`); eski devam mesajları thread'de kalıyor → kayıtta hem yinelenen hem çelişen içerik birikiyor.
3. **`http` ile başlayan ilk satır sessizce atılıyor** (`lexicanum.py:227-228`): `build_server.py`'nin ürettiği film kartlarında ilk satır **afiş URL'sidir** (`film_messages`, `card.append(f["_poster"])`). `/kayit-duzenle` bu kartı kaydettiğinde afiş satırı kalıcı olarak silinir. Tek satırlık URL'den oluşan bir kayıt ise tamamen boşaltılır (`old=''`).

**Etki:** 4000+ karakterlik analiz içeren kayıtların tamamı ve posterli film kartları düzenlemeyle bozulur.

**Düzeltme önerisi:**
- `kayit_duzel`'de thread'teki **tüm** mesajları topla (`channel_messages` benzeri sayfalama ile; starter `thread.fetch_message(thread.id)` — bu repoda starter id == thread id olduğu biliniyor, `build_server.py:880`'deki yorumla teyitli).
- Modal default olarak birleştirilmiş tam metni versin (4000 karakter üstü için modal sınırı aşıldığında uyarı göster; fazlası için çok adımlı akış veya "ilk N karakter düzenlenir" politikası).
- `on_submit` yeni gövdeyi 2000'lik parçalara bölüp **fazla eski mesajları silsin** (`run_relabel`'daki `sync_thread` mantığı zaten hazır bir referans).
- `old.startswith('http')` sezgisini kaldır; afiş satırı korunmalı.

---

### C3 — `run_bands`/`run_split` tanınmayan thread'i olan forumu yine de siliyor

**Konum:** `build_server.py:726-735` (`run_bands`), `807-830` (`run_split`)

```python
if f is None:
    print("!! bilinmeyen thread:", tid, t["name"], flush=True)
    continue          # <-- thread atlanıyor...
...
delete(f"/channels/{fid}")   # <-- ama forum (atlanan thread'leriyle) siliniyor
```

**Sorun:** State haritasında (`post_state.json`) olmayan her thread — elle açılmış kayıt, state dosyası kaybolmuş/kopyalanmamış, `done` anahtar formatı değişmiş — "bilinmeyen" sayılıp atlanıyor; ardından forum komple siliniyor. Discord'da forum silinmesi thread'lerin **kalıcı silinmesi** demek.

**Etki:** Tekrarlanabilir, geri alınamaz veri kaybı. `post_state.json` kaybolursa (work/ dizini silinirse) tüm arşiv tehlikeye girer.

**Düzeltme önerisi:** Bilinmeyen thread sayısı > 0 ise o forum için `delete`'yi durdur ve kullanıcıdan onay iste (ör. `--force` bayrağı); taşınan her thread için eski thread'i yalnızca yenisinin başarıyla açıldığı **onaylandıktan sonra** sil (mevcut kod bunu yapıyor ama forum silme kısmı koşulsuz).

---

### C4 — `run_relabel` 50+ mesajlı thread'lerde yanlış pencereyle hizalanıyor

**Konum:** `build_server.py:887-908`

```python
cur = channel_messages(tid, limit=50)   # en YENİ 50 mesaj
cur.reverse()
for i, m in enumerate(cur):            # cur[0] starter sanılıyor
    ...
    if i >= len(msgs): delete(...)      # "fazla" mesajlar siliniyor
```

**Sorun:** `channel_messages` (`filmarchive/dapi.py:45-56`) Discord API'sinde olduğu gibi **yeniden eskiye** sayfalama yapar; yani `limit=50` çağrısı thread'in en yeni 50 mesajını döndürür. `cur.reverse()` sonrası `cur[0]` thread'in **gerçek starter'ı değildir** — mesaj #N-49'dur. `sync_thread`, `cur[i]` ile `msgs[i]`'yi (üretilecek içerik) birebir hizaladığından 50+ mesajlı bir thread'de:

- yanlış mesajların içeriği değiştirilir (toplu PATCH),
- "fazla" sayılan eski mesajlar **silinir**,
- eksik kalan yeni mesajlar kuyruğa **eklenir**.

**Etki:** Mevcut dizinler ~20 mesajda kaldığı için henüz tetiklenmedi, ama arşiv büyüdükçe sessiz, geniş çaplı içerik bozulması üretir. 50 × 1950 karakter ≈ 97.500 karakter ≈ ~1.500 dizin satırı — büyük bantlar (ör. `filmler-3-5-alti`) bu sınırı aşabilir.

**Düzeltme önerisi:** `channel_messages`'ı `before` sayfalamasıyla tam geçmiş için kullan (limit'i 50 yerine tüm mesajlar yap) veya hizalamayı mesaj **id**'si üzerinden yap (starter id == thread id kuralı).

---

## 3. Yüksek ve Orta Bulgular

### H1 — README'deki yerel çalıştırma talimatı çalışmıyor

**Konum:** `lexicanum.py:17`, `build_index.py:7`, `requirements.txt`, `README.md`

`TOKEN = os.environ['DISCORD_TOKEN']` doğrudan ortam değişkeni okuyor; kodda `load_dotenv` yok, `requirements.txt`'de `python-dotenv` yok. README ise "`cp .env.example .env`" diyip `python3 lexicanum.py` çalıştırıyor → `KeyError: 'DISCORD_TOKEN'`. Üretim `systemd` `EnvironmentFile` ile çalıştığı için hata yalnızca yerel kurulumda patlıyor.

**Düzeltme:** `python-dotenv` bağımlılığa ekle + `lexicanum.py`/`build_index.py` başına `load_dotenv()`; ya da README'yi `export DISCORD_TOKEN=...` şekline çevir.

### H2 — DM'de yönetici komutları `AttributeError` veriyor

**Konum:** `lexicanum.py:119-120` (`is_admin`), `165-173`, `215-229`, `232-249`

DM etkileşiminde `inter.user` bir `discord.User`'dır; `guild_permissions` niteliği yoktur → `/kayit-ekle`, `/kayit-duzenle`, `/index-yenile` DM'den çağrılınca `AttributeError` → kullanıcıya "uygulama yanıt vermedi". `kayit_ekle`'de `lexicanum.py:169`'daki `inter.guild.get_channel` de aynı durumda patlar.

**Düzeltme:** Komutlara `@app_commands.guild_only()` + `@app_commands.default_permissions(manage_messages=True)` ekle; `is_admin` içinde `isinstance(inter.user, discord.Member)` kontrolü koy.

### H3 — `build_index.py` hatalarda çöküyor / iyi indeksin üstüne boş indeks yazıyor

**Konum:** `build_index.py:14-28`, `63-76`

- `req()` içindeki 12 deneme de exception atarsa (ağ kesintisi) veya hepsi 429 dönerse fonksiyon **örtük `None** döner → satır 28'de `req(...).json()` → `AttributeError: 'NoneType'` çökmesi.
- `scan()` içinde `r.status_code != 200 → break`: token hatası (401) veya kalıcı hata durumunda guild sessizce **boş** taranmış olur ve `main()` bunu fark etmeden `data/index.json`'ın üstüne yazar → çalışan arama indeksi 0 kayda düşer.

**Düzeltme:** `req` None/429 dönüşünde açık hata fırlatsın; `main()` sonunda toplam kayıt sayısını önceki indeksle karşıştırıp önemli düşüş varsa yazmayı reddetsin; yazma işlemi geçici dosya + `os.replace` ile atomik olsun.

### H4 — Aynı adlı thread'ler birbirinin üzerine yazılıyor

**Konum:** `build_index.py:44, 57` — `out[t['name']] = ...`

Anahtar yalnız başlık. Aynı guild'in farklı forumlarında aynı başlıklı iki kayıttan (ya da aktif/arşiv taraması arasında çakışanlardan) yalnızca biri indekse girer. Mevcut `data/index.json`'da çakışma yok (doğrulandı) ama yapısal risk duruyor.

**Düzeltme:** Anahtarı `(forum_id, thread_id)` yap; `out` değer olarak dict tutulduğu için `out[t['id']] = ...` yeterli.

### H5 — `wh40k/dapi.py` ağ hatasına korumasız; iki `dapi.py` kopyası ayrışmış

**Konum:** `wh40k/dapi.py:9-25` vs `filmarchive/dapi.py:10-32`

`wh40k` sürümünde `S.request` etrafında try/except yok → tek bir `ConnectionError` tüm dökümü çökertir. `filmarchive` sürümünde bu düzeltilmiş; ayrıca arşiv sayfalaması birinde `len(ths) < 100`, diğerinde `has_more` ile yapılmış. Aynı dosyanın korunmuş/korunmus iki kopyası bakım riski.

**Düzeltme:** `filmarchive/dapi.py` sürümünü ortak tek modüle çıkar (`bot/lib/dapi.py`), iki betik onu import etsin.

### H6 — Bant dizin satırları fazladan `**` ile bitiyor (canlıda doğrulandı)

**Konum:** `build_server.py:279` + `418-431`

`index_messages` her satırı `• **{e}**` ile sarıyor; `band_entry` zaten `Başlık** · puanlar` (başlık sonunda `**`) döndürüyor. Birleşince satır `• **Başlık** · puanlar**` oluyor — sonda eşlenmemiş `**`. `index_messages` docstring'i (satır 272-275) hedef çıktıyı sondasız `**`siz tanımlıyor.

**Kanıt:** Repodaki canlı döküm `FilmArchive/forumlar/FİLMLER - filmler-4-5-ve-ustu/Filmler · 4.5 ve Üstü — Kayıt Dizini.md` — her satır `... · uyg 4.7/5**` ile bitiyor. Discord'da satır sonu eşlenmemiş `**` düz metin olarak görünüyor.

**Düzeltme:** `index_messages`'ta saracı `• **{e}` yap (girdi zaten kendi `**`'sini kapatıyor) ya da `band_entry`'den sondaki `**`yi kaldır; ardından `relabel` fazıyla canlı dizin thread'lerini tazele.

### H7 — Dökümler mesaj sayısına üst sınır koyuyor

**Konum:** `filmarchive/dump_all.py:93, 120`; `wh40k/dump_all.py:81, 110`

- Thread'ler için `GET /channels/{tid}/messages?limit=100` — sayfalama yok → 100+ mesajı olan thread'lerde **eski mesajlar döküme girmez** (sessiz veri kaybı).
- Metin kanalları için `channel_messages(c["id"], limit=500)` — son 500 mesajla sınırlı.

**Düzeltme:** Thread mesajlarını da `before` ile sonuna kadar sayfala (yardımcı fonksiyon zaten var); sınır bilinçli tutulacaksa README/kod yorumunda belgele ve döküm özetinde "X mesaj kesildi" uyarısı bas.

### H8 — Kategori/forum adları sanitize edilmeden klasör yolu oluyor

**Konum:** `filmarchive/dump_all.py:86`, `wh40k/dump_all.py:74` — `fdir = f"{cat} - {f['name']}"`

`fsafe()` yalnızca dosya adına uygulanıyor. Discord kategori adları `/` içerebilir; aynı kodu paylaşan döküm ailesi bunu zaten üretti: repodaki `TrenchCrusade/forumlar/40・GELECEK / DUYURULMUŞ LORE - duyurulan-factionlar/...` yolu **Windows'ta klonlamayı engelliyor** (bu analiz sırasında checkout hatası olarak bizzat doğrulandı). Bu betikler Linux'ta çalıştığı için yazma bugün olmuyor; ama repo Windows'ta klonlanamıyor ve tüketen her araç kırılıyor.

**Düzeltme:** `fdir` bileşenlerine de `fsafe()` uygula; repodaki mevcut bozuk yolları yeniden adlandırıp betiği düzelttikten sonra dökümü tazele.

### M1 — `/kayit-ekle` yeni kaydı yalnız belleğe ekliyor (`lexicanum.py:154-157`)

`INDEX.append(...)` diske yazılmıyor → bot yeniden başlayınca yeni kayıt `/ara`'da kaybolur (link Discord'da durur). Düzeltme: append sonrası kilit altında atomik olarak `data/index.json`'a yaz veya ilgili forumu artımlı tara.

### M2 — `/index-yenile` eşzamanlı çalıştırmaya açık (`lexicanum.py:232-249`)

İki yönetici aynı anda çalıştırırsa iki `build_index` aynı dosyaya yazar (yarı yazılmış JSON okuma riski); ayrıca ~10 dk'lık iş 15 dakikalık interaction followup penceresini aşarsa sonuç mesajı sessizce düşer. Düzeltme: `asyncio.Lock`; atomik yaz; bitiş raporu yerine gerektiğinde kanal mesajı.

### M3 — `on_ready` her tam yeniden bağlanmada global `tree.sync()` (`lexicanum.py:281`)

Global komut senkronizasyonu ağır rate-limitlidir; bağlantı kopmalarında tekrar tekrar çalışır. Global sync'in yayına çıkması da ~1 saate kadar sürebilir. Düzeltme: process başına bir kez (modül düzeyi bayrak) veya guild-scoped sync.

### M4 — `run_guide`/`run_az` idempotent değil (`build_server.py:665-682`)

Her çalıştırmada kılavuz ve A-Z indeks mesajlarını yeniden POST ediyor → tekrar çalıştırmada kanallarda kopya birikiyor. (`run_bands`/`run_relabel` karşılaştır-PATCH yapıyor.) Düzeltme: aynı karşılaştır-PATCH/temizle mantığını buraya da uygula.

### M5 — Düzenleme thread'i zorla arşivliyor (`lexicanum.py:200, 206`)

`archived=False` → düzenle → `archived=True`; düzenleme öncesi aktif olan thread arşive itilir. Düzeltme: başlangıç durumunu sakla, geri yükle.

### M6 — Üye log kanalı silinirse `AttributeError` (`lexicanum.py:269, 276`)

`bot.get_channel(int(cid))` None dönebilir (silinen kanal / önbellek yokluğu) → `None.send` hatası; o giriş/çıkış kaydı düşmez. Ayrıca `log_embed`'de `bot.get_guild(member.guild.id)` (satır 259) gereksiz — `member.guild` zaten elde. Düzeltme: kanal None ise uyarı logla ve atla.

### M7 — Embed bağlantı metni markdown injection'a açık (`lexicanum.py:74-75`)

Başlığında `](` veya `*` geçen thread adları embed bağlantısını bozar (Discord thread adları bu karakterlere izin verir). Düzeltme: başlığı kaçır (markdown escape + köşeli parantezleri) — örn. `discord.utils.escape_markdown`.

### M8 — Forum lookup önbellekten (`lexicanum.py:169`, `123-129`)

`get_channel`/`g.channels` bot başlangıcından beri açılan forumları görmez → "Forum bulunamadı" yanlış uyarısı ve oto-tamamlamada eksik liste. Düzeltme: `fetch_channel` / `await inter.guild.fetch_channels()` kullan.

### M9 — Sıralama lambda'ları korumasız `float()` (`build_server.py:572, 745, 840, 921`)

`float(str(f.get("sana_uygunluk") or "0").split("/")[0])` — `"-"` veya `"4,7"` gibi değer `ValueError` fırlatır; `band_of` (satır 404-414) bunu try/except ile korur ama `run_posts`/`run_bands`/`run_split`/`run_relabel`'daki sıralamalar korumasız → tek boş değer tüm fazı çökertir. Düzeltme: `parse_uygunluk(f)` yardımcı fonksiyonu (varsayılan 0.0) ve sıralamalarda onu kullan.

### M10 — Poster önbelleği başarısız sonuçları önbelleğe almıyor (`build_server.py:106-124`)

`if cache.get(key):` — None poster değer kaydedilse de falsy → her tam çalıştırmada TMDB/Letterboxd yeniden taranır (yavaş + rate-limit riski). Ayrıca önbellek diske yalnız her 25 filmde bir yazılır — çökmede kayıp. Düzeltme: `if key in cache:`; yazma sıklığını artır.

### M11 — Her çalıştırmada yeni kalıcı davet üretiliyor (`build_server.py:511-531`)

`siblings_text` her rerun'da 4 guild için `max_age=0, max_uses=0, unique=True` davet açar → davet birikmesi; hedef kanal "ilk metin kanalı" (kural kanalı olabilir). Düzeltme: `GET /guilds/{gid}/invites` ile mevcut daveti bul ve yeniden kullan.

### M12 — `sweep_stale` koşulsuz siliyor (`filmarchive/dump_all.py:75-82`, `wh40k/dump_all.py:63-70`)

API bir forum için geçici olarak boş liste döndürürse o forumun tüm `.md` dosyaları "stale" sayılıp kalıcı silinir. Düzeltme: silinecek dosya oranı eşiği (ör. %30 üstünde dur), `--dry-run` bayrağı ve/veya silmek yerine `.trash/` dizinine taşıma.

---

## 4. Düşük Bulgular

| ID | Konum | Bulgu |
|----|-------|-------|
| L1 | `lexicanum.py:288` | `bot.run(TOKEN)` `if __name__ == '__main__'` korumasız — modül importu botu başlatır |
| L2 | `lexicanum.py` (genel) | `tree.on_error` tanımsız — beklenmeyen hatalarda kullanıcıya hiçbir açıklama gitmez |
| L3 | `lexicanum.py:105` | `random.choice(pool)` — boş havuzda (index.json yok / 0 kayıtlı sunucu filtresi) `IndexError` |
| L4 | `lexicanum.py:169` | `int(forum)` — kullanıcı elle sayı dışı değer girerse `ValueError`; try/except eksik |
| L5 | `wh40k/dump_all.py:124-129` | `docs/manifest.json` güncellemesi düğüm yoksa sessizce hiçbir şey yapmaz (filmarchive sürümü düğüm açar); manifest konumları da farklı (`REPO/server_manifest.json` vs `FILM/server_manifest.json`) |
| L6 | `dsan()` (iki döküm) | Farklı Unicode adlar aynı `_` dizisine düşebilir → sessiz üzerine yazma; çakışma durumuna kısa hash eki eklenebilir |
| L7 | `bot/idx2.log`, `README.md` | Bayat/üretilmiş dosyalar repoda: `idx2.log` (bayat log), `data/index.json` (1,2 MB yeniden üretilebilir artefakt); README'deki "3.957 kayıt" sayısı bayat (gerçek: 5.807) |
| L8 | `lexicanum.py:145-149` | Boş kayıt adı → `create_thread` 400 → genel "Hata:" mesajı; isim doğrulaması daha iyi UX olur |
| L9 | `build_server.py:70-103` | Afiş çözümleme HTML scrape'e bağlı: `og:image` + `w500` regex'i kırılgan (TMDB boyut değiştirirse miss); attribute sırasına duyarlı. TMDB API anahtarıyla resmi API daha sağlam |
| L10 | `build_server.py:241-251` | `line_chunks`: ilk satır limiti aşarsa listeye boş "" parçası girer → boş mesaj POST → 400 → `RuntimeError` (ender) |
| L11 | `requirements.txt` | Sürümler yalnız `>=` ile sabitlenmiş (üst sınır yok); `python-dotenv` eksik (H1 ile bağlantılı) |
| L12 | `systemd/lexicanum.service` | Sertleştirme yok: `NoNewPrivileges`, `ProtectSystem=strict`, `PrivateTmp`, `ReadWritePaths=/opt/lexicanum/data` eklenebilir |
| L13 | `lexicanum.py:91` | Çok uzun `sorgu` embed başlık sınırını (256) aşabilir → 400; girdi uzunluğu kısıtlanmalı |

Ayrıca **test/CI yok**: `norm`, `search`, `chunks`, `line_chunks`, `band_of` saf fonksiyonlar ve kolayca birim test edilebilir.

---

## 5. Geliştirme Önerileri (hata olmayanlar)

1. **Arama UX** — sonuç sayfalama butonları (`discord.ui.View`), toplam eşleşme sayısı ("10/37 sonuç gösteriliyor"), isteğe bağlı `ephemeral` bayrağı; eşleşme yokken "bunu mu demek istediniz?" önerisi (basit edit-distance).
2. **İndeks altyapısı** — `index.json` yerine SQLite + FTS5 (Türkçe normalizasyonu uygulanmış sanal kolonla): 5.807 kayıtta milisaniye aramalar, `/index-yenile`'i guild başına artımlı hale getirme, `kayit-ekle`'de otomatik kalıcılık.
3. **`/kayit-duzenle` UX** — 4000 karakter modal sınırı uzun analizler için yetersiz; tam metni ephemeral mesajla gösterip düzenlemeyi çok adımlı yapmak ya da "kaynağı dosyadan güncelle" akışı.
4. **Kod organizasyonu** — `lexicanum.py` tek dosya (288 satır) ve komut/event/modal iç içe; `search.py` / `commands/` / `logging.py` olarak ayırmak test edilebilirliği artırır. İki `dapi.py` kopyası tek `bot/lib/` modülünde birleşmeli (H5).
5. **Gözlemlenebilirlik** — `print` yerine `logging` (systemd journal'unda seviyeler); `/index-yenile` ilerleme yüzdesi (followup düzenleme), `/saglik` tanılama komutu (indeks yaşı, kayıt sayıları, eksik sunucular).
6. **CI** — GitHub Actions: `ruff check` + `python -m compileall` + pytest (özellikle C1 düzeltmesinin gerileme testleri) + secret taraması.
7. **Repo hijyeni** — `idx2.log` ve (tercihe göre) `data/index.json` `.gitignore`'a; `.gitignore`'a `work/` ekle (poster/state dosyaları). (Repo kökündeki yüzlerce dağınık `.md` bu raporun kapsamı dışında ama bir arada değinildi.)
8. **Doküman** — README'ye `/kayit-duzenle`'nin 4000 karakter sınırı notu; güncel kayıt sayıları; döküm betiklerinin mesaj sınırları (H7) düzeltülünce kaldırılacak not.

---

## 6. Düzeltme Planı

> Sıralama: önce veri kaybı/temel işlev, sonra sağlamlık, sonra kalite. Her faz sonunda doğrulama adımı tanımlıdır. Kod bu raporda değiştirilmedi — aşağıdaki plan uygulama içindir.

### Faz 1 — Kritik (hedef: 0,5 gün)

| # | İş | Dosya | Kabul kriteri |
|---|----|-------|---------------|
| 1.1 | `norm()` Türkçe transliterasyon (C1) | `lexicanum.py` | `"sadik"`→`"Sadık"`, `"isin"`→`"Işın"`, `"kagit"`→`"Kağıt"` eşleşiyor; eski davranış testleriyle karşılaştırılıyor |
| 1.2 | `/kayit-duzenle` tam metin toplama + fazla mesaj silme + http-strip kaldırma (C2) | `lexicanum.py` | Çok mesajlı kayıt düzenlendiğinde thread'de yalnız yeni mesajlar var; afişli kart düzenlendiğinde afiş satırı korunuyor |
| 1.3 | `run_bands`/`run_split` bilinmeyen thread'te silmeyi durdur (C3) | `build_server.py` | Bilinmeyen thread varsa forum silinmiyor, uyarı basılıyor |
| 1.4 | `run_relabel` tam mesaj sayfalaması (C4) | `build_server.py` | 60+ mesajlı sahte thread ile test: hiçbir mesaj yanlış PATCH'lenmiyor/silinmiyor |

**Doğrulama:** `python -m compileall`, yeni birim testler (`norm`, düzenleme akışı sahte thread ile), canlı sunucuda önce yedek alınarak kuru çalıştırma.

### Faz 2 — Yüksek (hedef: 1 gün)

| # | İş | Dosya |
|---|----|-------|
| 2.1 | `.env` yükleme veya README düzeltmesi (H1) | `lexicanum.py`, `build_index.py`, `requirements.txt` |
| 2.2 | `guild_only` + `default_permissions` + DM koruması (H2) | `lexicanum.py` |
| 2.3 | `build_index`: None kontrolü, hata fırlatma, atomik yaz, sayı sanity kontrolü (H3) | `build_index.py` |
| 2.4 | İndeks anahtarını thread id'ye çevir (H4) | `build_index.py` |
| 2.5 | `dapi.py` birleştirme + ağ koruması (H5) | `filmarchive/dapi.py`, `wh40k/dapi.py` → ortak modül |
| 2.6 | Dizin `**` düzeltmesi + `relabel` ile canlı dizin tazeleme (H6) | `build_server.py` |
| 2.7 | Döküm mesaj sayfalaması (H7) | iki `dump_all.py` |
| 2.8 | `fdir` sanitize + repodaki bozuk yolların düzeltilmesi (H8) | iki `dump_all.py` + repo yolları |

### Faz 3 — Orta (hedef: 1 gün)

- 3.1 M1 + M2 (kalıcı/artımlı indeks, kilit, atomik yaz)
- 3.2 M3 (tek seferlik sync), M4 (idempotent guide/az), M5, M6, M7, M8
- 3.3 M9 (`parse_uygunluk`), M10 (poster önbelleği), M11 (davet yeniden kullanımı), M12 (sweep eşiği/dry-run)

### Faz 4 — Düşük + kalite (hedef: 0,5 gün)

- 4.1 L1-L13 sırasıyla; `tree.on_error` ve girdi doğrulamaları öncelikli
- 4.2 CI: ruff + pytest + compileall (öneri 5.6)
- 4.3 Dokümantasyon ve repo hijyeni (öneri 7-8): README sayıları, `idx2.log` kaldırma, `.gitignore` güncellemesi
- 4.4 (Opsiyonel, ayrı iş) SQLite FTS5 geçişi ve komut modülerizasyonu (öneri 2, 4)

**Genel doğrulama (her faz):** birim testler → `python -m compileall` → canlı olmayan test sunucusunda el ile senaryolar → (varsa) döküm betikleri için kuru çalıştırma + diff incelemesi → yedek alındıktan sonra canlıya al.

---

*Rapor, `bot/` klasörünün 2026-09-24 tarihli `main` dalındaki hâli üzerine hazırlanmıştır (HEAD: `2a08f327`). Kod değiştirilmemiştir; tüm bulgular salt-okunur analiz ve repodaki canlı döküm verileriyle doğrulanmıştır.*
