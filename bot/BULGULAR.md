# Bulgu Defteri

İki raporun (`bug-raporu-ve-duzeltme-plani.md`, `derin-inceleme-ve-gelistirme-plani.md`)
bulgularının tek yerde durum takibi. Son güncelleme: 2026-09-25 — `bot/` genel sağlamlaştırma PR'ı.

## Kritikler

| ID | Konu | Durum |
|----|------|-------|
| C1 | `norm()` `ı` harfini siliyor — %15,5 kayıt aranamıyor | ✅ `lib/textnorm.py` — transliterasyon + tek kaynak |
| C2 | `/kayit-duzenle` veri kaybı | ✅ Önceki PR + bu tur: `join_body`/`split_for_modal` (N2) |
| C3 | `run_bands`/`run_split` bilinmeyen thread'li forumu siliyor | ✅ Bilinmeyen thread varsa forum+kategori silinmez; `--force`'ta önce `work/trash/` dökümü |
| C4 | `run_relabel` 50-mesaj penceresi | ✅ `sync_msgs` tam sayfalama + yalnız bot mesajları |

## Yüksek

| ID | Konu | Durum |
|----|------|-------|
| H1 | `.env` yüklenmiyor | ✅ `lib/dapi.py` dotenv yükler — tüm betikler kapsanır |
| H2 | DM'de AttributeError | ✅ Kapalı (önceki PR) |
| H3 | `req` None / boş indeks üzerine yazma | ✅ Atomik yazma + %90 toplam + **%50 guild-bazlı** koruma |
| H4 | Aynı adlı thread çakışması | ✅ Kapalı (önceki PR) |
| H5 | İki `dapi.py` ayrışması | ✅ `lib/dapi.py` — tek modül, eski kopyalar silindi |
| H6 | Dizin satırı `**` artığı | ✅ `band_entry` → `**{t}** · sc`, `index_messages` → `• {e}` |
| H7 | Döküm mesaj sınırları (100/500) | ✅ `channel_messages()` sınırsız sayfalama |
| H8 | `fdir` sanitize edilmiyor | ✅ `fsafe(cat) - fsafe(forum)`; `40・GELECEK ` yolu düzeltildi |

## Orta

| ID | Konu | Durum |
|----|------|-------|
| M1 | kayıt-ekle kalıcılığı | ✅ upsert + INDEX_LOCK + save (N3) |
| M2 | eşzamanlı index-yenile | ✅ Kapalı (önceki PR) |
| M3 | tekrarlı tree.sync | ✅ Kapalı (önceki PR) |
| M4 | guide/az idempotent değil | ✅ `sync_msgs` — tekrar koşu çift yazmaz |
| M5-M8 | arşiv durumu, log kanalı, embed injection, forum lookup | ✅ Kapalı (önceki PR) |
| M9 | korumasız `float()` | ✅ `fnum()` — fit_score + güven yüzdesi |
| M10 | poster önbelleği falsy | ✅ `if key in cache` — None da cache'lenir |
| M11 | davet birikmesi | ✅ `existing_invite()` — mevcut davet yeniden kullanılır |
| M12 | `sweep_stale` koşulsuz | ✅ >%30 stale oranında sweep atlanır; `--force-sweep`/`--dry-run` bayrakları |

## Düşük / yeni bulgular

| ID | Konu | Durum |
|----|------|-------|
| N1 | `all` fazı state'siz çöküyor | ✅ bands/split/relabel state yoksa no-op |
| N2 | düzenleme paragraf yapıştırması + tail | ✅ `join_body` + `split_for_modal` (paragraf sınırı) |
| N3 | INDEX.append kilit dışı | ✅ kilit + upsert + save_index |
| N4 | yabancı mesajlara dokunma | ✅ yalnız `author == bot.user.id` |
| N5 | thread olmayan kanal | ✅ `isinstance(discord.Thread)` |
| N6 | encoding belirtilmeyen open() | ✅ `lib/jsonio.py` — hep utf-8 |
| N7 | env adları tutarsız | ✅ `.env.example` tam liste |
| N8 | "N sonuç" toplam değil | ✅ `search` → (rows, total) |
| N9 | forum lookup önbellek bağımlı, `c` boş | ✅ `forum_of()` fetch fallback + kategori doldurma |
| N10 | biçimsiz `l` alanı IndexError | ✅ `r['i']` alanı + URL fallback |
| N11 | docs/ görüntüleyici kaynağı yok | ⏸️ Kapsam dışı (docs sitesi ayrı tutuluyor) |
| N12 | search() her sorguda norm+set | ✅ `r['n']` önceden-normalize (build_index + load_index + rec_of_thread) |
| N13 | followup 15 dk sınırı | ✅ HTTPException → `channel.send` fallback |
| N14 | forum-bazlı sessiz atlama | ✅ `scan` → (recs, bad) + %50 guild eşiği |
| N15 | repo hijyeni | ✅ idx2.log, .env→gitignore, 20 devin dalı silindi |
| L5 | wh40k manifest d��ğümü | ✅ create-if-missing + `texts` + `_txt` dökümü |
| L6 | `dsan` çakışması | ⏸️ Açık — aynı slug'a ayrışan iki kayıt için sonlandırıcı ekleme gerek |
| L7 | bayat dosyalar | ✅ idx2.log silindi (index.json commitli = bilinçli dağıtım kanalı) |
| L9 | TMDB scrape kırılgan | ✅ og:image regex `t/p/[^"]+` — boyut-agnostik |
| L10 | `line_chunks` boş parça/uzun satır | ✅ boş chunk yok, >limit satır sert bölünür |
| Ö1 | yıkıcı işlem öncesi snapshot | ✅ `backup_state()` + `trash_thread()` |
| Ö2 | dry-run kapısı | ✅ `DRY_RUN` env + `--dry-run` — dapi.req kısa devre |

## Özellikler (§6'dan seçilenler)

- `/ara` 0 sonuç → "Bunu mu demek istediniz?" (rapidfuzz token_set_ratio ≥60, 3 öneri) ✅
- Sonuç satırına kategori: `forum · kategori · sunucu` (`r['c']`) ✅
- `bot/tests/` birim testleri + `.github/workflows/bot-ci.yml` ✅
- Kalan opsiyonlar (bilinçli ertelendi): SQLite FTS5, modül bölme, GitHub Pages, Dockerfile, zamanlanmış gönderiler
