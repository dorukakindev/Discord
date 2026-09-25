# AGENTS — Doruk/Discord arşiv reposu

Bu repo 5 salt-okunur "arşiv" Discord guild'inin markdown dökümü + `docs/` statik site verisi + `bot/` araç takımıdır.

## Dizin

- `Warhammer/ TrenchCrusade/ BlackRPG/ Mythology/ FilmArchive/` — guild dökümleri (`forumlar/<cat> - <forum>/<kayıt>.md`, `metin-kanallari/<cat>/<kanal>.md`, `server_manifest.json`)
- `docs/` — statik site verisi (`manifest.json`, `index.json`, `data/<Sunucu>/...`)
- `bot/` — Lexicanum botu + üretim hattı betikleri (ayrıntı `bot/README.md`)
- `bot/lib/` — ortak modüller: `dapi` (Discord REST, DRY_RUN), `textnorm` (Türkçe normalize), `jsonio` (utf-8 + atomik yazma)
- `bot/tests/` — pytest birim testleri (`cd bot && python -m pytest tests/`)
- `bot/BULGULAR.md` — iki inceleme raporunun bulgu durum defteri

## Kurallar

- Bot kodu yalnız `bot/` altında yaşar; arşiv `.md` içeriğini elde düzenleme (döküm betikleri üretir).
- `.env`/token ASLA commitlenmez (`.gitignore` kapsamında).
- `docs/manifest.json`/`docs/index.json` betikler tarafından atomik güncellenir (`lib/jsonio.write_json_atomic`).
- Bot tarafında `DISCORD_TOKEN` (lexicanum, build_index) ve `DISCORD_BOT_TOKEN_WH40K` (build/dump betikleri) kullanılır.
- Yıkıcı betiklerde önce `--dry-run` (`DRY_RUN=1`): `dump_all.py --dry-run`, `build_server.py <faz> --dry-run`.
- Canlı sunucu: `ubuntu@158.101.217.164` (`/opt/lexicanum`, systemd `lexicanum.service`) — kurulum `bot/README.md`.
- Lint/test: `cd bot && ruff check . && python -m pytest tests/` (CI: `.github/workflows/bot-ci.yml`).
