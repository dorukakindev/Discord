---
name: testing-discord-archive-guilds
description: How to deep-verify a live "Archive" Discord guild (Film/Trench/Imperial/RPG/Mythica family) built by bot/<server>/build_server.py — API verification pattern, verbatim-content replay, read-only checks, invite checks, and environment pitfalls.
---

# Testing live Archive Discord guilds

## Access
- Bot `Lexicanum` (token env `DISCORD_BOT_TOKEN_WH40K`) is Administrator in the archive-family guilds. Use the shared `bot/lib/dapi.py` helpers (per-guild copies were deleted): `get/post/patch/delete`, `guild_channels()`, `channel_messages(cid)` (paginates all), `forum_threads(cid)` (active+archived). Select a guild with `dapi.configure(guild=<id>)` or `FILM_GUILD_ID`/`WH40K_GUILD_ID`/`DISCORD_GUILD_ID` env; `DRY_RUN=1` short-circuits writes.
- Build state lives in `bot/<server>/work/`: `structure.json` (channel ids), `post_state.json` (`done` map `slug|id|title`→thread id, `indexes` forum→index thread id), `posters.json`.

## Deep-verification pattern (strongest)
Replay the build script's own generators against the source DBs and compare with live:
- `split_dbs()` → main/kesif lists; `title_of()`, `forum_label()`, `film_messages()`, `index_messages()`, `guide_contents()`, `az_text()`, `chunks()`.
- Fetch thread messages (reverse page order → oldest first) and compare to regenerated message lists.
- **Discord strips leading whitespace at message start** — a chunk boundary can land mid-line inside `**bold**` (e.g. `• **Max and the` / `Junkmen (1971)**`), losing a space. Compare per-message with `strip()` edge tolerance AND concatenated text; report strict-verbatim diffs as cosmetic only if they're whitespace at message edges.
- Verify thread-name SETS (not just counts) vs `title_of(f)[:95]` + index name — catches wrong/duplicated threads.
- Index threads must have `flags & 2` (pinned).
- Posters: check `_poster` hydration from posters.json; valid domains are `media.themoviedb.org` and `a.ltrbxd.com`.
- **The main DB and the discoveries DB share the same autoincrement `id` space** — a `{id: film}` map built from `main+kesif` collapses overlapping ids onto the wrong film (e.g. main 548 = Stalker vs kesif 548 = The Fifth Seal). Build per-source id maps keyed by forum: band slugs → main ids, `*-kesifleri` slugs → kesif ids.
- **Posters may silently go missing on incremental imports**: `posters.json` is keyed `id|imdb_id` — if the DB's imdb_id assignments change after a fetch, cached entries become unresolvable (`cache.get(key)` → None → card renders without poster). When new records show 0 posters, check whether their keys exist under stale imdb suffixes before calling it intentional.
- **Incremental imports can leave stale content even when everything else passes**: after an import that adds films of *existing* directors, verify director cards (Kayıt sayısı + bullet list) were regenerated — new-director cards get created but pre-existing cards may not be updated. Also check guide/text channels for duplicated reposts (new message appended, old not deleted).
- **`post_state.json` writes are atomic** (`lib/jsonio.write_json_atomic`); destructive phases snapshot state to `work/backups/` and dump deleted threads to `work/trash/` first — rerun safety lives there.

## Read-only (salt-okunur) check — easy to get wrong
- Each channel/category needs `@everyone` (id == guild id) overwrite `deny == "377957124160"`.
- ALSO check leftover default categories/channels ("Text Channels"/"Voice Channels"/#general/#General): if the @everyone *role* has SEND_MESSAGES (0x800) + CREATE_THREADS at base level, any channel without an overwrite is writable → breaks the read-only claim even when all named channels deny correctly.

## Public invite
- API: `GET /invites/<code>` → guild.id, expires_at, channel, member_count. Sibling links: regex `discord\.gg/(\w+)` then resolve each code.
- **Chrome pitfall**: this box's Chrome-for-Testing SIGSEGVs on the discord.com SPA (seccomp-bpf/JIT crash; persists with `--no-sandbox`, `--disable-gpu`, `--js-flags=--jitless`). Don't burn time retrying — verify invites via API and render `https://discord.com/api/v10/invites/<code>` JSON in-browser for visual evidence.
- Guild widget (`/guilds/<id>/widget.json`) is usually disabled (403) — not a defect.

## Static viewer (docs/index.html, "Lexicanum Arşivleri")
- **First verify docs/index.html still exists** (`git ls-files docs/index.html`) — a merged "site regen" commit deleted it while keeping the data files. If absent, restore a copy from a commit that had it (e.g. `git show <commit>:docs/index.html > docs/index.html`) for test-only render checks, then remove it to keep the tree clean.
- No public Pages URL — serve yourself: `cd docs && python3 -m http.server <port>`.
- Viewer loads `manifest.json` (servers[].title → switcher; forums[].items[] → `details` "name (count)"; texts[] grouped by `grp`) and `index.json` (search entries {s,f,t,u}, s = display title e.g. 'THE FILM ARCHIVE'). `load(u)` fetches `docs/<u>` md and renders with a small line-mapper: bare image-URL line → `<img>`, `-# `→sub, `#/##/###`→headings, `>`→blockquote, `- `/`* `→li, `**`→bold, `[t](u)`→link.
- Index threads are the LAST item in each forum's nav list. Chrome find-in-page auto-expands collapsed `<details>` — use Ctrl+F to jump to deep items.
- `browser_console` tool may fail to attach to a manually relaunched Chrome even with `--remote-debugging-port` — verify render-level counts against the source .md (each `• ` line = one `<li>`) plus screenshots.

## Shell pitfalls
- The Chrome binary is `chrome` (`chrome-linux64/chrome`), not `google-chrome`. `pkill -f "chrome"` matches your own shell command and kills it — use `pkill -9 -x chrome`.
- Use `pgrep -f "chrome-linux64/chrome"` to inspect real Chrome processes.
