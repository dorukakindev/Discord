# -*- coding: utf-8 -*-
"""The Film Archive sunucusunu nMDB veritabanlarından kurar.

Kullanım:
    NMDB_MAIN=/path/nmdb_arsiv.db NMDB_DISC=/path/nmdb_arsiv_discoveries.db \
    DISCORD_BOT_TOKEN_WH40K=... python3 build_server.py <faz>

Fazlar: prep | structure | guide | posts | az | all
State/plan dosyaları WORK dir'de tutulur (varsayılan ./work).
"""
import json, os, re, sqlite3, sys, time, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dapi import req, get, post, patch, delete, guild_channels, GUILD

WORK = os.environ.get("WORK", os.path.join(os.path.dirname(os.path.abspath(__file__)), "work"))
os.makedirs(WORK, exist_ok=True)

MAIN_DB = os.environ.get("NMDB_MAIN", "")
DISC_DB = os.environ.get("NMDB_DISC", "")
SERVER = "THE FILM ARCHIVE"
DENY = "377957124160"  # @everyone: send/thread deny -> salt-okunur
EVERYONE = GUILD        # @everyone rol id = guild id

SESSION = __import__("requests").Session()


def norm(s):
    return unicodedata.normalize("NFKD", str(s or "")).casefold().strip()


def dash(v):
    return v is None or str(v).strip() in ("", "-", "None")


# ---------------------------------------------------------------- veri

def load_films(path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    films = [dict(r) for r in con.execute("select * from filmler")]
    cur = {r["film_id"]: r for r in con.execute(
        "select * from film_ai_analizleri where is_current=1 and status='current' and analysis_text != ''")}
    for f in films:
        a = cur.get(f["id"])
        f["_analiz"] = a["analysis_text"] if a else ""
        f["_model"] = (a["model"] if a else "") or ""
    return films


def split_dbs():
    """Ana arşiv = MAIN'deki her şey. Keşif = DISC'te olup MAIN'de olmayanlar."""
    main = load_films(MAIN_DB)
    disc = load_films(DISC_DB)
    keys = {(norm(f.get("ingilizce_adi")), str(f.get("yili") or "")) for f in main}
    ids = {f.get("imdb_id") for f in main if not dash(f.get("imdb_id"))}
    kesifler = []
    for f in disc:
        iid = f.get("imdb_id")
        if iid and not dash(iid) and iid in ids:
            continue
        if (norm(f.get("ingilizce_adi")), str(f.get("yili") or "")) in keys:
            continue
        kesifler.append(f)
    return main, kesifler


# ---------------------------------------------------------------- afiş

def fetch_poster(f):
    """media.themoviedb.org afiş URL'sini og:image'dan çöz."""
    tid = f.get("tmdb_id")
    if dash(tid):
        return None
    kinds = ["tv", "movie"] if f.get("kategori") in ("Dizi", "Anime") else ["movie", "tv"]
    for k in kinds:
        try:
            r = SESSION.get(f"https://www.themoviedb.org/{k}/{int(tid)}",
                            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/126",
                                     "Accept-Language": "en-US"}, timeout=20)
            m = re.search(r'og:image" content="(https://media\.themoviedb\.org/t/p/w500/[^"]+)', r.text)
            if r.status_code == 200 and m:
                return m.group(1)
        except Exception:
            pass
        time.sleep(0.3)
    return None


def fetch_poster_lb(f):
    """Letterboxd film sayfasının og:image'ı (afiş veya backdrop)."""
    lb = f.get("lb_link")
    if dash(lb):
        return None
    try:
        r = SESSION.get(lb.strip(), headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/126",
                                             "Accept-Language": "en-US"}, timeout=20)
        m = re.search(r'og:image"\s+content="([^"]+)"', r.text)
        if r.status_code == 200 and m:
            return m.group(1)
    except Exception:
        pass
    return None


def resolve_posters(allfilms):
    cache_p = os.path.join(WORK, "posters.json")
    cache = json.load(open(cache_p)) if os.path.exists(cache_p) else {}
    n = 0
    for f in allfilms:
        key = str(f["id"]) + "|" + str(f.get("imdb_id") or "")
        if cache.get(key):
            f["_poster"] = cache[key]
            continue
        f["_poster"] = fetch_poster(f) or fetch_poster_lb(f)
        cache[key] = f["_poster"]
        n += 1
        if n % 25 == 0:
            json.dump(cache, open(cache_p, "w"))
            print(f"poster {n}...", flush=True)
        time.sleep(0.25)
    json.dump(cache, open(cache_p, "w"))
    ok = sum(1 for f in allfilms if f.get("_poster"))
    print(f"posterlar: {ok}/{len(allfilms)}")


def hydrate_posters(allfilms):
    cache_p = os.path.join(WORK, "posters.json")
    cache = json.load(open(cache_p)) if os.path.exists(cache_p) else {}
    for f in allfilms:
        key = str(f["id"]) + "|" + str(f.get("imdb_id") or "")
        f["_poster"] = cache.get(key)


# ---------------------------------------------------------------- metin

def score_line(f):
    parts = []
    def add(label, val, suffix=""):
        if not dash(val):
            parts.append(f"{label} **{val}{suffix}**")
    add("IMDb", f.get("imdb_puani"), "/10")
    add("Letterboxd", f.get("lb_puani"), "/5")
    add("Metascore", f.get("metascore"))
    add("RT", f.get("rotten_puani"))
    add("TMDb", f.get("tmdb_puani"))
    icm_l, icm_f = f.get("icm_lists"), f.get("icm_favs")
    if not dash(icm_l) or not dash(icm_f):
        parts.append(f"ICM **{icm_l if not dash(icm_l) else 0} liste / {icm_f if not dash(icm_f) else 0} fav**")
    return " · ".join(parts)


def depth_line(f):
    lbl = [("Düşünsel", "dusunsel_yogunluk"), ("Psikolojik", "psikolojik_mekanizma"),
           ("Diyalog", "diyalog"), ("Olay örgüsü", "olay_orgusu"),
           ("Sembolik", "sembolik_katman"), ("Politik", "politik_agirlik"),
           ("Felsefi", "felsefi_yogunluk"), ("Ezoterik", "ezoterik_yogunluk"),
           ("Fikir-karakter", "fikir_karakter_butunlesmesi")]
    parts = [f"{n} **{f[k]}**" for n, k in lbl if not dash(f.get(k))]
    return " · ".join(parts)


def link_line(f):
    parts = []
    imdb = f.get("imdb_link")
    if dash(imdb) and not dash(f.get("imdb_id")):
        imdb = f"https://www.imdb.com/title/{f['imdb_id']}/"
    for label, v in [("IMDb", imdb), ("Letterboxd", f.get("lb_link")),
                     ("TMDb", f.get("tmdb_link")), ("Rotten", f.get("rotten_link")),
                     ("ICM", f.get("icm_link")), ("Fragman", f.get("fragman_link"))]:
        if not dash(v):
            parts.append(f"[{label}]({v})")
    return " · ".join(parts)


def title_of(f):
    t = str(f.get("ingilizce_adi") or f.get("orijinal_adi") or "Adsız").strip()
    y = f.get("yili")
    return f"{t} ({y})" if not dash(y) else t


def chunks(text, limit=1900):
    """Uzun metni paragraf sınırlarından böler."""
    out, cur = [], ""
    for para in re.split(r"(\n\n+)", text):
        if len(cur) + len(para) > limit:
            if cur.strip():
                out.append(cur.rstrip())
            cur = ""
            while len(para) > limit:
                out.append(para[:limit])
                para = para[limit:]
        cur += para
    if cur.strip():
        out.append(cur.rstrip())
    return out


def film_messages(f, forum_label):
    """Bir film kaydının Discord mesajları (starter + devamlar)."""
    msgs = []
    title = title_of(f)
    card = []
    if f.get("_poster"):
        card.append(f["_poster"])
    card.append(f"-# {SERVER} · {forum_label} · Kayıt")
    card.append(f"# {title}")
    meta = []
    for lbl, k, suf in [("Yönetmen", "yonetmen", ""), ("Tür", "tur", ""),
                        ("Süre", "sure", " dk"), ("Dil", "dil", ""), ("Yıl", "yili", "")]:
        v = f.get(k)
        if not dash(v):
            meta.append(f"**{lbl}:** {v}{suf}")
    card.append("> " + " · ".join(meta))
    org = f.get("orijinal_adi")
    if not dash(org) and org.strip() != (f.get("ingilizce_adi") or "").strip():
        card.append(f"*Orijinal adı: {org}*")
    uyg, gere = f.get("sana_uygunluk"), f.get("uygunluk_gerekcesi")
    if not dash(uyg):
        guv = f.get("uygunluk_guveni")
        g = f" (güven %{int(float(guv)*100)})" if not dash(guv) else ""
        line = f"**Sana uygunluk: {uyg}**{g}"
        if not dash(gere):
            line += f" — {gere}"
        card.append(line)
    if not dash(f.get("konu_ozeti")):
        card.append("")
        card.append(str(f["konu_ozeti"]).strip())
    sc = score_line(f)
    if sc:
        card.append("\n### Puanlar\n" + sc)
    dl = depth_line(f)
    if dl:
        card.append("\n### Katmanlar (0–10)\n" + dl)
    ll = link_line(f)
    if ll:
        card.append("\n### Bağlantılar\n" + ll)
    foot = f"-# nMDB arşiv kaydı #{f.get('arsiv_no','?')}"
    card.append("\n" + foot)
    body = "\n".join(card)
    for c in chunks(body, 1950):
        msgs.append(c)

    if f.get("_analiz"):
        sections = chunks("-# " + SERVER + " · " + title + " · Derin Analiz\n" + f["_analiz"].strip(), 1900)
        msgs.extend(sections)
    if not dash(f.get("tartismalar_ve_notlar")):
        sec = "### Tartışmalar & Notlar\n" + str(f["tartismalar_ve_notlar"]).strip()
        for c in chunks("-# " + SERVER + " · " + title + " · Notlar\n" + sec, 1900):
            msgs.append(c)
    return msgs


def index_messages(forum_label, entries):
    """Forum başındaki sabit dizin kaydının mesajları."""
    lines = [f"-# {SERVER} · {forum_label} · Dizin", f"# {forum_label} — Kayıt Dizini",
             f"{len(entries)} kayıt — alfabetik:", ""]
    for e in entries:
        lines.append(f"• **{e}**")
    return chunks("\n".join(lines), 1950)


# ---------------------------------------------------------------- yapı

STRUCTURE = [
    ("GİRİŞ & REHBER", [
        ("text", "hosgeldin", "The Film Archive — kişisel film arşivinin salt-okunur vitrini"),
        ("text", "arsiv-dizini", "Kategori ve forum dizini"),
        ("text", "nasil-okunur", "Bir film kaydı nasıl okunur; puan ve katman rehberi"),
        ("text", "a-z-indeks", "Tüm kayıtların alfabetik dizini"),
        ("text", "kaynak-politikasi", "Veri kaynakları ve çözümleme yöntemi"),
    ]),
    ("ANA ARŞİV", [
        ("forum", "filmler", "Koleksiyondaki filmler — künye, puanlar ve derin analiz. — Filmler"),
        ("forum", "diziler", "Koleksiyondaki diziler — künye, puanlar ve derin analiz. — Diziler"),
        ("forum", "belgeseller", "Koleksiyondaki belgeseller. — Belgeseller"),
        ("forum", "animeler", "Koleksiyondaki animeler. — Animeler"),
    ]),
    ("KEŞİFLER & ÖNERİLER", [
        ("forum", "protokol-kesifleri", "Film-protokol süzgecinden geçen yeni adaylar. — Protokol Keşifleri"),
        ("forum", "kurator-kesifleri", "Küratörlü keşif listeleri (v1 + v2). — Küratör Keşifleri"),
    ]),
    ("KÜNYE", [
        ("forum", "yonetmenler", "Yönetmen başına künye kartı — arşivdeki filmleriyle. — Yönetmenler"),
    ]),
    ("DİĞER SUNUCULARIMIZ", [
        ("text", "diger-sunucularimiz", "Aynı arşiv ailesindeki diğer sunucular"),
    ]),
]


def build_structure():
    chans = guild_channels()
    cat_by_name = {c["name"]: c for c in chans if c.get("type") == 4}
    ch_by_name = {(c.get("parent_id"), c["name"]): c for c in chans if c.get("type") in (0, 15)}
    ow = [{"id": EVERYONE, "type": 0, "allow": "0", "deny": DENY}]
    out = {"categories": {}, "channels": {}, "forums": {}}
    for cat_name, items in STRUCTURE:
        cat = cat_by_name.get(cat_name)
        if not cat:
            cat = post(f"/guilds/{GUILD}/channels",
                       json={"name": cat_name, "type": 4, "permission_overwrites": ow})
            print("category:", cat_name, cat["id"], flush=True)
            time.sleep(0.3)
        out["categories"][cat_name] = cat["id"]
        for kind, name, topic in items:
            key = (cat["id"], name)
            ch = ch_by_name.get(key)
            if not ch:
                payload = {"name": name, "parent_id": cat["id"], "topic": topic,
                           "permission_overwrites": ow}
                if kind == "forum":
                    payload["type"] = 15
                    payload["default_auto_archive_duration"] = 60
                else:
                    payload["type"] = 0
                ch = post(f"/guilds/{GUILD}/channels", json=payload)
                print(f"  {kind} {name}: {ch['id']}", flush=True)
                time.sleep(0.3)
            out["forums" if kind == "forum" else "channels"][name] = {"id": ch["id"], "cat": cat_name}
    json.dump(out, open(os.path.join(WORK, "structure.json"), "w"), ensure_ascii=False, indent=1)
    return out


def forum_label(slug):
    return {"filmler": "Filmler", "diziler": "Diziler", "belgeseller": "Belgeseller",
            "animeler": "Animeler", "protokol-kesifleri": "Protokol Keşifleri",
            "kurator-kesifleri": "Küratör Keşifleri", "yonetmenler": "Yönetmenler"}[slug]


# ---------------------------------------------------------------- rehber

def guide_contents(struct, counts):
    F = struct["forums"]
    return {
        "hosgeldin": (
            f"-# {SERVER} · Hoşgeldin\n# The Film Archive\n"
            "Kişisel film arşivinin ve protokol süzgeçli keşif listelerinin salt-okunur vitrini.\n\n"
            "## Nasıl kullanılır\n"
            "• Her kategori bir tema, her forum bir kayıt defteridir; her film/dizi kendi odasındadır.\n"
            "• Kayıtlar künye kartı + gerektiğinde **Derin Analiz** ve **Tartışmalar & Notlar** devam mesajları hâlinde yazılmıştır; çoğu kayıt afişiyle açılır.\n"
            "• Her forumun başında sabitlenmiş **DİZİN** kaydı vardır; hızlı atlama için `#a-z-indeks` kanalını kullanın.\n"
            "• `/ara` komutuyla Lexicanum tüm arşivde arama yapar.\n\n"
            "## Kurallar\n"
            "• Sunucu salt-okunurdur: yazma kapalı, okuma ve arama serbest.\n"
            "• Puanlar IMDb/Letterboxd/Metascore/Rotten Tomatoes/TMDb/ICM kayıtlarına, analizler nMDB'nin AI çözümlemesine dayanır; hata bildirimi için sunucu sahibine ulaşın."
        ),
        "arsiv-dizini": (
            f"-# {SERVER} · Arşiv Dizini\n# Arşiv Dizini\n"
            f"**ANA ARŞİV** — koleksiyondaki {counts['arsiv']} kayıt\n"
            f"• `filmler` → {counts['filmler']} kayıt\n"
            f"• `diziler` → {counts['diziler']} kayıt\n"
            f"• `belgeseller` → {counts['belgeseller']} kayıt\n"
            f"• `animeler` → {counts['animeler']} kayıt\n\n"
            f"**KEŞİFLER & ÖNERİLER** — arşive girmemiş {counts['kesif']} aday\n"
            f"• `protokol-kesifleri` → {counts['protokol']} kayıt (film-protokol süzgeci)\n"
            f"• `kurator-kesifleri` → {counts['kurator']} kayıt (küratörlü listeler)\n\n"
            f"**KÜNYE**\n• `yonetmenler` → {counts['yonetmen']} kayıt\n\n"
            "Hızlı atlama için: `#a-z-indeks` · puan alanlarının anlamı için: `#nasil-okunur`"
        ),
        "nasil-okunur": (
            f"-# {SERVER} · Nasıl Okunur\n# Bir film kaydı nasıl okunur?\n\n"
            "## Künye kartı\n"
            "Başlık, yönetmen/tür/süre/dil satırı, özet ve puanlar tek mesajda toplanır.\n\n"
            "## Puanlar\n"
            "**IMDb /10** · **Letterboxd /5** · **Metascore /100** · **RT %** · **TMDb /10** · **ICM** liste/fav sayısı.\n\n"
            "## Sana uygunluk\n"
            "nMDB'nin kullanıcı-profiline göre hesapladığı 5 üzerinden uyum puanı; parantezdeki güven yüzdesi tahminin sağlamlığıdır.\n\n"
            "## Katmanlar (0–10)\n"
            "AI çözümlemesinin ölçtüğü boyutlar: Düşünsel · Psikolojik · Diyalog · Olay örgüsü · Sembolik · Politik · Felsefi · Ezoterik · Fikir-karakter bütünleşmesi.\n\n"
            "## Devam mesajları\n"
            "Derin Analiz bölümleri (ayrıntılı konu, tez, hikâye motoru, olay örgüsü, felsefi çatışma, psikolojik mekanizmalar, diyalogların işlevi, sembolizm…) ve varsa **Tartışmalar & Notlar** kaydın içinde ayrı mesajlar olarak durur."
        ),
        "kaynak-politikasi": (
            f"-# {SERVER} · Kaynak Politikası\n# Kaynak politikası\n\n"
            "• **Künye & puanlar:** IMDb, Letterboxd, Metascore, Rotten Tomatoes, TMDb ve iCheckMovies kayıtları; doğrulama tarihi her kaydın verisindedir.\n"
            "• **Özet & derin analiz:** nMDB arşivine işlenmiş AI çözümlemeleri (model izleri kayıt altındadır).\n"
            "• **Keşifler:** `film-protocol` ve küratörlü liste süzgeçlerinden geçen adaylar; arşive girmiş değillerdir.\n"
            "• **Afişler:** TMDb (themoviedb.org) medya kitaplığından bağlanır.\n"
            "• Bu arşiv kişisel bir katalog vitrini olarak derlenmiştir; listeler pazarlama değil kayıt amaçlıdır."
        ),
    }


def siblings_text():
    names = {"1551561397031407626": "The Imperial Archive (Warhammer 40.000)",
             "1551907622259793991": "The Trench Archive (Trench Crusade)",
             "1551907883497558050": "Black RPG Archive",
             "1552487874631307284": "Codex Mythica (Mitoloji)"}
    lines = [f"-# {SERVER} · Diğer Sunucularımız", "# Diğer Sunucularımız",
             "Aynı arşiv ailesindeki salt-okunur sunucular:", ""]
    for gid, label in names.items():
        inv = None
        chans = get(f"/guilds/{gid}/channels") or []
        pick = next((c for c in chans if c.get("type") == 0), chans[0] if chans else None)
        if pick:
            try:
                inv = post(f"/channels/{pick['id']}/invites",
                           json={"max_age": 0, "max_uses": 0, "unique": True})
            except Exception as e:
                print("invite fail", gid, e)
        lines.append(f"• **{label}** — https://discord.gg/{inv['code']}" if inv
                     else f"• **{label}**")
        time.sleep(0.4)
    return "\n".join(lines)


def az_text(main, kesifler):
    rows = []
    for f in main:
        rows.append((title_of(f), "Arşiv"))
    for f in kesifler:
        rows.append((title_of(f), "Keşif"))
    rows.sort(key=lambda x: norm(x[0]))
    out = [f"-# {SERVER} · A–Z İndeks", "# A–Z İndeks",
           f"{len(rows)} kayıt — Arşiv + Keşifler, alfabetik:", ""]
    cur = ""
    for title, tag in rows:
        ch = title[0].upper()
        if ch != cur:
            cur = ch
            out.append(f"\n## {cur}")
        out.append(f"• **{title}** · {tag}")
    return chunks("\n".join(out), 1950)


# ---------------------------------------------------------------- post

def run_posts(main, kesifler, struct):
    state_p = os.path.join(WORK, "post_state.json")
    state = json.load(open(state_p)) if os.path.exists(state_p) else {"done": {}, "indexes": {}}

    def save():
        json.dump(state, open(state_p, "w"), ensure_ascii=False)

    groups = [
        ("filmler", [f for f in main if f["kategori"] == "Film"]),
        ("diziler", [f for f in main if f["kategori"] == "Dizi"]),
        ("belgeseller", [f for f in main if f["kategori"] == "Belgesel"]),
        ("animeler", [f for f in main if f["kategori"] == "Anime"]),
        ("protokol-kesifleri", [f for f in kesifler if f.get("uygunluk_kaynagi") == "film-protocol-2026-09-14-v1"]),
        ("kurator-kesifleri", [f for f in kesifler if f.get("uygunluk_kaynagi") != "film-protocol-2026-09-14-v1"]),
    ]

    for slug, films in groups:
        films.sort(key=lambda f: norm(title_of(f)))
        fid = struct["forums"][slug]["id"]
        label = forum_label(slug)
        if slug not in state["indexes"]:
            msgs = index_messages(label, [title_of(f) for f in films])
            t = post(f"/channels/{fid}/threads",
                     json={"name": f"{label} — Kayıt Dizini",
                           "message": {"content": msgs[0]},
                           "applied_tags": []})
            tid = t["id"]
            for extra in msgs[1:]:
                post(f"/channels/{tid}/messages", json={"content": extra})
                time.sleep(0.3)
            try:
                patch(f"/channels/{tid}", json={"flags": 2})
            except Exception as e:
                print("pin fail:", e)
            state["indexes"][slug] = tid
            save()
            print(f"[{slug}] index post ok", flush=True)
        for f in films:
            key = slug + "|" + str(f["id"]) + "|" + title_of(f)
            if key in state["done"]:
                continue
            msgs = film_messages(f, label)
            name = title_of(f)[:95]
            t = post(f"/channels/{fid}/threads",
                     json={"name": name, "message": {"content": msgs[0]},
                           "applied_tags": []})
            tid = t["id"]
            for extra in msgs[1:]:
                post(f"/channels/{tid}/messages", json={"content": extra})
                time.sleep(0.35)
            state["done"][key] = tid
            save()
            if len(state["done"]) % 10 == 0:
                print(f"posts: {len(state['done'])}", flush=True)
            time.sleep(0.35)

    # yonetmenler
    slug = "yonetmenler"
    fid = struct["forums"][slug]["id"]
    label = forum_label(slug)
    by_dir = {}
    for f in main + kesifler:
        d = (f.get("yonetmen") or "").strip()
        if dash(d) or d == "Çeşitli yönetmenler":
            continue
        by_dir.setdefault(d, []).append(f)
    names = sorted(by_dir, key=lambda x: norm(x.split()[-1]))
    if slug not in state["indexes"]:
        msgs = index_messages(label, names)
        t = post(f"/channels/{fid}/threads",
                 json={"name": f"{label} — Kayıt Dizini", "message": {"content": msgs[0]}})
        tid = t["id"]
        for extra in msgs[1:]:
            post(f"/channels/{tid}/messages", json={"content": extra})
            time.sleep(0.3)
        try:
            patch(f"/channels/{tid}", json={"flags": 2})
        except Exception as e:
            print("pin fail:", e)
        state["indexes"][slug] = tid
        save()
    for name in names:
        key = slug + "|" + name
        if key in state["done"]:
            continue
        works = sorted(by_dir[name], key=lambda f: str(f.get("yili") or ""))
        card = [f"-# {SERVER} · Yönetmenler · Kayıt", f"# {name}",
                f"> **Kayıt sayısı:** {len(works)}", ""]
        for w in works:
            uyg = f" — uygunluk {w['sana_uygunluk']}" if not dash(w.get("sana_uygunluk")) else ""
            card.append(f"• **{title_of(w)}**{uyg}")
        msgs = chunks("\n".join(card), 1950)
        t = post(f"/channels/{fid}/threads",
                 json={"name": name[:95], "message": {"content": msgs[0]}})
        tid = t["id"]
        for extra in msgs[1:]:
            post(f"/channels/{tid}/messages", json={"content": extra})
            time.sleep(0.3)
        state["done"][key] = tid
        save()
        if len(state["done"]) % 10 == 0:
            print(f"posts: {len(state['done'])}", flush=True)
        time.sleep(0.3)


def run_guide(main, kesifler, struct):
    counts = {"arsiv": len(main), "filmler": sum(1 for f in main if f["kategori"] == "Film"),
              "diziler": sum(1 for f in main if f["kategori"] == "Dizi"),
              "belgeseller": sum(1 for f in main if f["kategori"] == "Belgesel"),
              "animeler": sum(1 for f in main if f["kategori"] == "Anime"),
              "kesif": len(kesifler),
              "protokol": sum(1 for f in kesifler if f.get("uygunluk_kaynagi") == "film-protocol-2026-09-14-v1"),
              "kurator": sum(1 for f in kesifler if f.get("uygunluk_kaynagi") != "film-protocol-2026-09-14-v1")}
    by_dir = {f.get("yonetmen") for f in main + kesifler}
    by_dir.discard(None); by_dir.discard("Çeşitli yönetmenler")
    counts["yonetmen"] = len(by_dir)
    for slug, text in guide_contents(struct, counts).items():
        cid = struct["channels"][slug]["id"]
        post(f"/channels/{cid}/messages", json={"content": text})
        print("guide:", slug, flush=True)
        time.sleep(0.4)
    cid = struct["channels"]["diger-sunucularimiz"]["id"]
    post(f"/channels/{cid}/messages", json={"content": siblings_text()})
    print("guide: diger-sunucularimiz", flush=True)


def run_az(main, kesifler, struct):
    cid = struct["channels"]["a-z-indeks"]["id"]
    for m in az_text(main, kesifler):
        post(f"/channels/{cid}/messages", json={"content": m})
        time.sleep(0.4)
    print("a-z-indeks ok", flush=True)


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    main_db, kesifler = split_dbs()
    if phase in ("prep", "all"):
        resolve_posters(main_db + kesifler)
    else:
        hydrate_posters(main_db + kesifler)
    if phase == "prep":
        return
    struct_p = os.path.join(WORK, "structure.json")
    if phase in ("structure", "all") or not os.path.exists(struct_p):
        struct = build_structure()
    else:
        struct = json.load(open(struct_p))
    if phase in ("guide", "all"):
        run_guide(main_db, kesifler, struct)
    if phase in ("posts", "all"):
        run_posts(main_db, kesifler, struct)
    if phase in ("az", "all"):
        run_az(main_db, kesifler, struct)
    print("DONE", phase)


if __name__ == "__main__":
    main()
