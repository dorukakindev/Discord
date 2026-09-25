# Lexicanum / Arşiv Ailesi — Derinlemesine İnceleme ve Geliştirme Planı

- **Tarih:** 2026-09-25
- **Kapsam:** `bot/` altındaki tüm Python kodu (`lexicanum.py`, `build_index.py`, `filmarchive/{build_server,dapi,dump_all}.py`, `wh40k/{dapi,dump_all}.py`), yapılandırma (`requirements.txt`, `systemd/`, `.env.example`, `data/`), repo düzeni ve canlı döküm çıktıları
- **Yöntem:** HEAD `9798d336` (main) üzerinde tüm dosyalar satır satır okundu; önceki raporun (`bug-raporu-ve-duzeltme-plani.md`, HEAD `3c08d9d1`) her bulgusu güncel kodla karşılaştırıldı; iddialar `python -m compileall`, `index.json` verisi ve Windows ortamında canlı denemelerle doğrulandı. **Kod üzerinde hiçbir değişiklik yapılmadı** — bu dosya raporun tek artefaktıdır.
- **Önem ölçeği:** 🔴 Kritik (veri kaybı / temel işlev bozuk) · 🟠 Yüksek · 🟡 Orta · ⚪ Düşük

---

## 1. Yönetici Özeti

Proje, 5 salt-okunur Discord arşiv sunucusunu (Imperial/WH40K, Trench, Black RPG, Codex Mythica, Film Archive) tek `Lexicanum` botuyla yöneten küçük ama işlevsel bir sistem: forum tabanlı kayıtlar, REST döküm betikleri, SQLite→Discord sunucu kurucusu ve statik docs görüntüleyici.

**Durum:** Önceki hata raporunun **37 bulgusunun 17'si tamamen, 2'si kısmen** kapatılmış (`#12`, `#13` PR'ları): Türkçe `ı` araması, `/kayit-duzenle` veri kaybı, `.env` yükleme, DM çökmesi, indeks kilidi/atomik yazma/%90 koruyucu, thread event-senkronizasyonu, `tree.on_error`, systemd sertleştirme ve bağımlılık üst sınırları — hepsi çözülmüş ve kod kalitesi gözle görülür artmış.

**Ancak:** veri kaybı riski taşıyan iki kritik bulgu (**C3**, **C4**) dahil 13 bulgu hâlâ açık; hepsi `build_server.py` ve `dump_all.py` tarafında — yani bot değil, **arşivi kuran/dökümleyen betikler**. Ayrıca bu incelemede **16 yeni bulgu** çıktı; en dikkat çekicileri: `all` fazının taze kurulumda çökmesi (N1), `/kayit-duzenle`'nin yeni düzeltmesinde paragraf yapıştırma kenar durumu (N2), `INDEX.append` yarışıyla çift kayıt olasılığı (N3) ve `encoding` belirtilmeyen `open()` çağrılarının Windows'ta çökmesi (N6 — bu makinede canlı doğrulandı).

**Öncelik:** Faz A'daki 4 iş (C3, C4, M12, N1) tek seferde ~yarım gün; hepsi "silmeden önce dur" kuralı. Sonra döküm bütünlüğü (Faz B), bot sağlamlığı (Faz C), içerik kalitesi (Faz D), altyapı/CI (Faz E) ve repo hijyeni (Faz F).

---

## 2. Proje Haritası

```
nMDB SQLite ──> build_server.py (fazlar: prep→structure→guide→posts→az + migrasyonlar bands/split/relabel)
                        │  Film Archive forumlarını kurar, poster çözer, dizinler yazar
                        ▼
5 Discord guild ──> build_index.py (REST tarama) ──> data/index.json (5.807 kayıt)
       │  ▲                                              │
       │  └── lexicanum.py: /ara /rastgele /istatistik    │ arama + fuzzy (rapidfuzz)
       │      /kayit-ekle /kayit-duzenle /index-yenile    │
       │      thread event'leriyle canlı indeks senkronu ──┘
       └──> wh40k/dump_all.py + filmarchive/dump_all.py ──> <Arşiv>/forumlar/*.md + docs/data/*
                                                             docs/index.json + manifest.json
                                                             (statik viewer index.html — repoda YOK, bkz. N11)
```

| Bileşen | Satır | Rol |
|---|---|---|
| `lexicanum.py` | 457 | Discord bot: arama, rastgele, istatistik, kayıt ekle/düzenle, index-yenile, üye logu, thread→indeks senkronu |
| `build_index.py` | 95 | Tüm forumların aktif+arşiv thread'lerini tarar → `data/index.json` (atomik yaz + %90 koruma) |
| `filmarchive/build_server.py` | 967 | nMDB veritabanlarından Film Archive sunucusunu kurar/günceller; faz tabanlı, state'li, kısmen idempotent |
| `filmarchive/dapi.py` / `wh40k/dapi.py` | 80/70 | Discord REST yardımcıları — **iki ayrışmış kopya** (H5 açık) |
| `*/dump_all.py` | 160/139 | Guild → repo `.md` dökümü + docs manifest/index senkronu |

**Veri durumu (ölçüldü):** `index.json` = 5.807 kayıt → Mythica 2.272 · Imperial 1.761 · BlackRPG 838 · Film 648 · Trench 288. Repo genelinde ~14.000 dosya; `docs/` 7.002 dosya ile en büyük pay.

---

## 3. Önceki Raporun Kapanış Durumu

> Doğrulama: her bulgu HEAD `9798d336` koduyla karşılaştırıldı.

| ID | Önem | Durum | Not |
|----|------|-------|-----|
| C1 `ı` araması | 🔴 | ✅ Kapalı | `_TR` transliterasyonu eklendi (`lexicanum.py:51-59`) |
| C2 kayıt-düzenle veri kaybı | 🔴 | ✅ Kapalı | Tam geçmiş + parçalı edit + fazla mesaj silme + arşiv durumu geri yükleme (`242-302`); yeni kenar durumu için bkz. N2 |
| C3 forum silme (bilinmeyen thread) | 🔴 | ❌ **Açık** | `build_server.py:729-735, 816-830` dokunulmamış |
| C4 `run_relabel` 50 mesaj penceresi | 🔴 | ❌ **Açık** | `build_server.py:889` hâlâ `limit=50` en-yeni pencere |
| H1 `.env` yüklenmiyor | 🟠 | ✅ Kapalı | `python-dotenv` + `load_dotenv()` iki betikte de var |
| H2 DM'de AttributeError | 🟠 | ✅ Kapalı | `guild_only` + `isinstance(Member)` kontrolü |
| H3 `req` None / boş indeks yazma | 🟠 | 🟡 Kısmen | `req` artık `RuntimeError` fırlatıyor + atomik yazma + %90 koruma; **ama** forum-bazında 401/403/500 hâlâ sessiz `break` (N14) |
| H4 aynı adlı thread çakışması | 🟠 | ✅ Kapalı | Anahtar `t['id']` oldu (`build_index.py:53,66`) |
| H5 iki `dapi.py` ayrışması | 🟠 | ❌ **Açık** | `wh40k/dapi.py` hâlâ try/except'siz; `forum_threads` sayfalama yöntemleri farklı |
| H6 dizin satırı fazladan `**` | 🟠 | ❌ **Açık** | `index_messages` (`build_server.py:280`) + `band_entry` (`427`) birlikte hâlâ `...**` üretiyor; canlı dizinlerin `relabel` tazelemesi de gerekli |
| H7 döküm mesaj sınırları | 🟠 | ❌ **Açık** | Thread başına 100 / kanal başına 500 üst sınır duruyor |
| H8 `fdir` sanitize edilmiyor | 🟠 | ❌ **Açık** | Kategori/forum adı hâlâ ham klasör yolu; Windows'ta klonlamayı bozan yol repoda duruyor |
| M1 kayıt-ekle kalıcılığı | 🟡 | 🟡 Kısmen | `on_thread_create` event'i artık `save_index()` yapıyor; `on_submit`'in doğrudan `INDEX.append`'i kilit dışı + yarışa açık (N3) |
| M2 eşzamanlı index-yenile | 🟡 | ✅ Kapalı | `INDEX_LOCK` + kilit kontrolü (`312-314`) |
| M3 tekrarlı tree.sync | 🟡 | ✅ Kapalı | `_TREE_SYNCED` bayrağı |
| M4 guide/az idempotent değil | 🟡 | ❌ **Açık** | `run_guide`/`run_az` her koşuda koşulsuz POST → kopya birikimi |
| M5 zorla arşivleme | 🟡 | ✅ Kapalı | `was_archived` geri yükleniyor (`301`) |
| M6 log kanalı None | 🟡 | ✅ Kapalı | `member_log` kontrolü (`406-414`) |
| M7 embed injection | 🟡 | ✅ Kapalı | `escape_markdown` + köşeli parantez kaçışı (`104-110`) |
| M8 forum lookup önbellek | 🟡 | ✅ Kapalı | `fetch_channels`/`fetch_channel` + fallback |
| M9 korumasız `float()` | 🟡 | ❌ **Açık** | 4 sıralama lambdası hâlâ `ValueError`'a açık |
| M10 poster önbelleği falsy | 🟡 | ❌ **Açık** | `cache.get(key)` None'u miss sayıyor |
| M11 davet birikmesi | 🟡 | ❌ **Açık** | Her koşuda yeni kalıcı davet |
| M12 `sweep_stale` koşulsuz | 🟡 | ❌ **Açık** | API boş dönerse tüm `.md`'ler silinir |
| L1 `__main__` koruması | ⚪ | ✅ Kapalı | |
| L2 `tree.on_error` | ⚪ | ✅ Kapalı | `on_app_error` eklendi |
| L3 boş havuz `random.choice` | ⚪ | ✅ Kapalı | `if not pool` kontrolü |
| L4 `int(forum)` ValueError | ⚪ | ✅ Kapalı | except'e eklendi |
| L5 wh40k manifest düğümü | ⚪ | ❌ **Açık** | |
| L6 `dsan` çakışması | ⚪ | ❌ **Açık** | |
| L7 bayat dosyalar | ⚪ | 🟡 Kısmen | `idx2.log` hâlâ repoda; `index.json` commitli artefakt (bilinçli seçim olabilir) |
| L8 boş kayıt adı | ⚪ | ✅ Kapalı | `if not name` kontrolü |
| L9 TMDB scrape kırılgan | ⚪ | ❌ **Açık** | |
| L10 `line_chunks` boş parça | ⚪ | ❌ **Açık** | |
| L11 bağımlılık üst sınırı | ⚪ | ✅ Kapalı | `rapidfuzz<4`, `python-dotenv<2` |
| L12 systemd sertleştirme | ⚪ | ✅ Kapalı | `NoNewPrivileges`, `ProtectSystem=strict` vb. eklendi |
| L13 embed başlık sınırı | ⚪ | ✅ Kapalı | `sorgu[:200]`, `title[:256]` |

**Skor:** 17 ✅ · 2 🟡 · 13 ❌ açık. Açıkların tamamı `build_server.py` + `dump_all.py` + `dapi.py` tarafında.

---

## 4. Yeni Bulgular (bu inceleme)

### N1 — 🟠 `all` fazı taze kurulumda çöküyor

`main()` (`build_server.py:937-963`) `all`'da `bands`→`split`→`relabel`'i de çalıştırır; `run_bands`/`run_split`/`run_relabel` `post_state.json`'u **koşulsuz** `json.load(open(...))` ile açıyor (`693, 783, 884`). `run_posts`'taki `os.path.exists` koruması (`559`) bunlarda yok → taze `work/` dizininde `FileNotFoundError`, `posts` hiç çalışmadan çıkılır. Docstring "Fazlar: ... | all" diyor ama `all` gerçekte "sıfırdan kur" anlamına gelmiyor.

**Düzeltme:** üç fonksiyonda da `state_p` yoksa erken dönüş (migrasyon fazları zaten no-op olmalı), ya da `all` = yalnızca `prep+structure+guide+posts+az` olarak tanımlanmalı; migrasyon fazları ayrı komutlar kalmalı.

### N2 — 🟡 `/kayit-duzenle` paragraf yapıştırması ve tail kenar durumu

İki ayrı kusur (`lexicanum.py:299, 243, 252`):

1. `old = ''.join(m.content for m in msgs)` mesajları **ayraçsız** birleştiriyor. `KayitModal` gövdesi 2000'de kesildiği için bu doğru; ama `build_server.py` `chunks()` paragraf sınırında bölüp her parçayı `rstrip()`liyor → film kaydı düzenlenirken paragraf arası `\n\n`'ler kaybolur, metin yapışır. Tersi de sorunlu: `'\n\n'` ile birleştirilse modal kayıtlarının orta-kelime kesimlerine sahte boş satır girer. Güvenli yol: birleştirmeyi üretim chunker'ının tersi yapmak yerine thread'e `record_format` işareti koymak ya da "mesaj başına" düzenleme akışı.
2. `tail = old[4000:]` + `body.strip() + self.tail` (`252, 300`): modal yalnız ilk 4000 karakteri gösterir; kullanıcı gövdenin sonundaki boşluğu silse bile `tail` orta-kelimeden başlayıp yapışır (`"...kelime " + "ime devam"` → `kelimeime devam`). Ayrıca kullanıcının bilerek sildiği sondaki içerik geri eklenir — sezgisel değil.

### N3 — 🟡 `KayitModal.on_submit` `INDEX.append` kilit dışı + çift kayıt yarışı

`lexicanum.py:199-202` `INDEX.append` `INDEX_LOCK` dışında ve `save_index()` çağırmıyor — kalıcılık `on_thread_create` event'ine emanet. Gateway event'i `create_thread` REST yanıtıyla yarışır: event önce işlenirse `upsert_thread` ekler, ardından `on_submit` **aynı thread'i ikinci kez** ekler → indekste çift kayıt, `/ara`'da yinelenen sonuç (sonraki `upsert` yalnız ilk eşleşmeyi düzeltir). Event kaybolursa kayıt yalnız RAM'de kalır.

**Düzeltme:** `on_submit` içinde `INDEX_LOCK` altında `upsert_thread`'e eşdeğer dedupe-ekleme + `save_index()`; `on_thread_create` zaten idempotent.

### N4 — 🟡 Düzenleme, bot'a ait olmayan mesajlarda kısmen başarısız olur

`DuzenleModal.on_submit` (`lexicanum.py:255-264`) thread'deki **tüm** mesajları sırayla `edit`/`delete`'e tabi tutar. Bot yalnız kendi mesajlarını düzenleyebilir; kayıt thread'inde başka kullanıcı yorumu varsa `msgs[i].edit` → `Forbidden` → döngü ortasında hata → kısmen güncellenmiş kayıt + yorumlar da gövdeye katılmış olur (N2 birleştirme).

**Düzeltme:** düzenleme öncesi `m.author == bot.user` filtresi + yabancı mesaj varsa uyarı; yorumları gövdeye katma.

### N5 — ⚪ `/kayit-duzenle` thread olmayan kanal id'sini kabul ediyor

Autocomplete yalnızca öneridir; kullanıcı keyfi `kayit` değeri girebilir. Sayısal ama thread olmayan bir id `fetch_channel`'dan `TextChannel` döndürür → `th.archived` (`301`) `AttributeError` / `thread.edit(archived=...)` `TypeError` → "Beklenmedik hata". `isinstance(th, discord.Thread)` kontrolü eklenmeli.

### N6 — 🟠 `open()` çağrıları `encoding` belirtmiyor — Windows'ta çökme (canlı doğrulandı)

Tüm dosya G/Ç'si (`load_index`, `save_index`, `GUILDS` yükleme, `build_index` yazma, `dump_all` `w()`) varsayılan kodlamayı kullanır. **Bu makinede doğrulandı:** `json.load(open('data/index.json'))` cp1254 altında `UnicodeDecodeError` veriyor (kategori adlarındaki `・` U+30FB ve Türkçe karakterler). Yani bot bu Windows kutusunda **hiç başlayamaz**; üretim Linux'ta UTF-8 olduğu için görünmez. Geliştirme makinesi Windows olan bir proje için taşınabilirlik hatası.

**Düzeltme:** tüm `open(...)` çağrılarına `encoding='utf-8'` (okuma+yazma); `requirements`/README'ye `PYTHONUTF8=1` notu alternatif ama kodda düzeltmek daha sağlam.

### N7 — ⚪ Ortam değişkeni adları tutarsız

`lexicanum.py`/`build_index.py` → `DISCORD_TOKEN`; `wh40k/dapi.py` → `DISCORD_BOT_TOKEN_WH40K`; `filmarchive/dapi.py` → `DISCORD_BOT_TOKEN_WH40K` **veya** `DISCORD_TOKEN`; `filmarchive` ayrıca `FILM_GUILD_ID` isterken `wh40k` guild id'yi sabitliyor. `.env.example` yalnız `DISCORD_TOKEN`'ı belgeliyor → döküm betikleri taze `.env` ile `KeyError` verir.

### N8 — ⚪ `/ara` "N sonuç" toplam değil, gösterilen sayı

`ara` (`lexicanum.py:125`) `search(..., limit=10)` sonucunun `len`'ini başlığa yazıyor → 500 eşleşmede bile "10 sonuç". Ya `search`'e sayaç döndürülmeli ya da başlık "ilk 10" demeli.

### N9 — ⚪ `forum_thread_in_scope`/`rec_of_thread` önbelleğe bağımlı; `c` alanı hep boş

`bot.get_channel(th.parent_id)` (`349, 369`) önbellekte yoksa thread sessizce indeks dışı kalır (`forum_thread_in_scope` → `False`). Ayrıca event ile eklenen kayıtlarda `'c': ''` → `build_index` kayıtlarıyla şema tutarsızlığı (kategori bilgisi). `fetch_channel` fallback + `parent.parent_id`→kategori çözümü.

### N10 — ⚪ `on_thread_delete` biçimsiz `l` alanında IndexError

`r['l'].rsplit('/', 1)[1]` (`400`) — `l` `/'siz ise `IndexError`. Event handler çökmez ama log kirliliği + silme atlanır. Savunma: `.rsplit('/',1)[-1]` yerine açık `if '/' in r['l']` ya da kayıtlara `id` alanı eklenmesi (daha temiz).

### N11 — 🟡 `docs/` görüntüleyici kaynağı repoda yok

`.agents/skills/testing-discord-archive-guilds/SKILL.md` `docs/index.html` "Lexicanum Arşivleri" viewer'ını anlatıyor ama `docs/` ağacında yalnız `index.json`, `manifest.json`, `data/` var — HTML/JS kaynağı commitlenmemiş (üretilen artefakt mı, kayıp mı belli değil). Viewer repo dışında üretiliyorsa üretecini commitlemek; unutulduysa eklemek gerekir — aksi halde site tek makineye bağımlı.

### N12 — ⚪ `search()` her sorguda 5.807 `norm()` + `set()` yeniden hesaplıyor

`/ara` başına ~60-100 ms saf-Python işi; tek kullanıcılı arşivde sorun değil ama gereksiz. Kayıt yapısına önceden-normalize `n` alanı eklenebilir (`load_index`'de bir kez) — `kayit_ac` de aynı faydayı görür.

### N13 — ⚪ `/index-yenile` followup 15 dakika sınırına takılabilir

İlk yanıt sonrası followup token'ı 15 dk yaşar; tarama README'ye göre ~10 dk — büyüyen arşivde sınır aşılırsa `followup.send` (`331`) `HTTPException` fırlatır, kullanıcı "sonuçsuz kaldı" sanır. Bitişi log kanalına düşmek ya da `inter.edit_original_response` yerine kanala mesaj atmak daha dayanıklı.

### N14 — 🟡 `build_index.scan` forum-bazında sessiz atlıyor

`r.status_code != 200 → break` (`49`): tek forumun 401/403/500'ü o forumu boş tarar; %90 koruyucu yalnız **toplam** düşüşü yakalar — bir sunucunun tek forumu tamamen düşse indeks sessizce eksilir. Forum bazlı "beklenen vs bulunan" sayaç veya hata logu + `main`'de guild-bazında eşik önerilir.

### N15 — ⚪ Repo hijyeni artıkları

- `bot/idx2.log` (4 satır bayat log) commitli.
- `data/index.json` 1,2 MB üretilmiş artefakt commitli (bilinçli olabilir: bot ilk açılışta hazır indeksle başlıyor — karar README'ye yazılmalı).
- `.env.example` `DISCORD_BOT_TOKEN_WH40K`/`FILM_GUILD_ID`/`NMDB_*` değişkenlerini içermiyor (N7).
- Uzakta `devin/1790290120-lexicanum-v11` (main'in gerisinde) ve `devin/1790291279-lexicanum-v12` (main ile aynı) dalları duruyor — temizlenebilir.

### N16 — ⚪ Pozitif gözlemler (rapor bütünlüğü için)

- `search`'e `rapidfuzz.fuzz.token_set_ratio` eklenmesi (≥75 eşiği, skor 46-55 bandında) yazım varyantlarını ("khorne"↔"korne") yakalıyor — iyi ayarlanmış, alt-skor bandı token-kesişiminin altında tutularak sıralama korunmuş.
- `save_index` atomik (`tmp`+`os.replace`), `build_index` %90 koruyucusu, `INDEX[:] =` yerinde-değiştirme, `members` intent'inin bilinçli kullanımı — hepsi doğru mühendislik.
- `filmarchive/dapi.py`'nin `req`'i (try/except + 429/5xx/404 ayrımı) sağlam; ortak modüle bu sürüm çıkarılmalı (H5).

---

## 5. Geliştirme Planı

> Sıralama: veri kaybı → döküm bütünlüğü → bot sağlamlığı → içerik kalitesi → altyapı → hijyen. Kod bu raporda değiştirilmedi; plan uygulama içindir.

### Faz A — Kalan veri kaybı riskleri (hedef: ~0,5 gün)

| # | İş | Dosya | Kabul kriteri |
|---|----|-------|---------------|
| A1 | C3: bilinmeyen thread varken forumu silme | `build_server.py` `run_bands`/`run_split` | `!! bilinmeyen thread` sayısı >0 → `delete` atlanır, `--force` gerektirir |
| A2 | C4: `run_relabel` tam sayfalama | `build_server.py:889` | 50+ mesajlı thread'de hizalama starter'dan başlar; sahte 60 mesajlı thread ile test |
| A3 | M12: `sweep_stale` eşiği | iki `dump_all.py` | Silinecek oran >%30 veya forum boş döndüyse silme durur; `--dry-run` bayrağı |
| A4 | N1: `all` fazı state'siz çöküyor | `build_server.py:693,783,884` | Taze `work/`'de `all` = `prep+structure+guide+posts+az`; migrasyonlar state yoksa no-op |

### Faz B — Döküm bütünlüğü (hedef: ~0,5 gün)

| # | İş |
|---|----|
| B1 | H7: thread mesajları `before` ile tam sayfala; metin kanalı sınırını kaldır veya kesinti sayısını raporla |
| B2 | H8: `fdir`/`cat` bileşenlerine `fsafe()`; repodaki `/` içeren bozuk yolu (`TrenchCrusade/forumlar/40・GELECEK / DUYURULMUŞ LORE - ...`) yeniden adlandır + dökümü tazele |
| B3 | H5: `filmarchive/dapi.py`'yi `bot/lib/dapi.py`'e çıkar; iki betik ortak kullansın; `GUILD` env ile parametrik |
| B4 | N6: tüm `open()`'lara `encoding='utf-8'` (Windows geliştirme desteği) |
| B5 | N14 + L5: forum-bazlı hata logu, guild eşiği, wh40k manifest düğümü eksikse oluştur |

### Faz C — Bot sağlamlığı (hedef: ~0,5 gün)

| # | İş |
|---|----|
| C1 | N2: birleştirme ayracı sorununu çöz (kayıt format işareti veya mesaj-bazlı düzenleme); `tail`'i yalnız >4000'de ve ayrık sakla, kullanıcıya "sondan N karakter korunuyor" notu |
| C2 | N3: `on_submit` kilit içinde dedupe-ekleme + `save_index()` |
| C3 | N4+N5: `m.author == bot.user` filtresi, `isinstance(th, Thread)` kontrolü |
| C4 | N9+N10: `fetch_channel` fallback, `'c'` alanını parent kategoriden doldur, `id` alanını şemaya ekle (URL ayrıştırmayı bırak) |
| C5 | N13: uzun işlerde sonucu kanala/loga yaz |
| C6 | M4: `run_guide`/`run_az`'a karşılaştır-PATCH (`sync_thread` mantığı hazır referans) |
| C7 | M9: `parse_uygunluk()` yardımcısı; M10: `key in cache`; M11: mevcut daveti yeniden kullan |

### Faz D — İçerik kalitesi (hedef: ~0,5 gün)

- D1 H6: `**` saracı düzelt + `relabel` fazıyla canlı dizinleri tazele (önce test sunucusu/tek forumda kuru çalıştırma)
- D2 N8: `/ara` başlığına toplam eşleşme ("10/412 gösteriliyor")
- D3 N12: indeks kayıtlarına önceden-normalize alan
- D4 L9: TMDB poster için resmi API'ye geçiş değerlendirmesi (anahtar gerekir) ya da regex gevşetme

### Faz E — Altyapı ve kalite (hedef: ~1 gün, paralel yapılabilir)

- E1 Testler: `norm`, `search`, `chunks`, `line_chunks`, `band_of`, `forum_label`, `parse_uygunluk` — saf fonksiyonlar; sahte thread ile düzenleme akışı
- E2 CI (GitHub Actions): `ruff check` + `python -m compileall` + `pytest` + gitleaks; PR'larda otomatik
- E3 (opsiyonel, büyük) SQLite + FTS5 indeks: artımlı guild taraması, ms arama, `kayit-ekle` otomatik kalıcılık; `index.json`'ı export artefaktı olarak tut
- E4 `lexicanum.py`'yi `commands/` + `index_store.py` + `search.py` modüllerine ayır; iki `dapi.py`'yi birleştir (B3 ile aynı iş)
- E5 Gözlemlenebilirlik: `print`→`logging` (dump'lar hâlâ print), `/saglik` komutu (indeks yaşı, guild başına sayı, son tarama zamanı)

### Faz F — Repo hijyeni ve doküman (hedef: ~0,5 gün)

- F1 N15: `idx2.log` kaldır; `index.json` kararını README'ye yaz; `.env.example`'ı tüm değişkenlerle güncelle (N7); geride kalan `devin/*` dallarını sil
- F2 N11: viewer kaynağını repoya al veya üretecini commitle; GitHub Pages ile `docs/` yayını (statik, sunucu maliyeti sıfır)
- F3 Kökteki ~600 dağınık `.md` + `THE_IMPERIAL_ARCHIVE_TAM.md` (1,2 MB) ile `Warhammer/` ilişkisini netleştir — eski düz döküm mü? Öyleyse `Warhammer/altına taşı veya `archive/` klasörü; `a-z-indeks*.md` dosyaları zaten forumlarda dizin olarak var
- F4 `AGENTS.md` ekle: build/test/döküm komutları, env değişkenleri, "canlı sunucuya yazan betikler" uyarısı (`.agents/skills/` ile tutarlı)

---

## 6. Ekleme / Özellik Önerileri

**Arama & UX**
1. `/ara` sonuçlarında sayfalama butonları (`discord.ui.View`) + kategori filtresi (`r['c']` zaten indeksleniyor ama embed'de gösterilmiyor — göster).
2. "Bunu mu demek istediniz?" — 0 sonuçta `process.extractOne` ile en yakın 3 başlık (rapidfuzz zaten bağımlılık).
3. `/benzer <kayıt>` — aynı forum/kategorideki diğer kayıtlar (veri hazır, ucuz).
4. `/gunun-kaydi` — günlük planlanmış gönderi (APScheduler veya basit `asyncio` döngüsü; sunuculara canlılık katar).
5. Sonuç embed'ine kayıt yaşı/güncelleme bilgisi; `index.json`'a `mtime` footer'ı.

**Yönetim**
6. `/yedek` — tek komutta indeks + log config + (opsiyonel) forum dökümü zip'i; systemd timer'a da bağlanabilir.
7. `/on-degisiklik` — son N indeks farkı (event logları zaten `log.info`'da; kalıcı `data/index_changelog.jsonl` tutulabilir).
8. Rol bazlı katkı akışı: `✍️ Katkıcı` rolüne `/kayit-oner` (ephemeral onay kuyruğu → yönetici onayıyla `kayit-ekle`) — manifest'teki roller bunu ima ediyor.

**Altyapı**
9. `docs/` statik sitesini GitHub Pages'e aç (viewer eklendikten sonra) → arşive Discord'suz erişim.
10. Dependabot + minimumReleaseAge benzeri politika (requirements'ta üst sınır zaten var).
11. `docker-compose.yml` veya tek `Dockerfile` — Oracle VM kurulum adımlarını (README §Oracle) tek dosyaya indirger.
12. Çok-sunuculu döküm betiklerini tek `dump.py --guild <slug>` CLI'sine indirgeme (guilds.json'dan okur; H5/L5/N7'yi de kapatır).

**İçerik**
13. Sunucular arası çapraz bağlantılar: WH40K kartlarında `[[...]]` benzeri referans taraması → "İlgili kayıtlar" devam mesajı (Markdown dosyalarında bağlantılar zaten var mı — döküm verisiyle ölçülebilir).
14. Mythica/Trench için `build_server.py` benzeri kurucu çıkarmak yerine **genel** `build_forum.py` (film-özel alanlar config'e) — yeni arşiv sunucusu eklemeyi saat meselesine indirir.

---

## 7. Bu Rapor İçin Çalıştırılan Doğrulamalar

| Kontrol | Sonuç |
|---|---|
| `python -m compileall bot/` (Python 3.14) | ✅ tüm dosyalar derleniyor |
| `index.json` ayrıştırma + dağılım | 5.807 kayıt, 5 guild, `c` alanı dolu |
| Windows varsayılan kodlamasıyla `index.json` okuma | ❌ `UnicodeDecodeError` (N6 canlı kanıtı — cp1254, `・` U+30FB kodlanamıyor) |
| `git ls-remote` + fetch | remote main 2 commit ilerideydi (#12, #13); rapor güncel HEAD `9798d336` üzerine |
| v11/v12 dalları diff | v11 main'in gerisinde; v12 main ile aynı (N15) |

---

*Rapor `bot/` ve repo genelinin 2026-09-25 tarihli `main` (`9798d336`) hâli üzerine hazırlandı. Kod değiştirilmedi; tüm bulgular salt-okunur analiz, repo verisi ve bu makinede çalıştırılan doğrulamalarla desteklendi.*
