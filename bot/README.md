# Lexicanum Bot

Üç arşiv sunucusunu (Imperial / Trench / Black RPG) tek botla yönetir.

## Komutlar

| Komut | Kim | İşlev |
|---|---|---|
| `/ara <sorgu>` | herkes | 3.957 kayıtta Türkçe-normalize arama, Discord bağlantılı sonuç listesi |
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

## Güvenlik

- Token asla repoya yazılmaz; yalnızca `.env`'de durur (`.gitignore` kapsamında).
- Geliştirme sırasında token düz metin olarak paylaşıldıysa Developer Portal'dan
  **Reset Token** ile yenilemek önerilir (eski token anında ölür, `.env` güncellenir).
