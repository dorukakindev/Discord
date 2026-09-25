# Lexicanum Bot

Arşiv sunucularını (Imperial / Trench / Black RPG / Film Archive) tek botla yönetir.

## Komutlar

| Komut | Kim | İşlev |
|---|---|---|
| `/ara <sorgu>` | herkes | Kayıtlarda Türkçe-normalize + fuzzy arama, Discord bağlantılı sonuç listesi; 0 sonuçta öneri sunar |
| `/sor <soru>` | herkes | Soruyu en yakın kayda eşler, kaydın thread metninden en ilgili paragrafı çıkarır (LLM yok, anahtar-kelime puanlama) |
| `/rastgele` | herkes | Rastgele kayıt (içinde bulunulan sunucu öncelikli) |
| `/istatistik` | herkes | Sunucu başına kayıt sayısı |
| `/kayit-ekle` | `manage_messages` | Forum seç + modal ile başlık/metin → yeni kayıt postu |
| `/kayit-duzenle` | `manage_messages` | Kayıt seç + modal ile metni değiştir |
| `/index-yenile` | `manage_messages` | Sunucuları yeniden tarayıp `data/index.json`'ı tazeler |

Ayrıca `data/log_channels.json`'da tanımlı kanallara üye giriş/çıkış logu düşer.

## Gereksinimler

- Python 3.10+ · `pip install -r requirements.txt`
- Discord geliştirici portalında **Server Members Intent** açık olmalı
  (Developer Portal → Bot → Privileged Gateway Intents).
- Botun üç sunucuda da üye ve forumlarda `Manage Threads`/`Send Messages`
  yetkisi olmalı (mevcut Lexicanum botu bu yetkilere sahip).

## Çalıştırma

```bash
cp .env.example .env    # DISCORD_TOKEN=... yaz
pip install -r requirements.txt
python3 lexicanum.py
```

İlk kurulumda veya içerik değişince indeksi üret:

```bash
DISCORD_TOKEN=... python3 build_index.py   # ~10 dk, data/index.json yazar
```

## Üretim hattı betikleri

| Betik | İş |
|---|---|
| `build_index.py` | 5 guild'in forumlarını tarar → `data/index.json` (atomik yazma + %50/guild + %90/toplam koruma; hatalı forumlar raporlanır) |
| `filmarchive/build_server.py` | nMDB veritabanlarından Film Archive guild'ini kurar/günceller. Fazlar: `prep structure guide posts az bands split relabel all`. Flag'ler: `--dry-run`, `--force` |
| `filmarchive/dump_all.py` · `wh40k/dump_all.py` | Canlı guild → repo markdown dökümü + `docs/` verisi. Flag'ler: `--dry-run`, `--force-sweep` |
| `lib/dapi.py` | Ortak Discord REST katmanı (retry/429/5xx, DRY_RUN kısa devre). Guild'ler `configure()` veya `*_GUILD_ID` env ile bildirilir |
| `lib/textnorm.py` · `lib/jsonio.py` | Türkçe arama normalizasyonu · utf-8 okuma + atomik JSON yazma |

Güvenlik: yıkıcı betikler `post_state.json` yedeği (`work/backups/`) + silinmeden önce thread dökümü (`work/trash/`) alır. Bilinmeyen thread içeren forum `--force` olmadan silinmez; `sweep_stale` >%30 oranında durur. Önce `--dry-run` ile plan gör:

```bash
DRY_RUN=1 python3 filmarchive/build_server.py split
python3 filmarchive/dump_all.py --dry-run
```

Geliştirme/test: `cd bot && ruff check . && python -m pytest tests/` — bulgu takibi `BULGULAR.md`.

## Docker (alternatif)

```bash
cd bot && docker build -t lexicanum .
docker run -d --name lexicanum --restart unless-stopped --env-file .env lexicanum
```

## Oracle Cloud Always Free kurulumu (kalıcı, ücretsiz)

1. `cloud.oracle.com` → **Sign Up** (kredi kartı ister, ücret almaz).
2. **Create a VM instance** → Shape: `VM.Standard.A1.Flex` (Ampere ARM),
   Image: Ubuntu 22.04, 1 OCPU / 6 GB yeterli.
   Not: A1 kapasitesi bölgeye göre değişir; doluysa başka bölge seç.
3. VM'e SSH ile bağlan. Bot yalnızca **dışa** bağlantı kurar —
   güvenlik listesine (Security List) hiçbir inbound kuralı gerekmez.
4. ```bash
   sudo apt update && sudo apt install -y python3-pip git
   sudo useradd -r -s /usr/sbin/nologin lexicanum
   sudo git clone https://github.com/dorukakindev/Discord.git /opt/lexicanum-repo
   sudo cp -r /opt/lexicanum-repo/bot /opt/lexicanum
   sudo chown -R lexicanum:lexicanum /opt/lexicanum
   cd /opt/lexicanum && pip3 install -r requirements.txt
   sudo cp systemd/lexicanum.service /etc/systemd/system/
   sudoedit /opt/lexicanum/.env          # DISCORD_TOKEN=...
   sudoedit /etc/systemd/system/lexicanum.service  # yolları doğrula
   ```
5. İndeksi üret: `sudo -u lexicanum env DISCORD_TOKEN=... python3 build_index.py`
   (ya da botu açtıktan sonra Discord'da `/index-yenile` çalıştır).
6. ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now lexicanum
   journalctl -u lexicanum -f    # logları izle
   ```

Güncelleme: `cd /opt/lexicanum-repo && git pull && cp -r bot/. /opt/lexicanum/ && sudo systemctl restart lexicanum`

## Canlı kurulum (Eylül 2026)

- **VM**: `ubuntu@158.101.217.164` — Oracle Always Free, Amsterdam, Ubuntu 22.04 ARM
  (VM.Standard.A1.Flex, 2 OCPU / 12 GB). Lexicanum'a ayrılmış makine; quiztavern ile
  aynı VCN ama bağımsız.
- **Kurulum**: `/opt/lexicanum` (`lexicanum` sistem kullanıcısı), `.env` (600),
  `discord.py` sistem genelinde kurulu.
- **Servis**: `lexicanum.service` (enabled, `Restart=always`) —
  `journalctl -u lexicanum -f` ile izlenir.
- **SSH**: Devin tarafında `~/.ssh/lexicanum-oracle` anahtarı `ubuntu`
  kullanıcısına launch'ta eklendi.

## Güvenlik

- Token asla repoya yazılmaz; yalnızca `.env`'de durur (`.gitignore` kapsamında).
- Geliştirme sırasında token düz metin olarak paylaşıldıysa Developer Portal'dan
  **Reset Token** ile yenilemek önerilir (eski token anında ölür, `.env` güncellenir).
