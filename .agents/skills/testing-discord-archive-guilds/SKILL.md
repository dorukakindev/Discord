---
name: testing-discord-archive-guilds
description: How to deep-verify a live "Archive" Discord guild (Film/Trench/Imperial/RPG/Mythica family) built by bot/<server>/build_server.py — API verification pattern, verbatim-content replay, read-only checks, invite checks, and environment pitfalls.
---

# Testing live Archive Discord guilds

## Access
- Bot `Lexicanum` (token env `DISCORD_BOT_TOKEN_WH40K`) is Administrator in the archive-family guilds. Use `bot/<server>/dapi.py` helpers: `get/post/patch/delete`, `guild_channels()`, `channel_messages(cid)` (paginates), `forum_threads(cid)` (active+archived). Guild id is in `dapi.GUILD` / `FILM_GUILD_ID` env.
- Build state lives in `bot/<server>/work/`: `structure.json` (channel ids), `post_state.json` (`done` map `slug|id|title`→thread id, `indexes` forum→index thread id), `posters.json`.

## Deep-verification pattern (strongest)
Replay the build script's own generators against the source DBs and compare with live:
- `split_dbs()` → main/kesif lists; `title_of()`, `forum_label()`, `film_messages()`, `index_messages()`, `guide_contents()`, `az_text()`, `chunks()`.
- Fetch thread messages (reverse page order → oldest first) and compare to regenerated message lists.
- **Discord strips leading whitespace at message start** — a chunk boundary can land mid-line inside `**bold**` (e.g. `• **Max and the` / `Junkmen (1971)**`), losing a space. Compare per-message with `strip()` edge tolerance AND concatenated text; report strict-verbatim diffs as cosmetic only if they're whitespace at message edges.
- Verify thread-name SETS (not just counts) vs `title_of(f)[:95]` + index name — catches wrong/duplicated threads.
- Index threads must have `flags & 2` (pinned).
- Posters: check `_poster` hydration from posters.json; valid domains are `media.themoviedb.org` and `a.ltrbxd.com`.

## Read-only (salt-okunur) check — easy to get wrong
- Each channel/category needs `@everyone` (id == guild id) overwrite `deny == "377957124160"`.
- ALSO check leftover default categories/channels ("Text Channels"/"Voice Channels"/#general/#General): if the @everyone *role* has SEND_MESSAGES (0x800) + CREATE_THREADS at base level, any channel without an overwrite is writable → breaks the read-only claim even when all named channels deny correctly.

## Public invite
- API: `GET /invites/<code>` → guild.id, expires_at, channel, member_count. Sibling links: regex `discord\.gg/(\w+)` then resolve each code.
- **Chrome pitfall**: this box's Chrome-for-Testing SIGSEGVs on the discord.com SPA (seccomp-bpf/JIT crash; persists with `--no-sandbox`, `--disable-gpu`, `--js-flags=--jitless`). Don't burn time retrying — verify invites via API and render `https://discord.com/api/v10/invites/<code>` JSON in-browser for visual evidence.
- Guild widget (`/guilds/<id>/widget.json`) is usually disabled (403) — not a defect.

## Static viewer (docs/index.html, "Lexicanum Arşivleri")
- No public Pages URL — serve yourself: `cd docs && python3 -m http.server <port>`.
- Viewer loads `manifest.json` (servers[].title → switcher; forums[].items[] → `details` "name (count)"; texts[] grouped by `grp`) and `index.json` (search entries {s,f,t,u}, s = display title e.g. 'THE FILM ARCHIVE'). `load(u)` fetches `docs/<u>` md and renders with a small line-mapper: bare image-URL line → `<img>`, `-# `→sub, `#/##/###`→headings, `>`→blockquote, `- `/`* `→li, `**`→bold, `[t](u)`→link.
- Index threads are the LAST item in each forum's nav list. Chrome find-in-page auto-expands collapsed `<details>` — use Ctrl+F to jump to deep items.
- `browser_console` tool may fail to attach to a manually relaunched Chrome even with `--remote-debugging-port` — verify render-level counts against the source .md (each `• ` line = one `<li>`) plus screenshots.

## Shell pitfalls
- The Chrome binary is `chrome` (`chrome-linux64/chrome`), not `google-chrome`. `pkill -f "chrome"` matches your own shell command and kills it — use `pkill -9 -x chrome`.
- Use `pgrep -f "chrome-linux64/chrome"` to inspect real Chrome processes.
