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
from dapi import req, get, post, patch, delete, guild_channels, channel_messages, forum_threads, GUILD

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
    add("nMDB", f.get("nutpuan"))
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


def line_chunks(text, limit=1950):
    """Satır listesi içeriklerini (dizinler) satır sınırlarından böler;
    maddelerin ortasına denk gelen kesimler `**` artığı bırakır."""
    out, cur = [], ""
    for ln in text.split("\n"):
        cand = ln if not cur else cur + "\n" + ln
        if len(cand) > limit:
            out.append(cur)
            cur = ln
        else:
            cur = cand
    if cur:
        out.append(cur)
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
    # Discord mesaj içeriğinin kenar boşluklarını kırpar — üretim de aynısını yapsın
    return [m.strip() for m in msgs]


def index_messages(forum_label, entries, sort_note="alfabetik"):
    """Forum başındaki sabit dizin kaydının mesajları.

    entries elemanları `**` ile kapatılmış gövde metni de içerebilir
    (örn. `Title** · Film · IMDb 7.5` → `• **Title** · Film · IMDb 7.5`)."""
    head = "\n".join([f"-# {SERVER} · {forum_label} · Dizin", f"# {forum_label} — Kayıt Dizini",
                       f"{len(entries)} kayıt — {sort_note}:"])
    body = "\n".join(f"• **{e}**" for e in entries)
    return [head] + line_chunks(body)


# ---------------------------------------------------------------- yapı

BANDS = ["4-5-ve-ustu", "4-0-4-5", "3-5-4-0", "3-5-alti"]
BAND_LABELS = {"4-5-ve-ustu": "4.5 ve Üstü", "4-0-4-5": "4.0–4.5",
               "3-5-4-0": "3.5–4.0", "3-5-alti": "3.5 Altı"}
BAND_DESC = {"4-5-ve-ustu": "4.5 ve üstü", "4-0-4-5": "4.0–4.5",
             "3-5-4-0": "3.5–4.0", "3-5-alti": "3.5 altı"}
KAT_SLUG = {"Film": "filmler", "Dizi": "diziler",
            "Belgesel": "belgeseller", "Anime": "animeler"}
KAT_LABELS = {"filmler": "Filmler", "diziler": "Diziler",
              "belgeseller": "Belgeseller", "animeler": "Animeler"}
KAT_CAT = {"filmler": "FİLMLER", "diziler": "DİZİLER",
           "belgeseller": "BELGESELLER", "animeler": "ANİMELER"}
# "bands": kategori kendi puan bant forumlarına bölünür; "single": tek forum
KAT_MODE = {k: "bands" for k in KAT_LABELS}


def kat_items(kat):
    """Bir tür kategorisinin forumları: puan bantları ya da tek forum."""
    lab = KAT_LABELS[kat]
    if KAT_MODE[kat] == "bands":
        return [("forum", f"{kat}-{b}",
                 f"{lab} · uygunluk veya kişisel puan {BAND_DESC[b]} — {lab} · {BAND_LABELS[b]}")
                for b in BANDS]
    return [("forum", kat, f"{lab} kayıtları — {lab}")]


def band_slugs():
    """Ana arşiv kayıtlarının dağıldığı tüm forum slug'ları."""
    out = []
    for kat in KAT_LABELS:
        out += [f"{kat}-{b}" for b in BANDS] if KAT_MODE[kat] == "bands" else [kat]
    return out


def forum_slug_of(f):
    kat = KAT_SLUG.get(f.get("kategori"), "filmler")
    return f"{kat}-{band_of(f)}" if KAT_MODE[kat] == "bands" else kat


STRUCTURE = [
    ("GİRİŞ & REHBER", [
        ("text", "hosgeldin", "The Film Archive — kişisel film arşivinin salt-okunur vitrini"),
        ("text", "arsiv-dizini", "Kategori ve forum dizini"),
        ("text", "nasil-okunur", "Bir film kaydı nasıl okunur; puan ve katman rehberi"),
        ("text", "a-z-indeks", "Tüm kayıtların alfabetik dizini"),
        ("text", "kaynak-politikasi", "Veri kaynakları ve çözümleme yöntemi"),
    ]),
    (KAT_CAT["filmler"], kat_items("filmler")),
    (KAT_CAT["diziler"], kat_items("diziler")),
    (KAT_CAT["belgeseller"], kat_items("belgeseller")),
    (KAT_CAT["animeler"], kat_items("animeler")),
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
        for item in items:
            kind, name, topic = item[:3]
            tag_names = item[3] if len(item) > 3 else []
            key = (cat["id"], name)
            ch = ch_by_name.get(key)
            if not ch:
                payload = {"name": name, "parent_id": cat["id"], "topic": topic,
                           "permission_overwrites": ow}
                if kind == "forum":
                    payload["type"] = 15
                    payload["default_auto_archive_duration"] = 60
                    if tag_names:
                        payload["available_tags"] = [{"name": t} for t in tag_names]
                else:
                    payload["type"] = 0
                ch = post(f"/guilds/{GUILD}/channels", json=payload)
                print(f"  {kind} {name}: {ch['id']}", flush=True)
                time.sleep(0.3)
            elif kind == "forum" and tag_names:
                have = {t["name"] for t in ch.get("available_tags", [])}
                if have != set(tag_names):
                    ch = patch(f"/channels/{ch['id']}", json={
                               "available_tags": [{"name": t} for t in tag_names]})
                    time.sleep(0.3)
            entry = {"id": ch["id"], "cat": cat_name}
            if kind == "forum":
                entry["tags"] = {t["name"]: t["id"] for t in ch.get("available_tags", [])}
            out["forums" if kind == "forum" else "channels"][name] = entry
    json.dump(out, open(os.path.join(WORK, "structure.json"), "w"), ensure_ascii=False, indent=1)
    return out


def forum_label(slug):
    fixed = {"protokol-kesifleri": "Protokol Keşifleri",
             "kurator-kesifleri": "Küratör Keşifleri", "yonetmenler": "Yönetmenler",
             **BAND_LABELS, **KAT_LABELS}
    if slug in fixed:
        return fixed[slug]
    kat, band = slug.split("-", 1)
    return f"{fixed[kat]} · {fixed[band]}"


def fit_score(f):
    """Bant puanı: sana_uygunluk ile kisisel_puan/2'nin maksimumu."""
    try:
        s = float(str(f.get("sana_uygunluk") or "").split("/")[0])
    except ValueError:
        s = 0.0
    try:
        k = float(str(f.get("kisisel_puan") or "")) / 2.0
    except ValueError:
        k = 0.0
    return max(s, k)


def band_of(f):
    s = fit_score(f)
    if s >= 4.5:
        return "4-5-ve-ustu"
    if s >= 4.0:
        return "4-0-4-5"
    if s >= 3.5:
        return "3-5-4-0"
    return "3-5-alti"


def band_entry(f):
    """Bant dizininde tek satır: başlık + puanlar (forum zaten tek tür)."""
    sc = []
    for label, key, suf in [("IMDb", "imdb_puani", "/10"), ("LB", "lb_puani", "/5"),
                            ("nMDB", "nutpuan", "")]:
        if not dash(f.get(key)):
            sc.append(f"{label} {f[key]}{suf}")
    if not dash(f.get("sana_uygunluk")):
        sc.append(f"uyg {f['sana_uygunluk']}")
    return f"{title_of(f)}** · {' · '.join(sc)}"


# ---------------------------------------------------------------- rehber

def counts_of(main, kesifler):
    """Rehber metinlerinin sayaçları: tür kategorisi × puan bandı."""
    c = {"arsiv": len(main), "kesif": len(kesifler),
         "protokol": sum(1 for f in kesifler if f.get("uygunluk_kaynagi") == "film-protocol-2026-09-14-v1"),
         "kurator": sum(1 for f in kesifler if f.get("uygunluk_kaynagi") != "film-protocol-2026-09-14-v1")}
    for kat in KAT_LABELS:
        fs = [f for f in main if KAT_SLUG.get(f.get("kategori")) == kat]
        c[kat] = {"total": len(fs),
                  "b45": sum(1 for f in fs if band_of(f) == "4-5-ve-ustu"),
                  "b40": sum(1 for f in fs if band_of(f) == "4-0-4-5"),
                  "b35": sum(1 for f in fs if band_of(f) == "3-5-4-0"),
                  "b0": sum(1 for f in fs if band_of(f) == "3-5-alti")}
    by_dir = {f.get("yonetmen") for f in main + kesifler}
    by_dir.discard(None); by_dir.discard("Çeşitli yönetmenler")
    c["yonetmen"] = len(by_dir)
    return c


def guide_contents(struct, counts):
    F = struct["forums"]
    kat_lines = []
    for kat in KAT_LABELS:
        k = counts[kat]
        kat_lines.append(f"**{KAT_CAT[kat]}** — {k['total']} kayıt")
        if KAT_MODE[kat] == "bands":
            for b, kn in [("4-5-ve-ustu", "b45"), ("4-0-4-5", "b40"),
                          ("3-5-4-0", "b35"), ("3-5-alti", "b0")]:
                kat_lines.append(f"• `{kat}-{b}` → {k[kn]}")
        else:
            kat_lines.append(f"• `{kat}` → {k['total']}")
    return {
        "hosgeldin": (
            f"-# {SERVER} · Hoşgeldin\n# The Film Archive\n"
            "Kişisel film arşivinin ve protokol süzgeçli keşif listelerinin salt-okunur vitrini.\n\n"
            "## Nasıl kullanılır\n"
            "• Her kategori bir tür (FİLMLER · DİZİLER · BELGESELLER · ANİMELER), altındaki forumlar ise puan bantlarıdır (4.5+ · 4.0–4.5 · 3.5–4.0 · <3.5) — bandı `sana uygunluk` veya `kişisel puan` hangisi yüksekse o belirler; her kayıt kendi odasındadır.\n"
            "• Kayıtlar künye kartı + gerektiğinde **Derin Analiz** ve **Tartışmalar & Notlar** devam mesajları hâlinde yazılmıştır; çoğu kayıt afişiyle açılır.\n"
            "• Her forumun başında sabitlenmiş **DİZİN** kaydı vardır; hızlı atlama için `#a-z-indeks` kanalını kullanın.\n"
            "• `/ara` komutuyla Lexicanum tüm arşivde arama yapar.\n\n"
            "## Kurallar\n"
            "• Sunucu salt-okunurdur: yazma kapalı, okuma ve arama serbest.\n"
            "• Puanlar IMDb/Letterboxd/Metascore/Rotten Tomatoes/TMDb/ICM kayıtlarına, analizler nMDB'nin AI çözümlemesine dayanır; hata bildirimi için sunucu sahibine ulaşın."
        ),
        "arsiv-dizini": (
            f"-# {SERVER} · Arşiv Dizini\n# Arşiv Dizini\n"
            "Kayıtlar tür kategorileri altında puan bantlarına ayrılır (bant = `sana uygunluk` veya `kişisel puan/2`, yüksek olan):\n\n"
            + "\n".join(kat_lines) + "\n\n"
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
            "**IMDb /10** · **Letterboxd /5** · **Metascore /100** · **RT %** · **TMDb /10** · **nMDB /100** · **ICM** liste/fav sayısı.\n\n"
            "## Puan bantları\n"
            "Her tür kategorisinin forumları puana göre ayrılmıştır: bant = `sana uygunluk` ile `kişisel puan` (Letterboxd×2)/2'nin maksimumu; `*-4-5-ve-ustu` en güçlü eşleşmeleri, `*-3-5-alti` en zayıfları toplar. Her forumun dizini puanları satır içinde gösterir.\n\n"
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
    head = "\n".join([f"-# {SERVER} · A–Z İndeks", "# A–Z İndeks",
                        f"{len(rows)} kayıt — Arşiv + Keşifler, alfabetik:"])
    body = []
    cur = ""
    for title, tag in rows:
        ch = title[0].upper()
        if ch != cur:
            cur = ch
            body.append("")
            body.append(f"## {cur}")
        body.append(f"• **{title}** · {tag}")
    return [head] + line_chunks("\n".join(body))


# ---------------------------------------------------------------- post

def run_posts(main, kesifler, struct):
    state_p = os.path.join(WORK, "post_state.json")
    state = json.load(open(state_p)) if os.path.exists(state_p) else {"done": {}, "indexes": {}}

    def save():
        json.dump(state, open(state_p, "w"), ensure_ascii=False)

    groups = [(s, [f for f in main if forum_slug_of(f) == s]) for s in band_slugs()] + [
        ("protokol-kesifleri", [f for f in kesifler if f.get("uygunluk_kaynagi") == "film-protocol-2026-09-14-v1"]),
        ("kurator-kesifleri", [f for f in kesifler if f.get("uygunluk_kaynagi") != "film-protocol-2026-09-14-v1"]),
    ]

    for slug, films in groups:
        is_band = slug in band_slugs()
        if is_band and not films:
            continue
        if is_band:
            films.sort(key=lambda f: (-fit_score(f), norm(title_of(f))))
        else:
            films.sort(key=lambda f: norm(title_of(f)))
        fid = struct["forums"][slug]["id"]
        label = forum_label(slug)
        if slug not in state["indexes"]:
            entries = [band_entry(f) for f in films] if is_band else [title_of(f) for f in films]
            msgs = index_messages(label, entries,
                                  "uygunluk sırası" if is_band else "alfabetik")
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
            tag_id = struct["forums"][slug].get("tags", {}).get(f.get("kategori"))
            t = post(f"/channels/{fid}/threads",
                     json={"name": name, "message": {"content": msgs[0]},
                           "applied_tags": [tag_id] if tag_id else []})
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
    for slug, text in guide_contents(struct, counts_of(main, kesifler)).items():  # noqa: E501
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


def run_bands(main, kesifler, struct):
    """Eski kategori forumlarının kayıtlarını sana-uygunluk bant forumlarına taşır.

    Thread'ler taşınamadığı için yeniden oluşturulur (kartlar film_messages ile
    yeniden üretilir → nutpuan da eklenir), eski forum komple silinir.
    Band dizinleri uygunluk sırasına göre skorlu satırlarla yazılır.
    İdempotent: eski forum yoksa taşıma geçilir.
    """
    state_p = os.path.join(WORK, "post_state.json")
    state = json.load(open(state_p))

    def save():
        json.dump(state, open(state_p, "w"), ensure_ascii=False)

    old_slugs = ["filmler", "diziler", "belgeseller", "animeler"]
    old_forums = {c["name"]: c["id"] for c in guild_channels()
                  if c.get("type") == 15 and c["name"] in old_slugs}
    by_tid = {tid: key for key, tid in state["done"].items()}
    main_by_id = {str(f["id"]): f for f in main}
    old_index_tids = {state["indexes"].get(s) for s in old_slugs}

    for slug in old_slugs:
        fid = old_forums.get(slug)
        if not fid:
            continue
        for t in forum_threads(fid):
            tid = t["id"]
            if tid in old_index_tids:
                continue
            key = by_tid.get(tid)
            f = main_by_id.get(key.split("|")[1]) if key else None
            if f is None:
                print("!! bilinmeyen thread:", tid, t["name"], flush=True)
                continue
            band = band_of(f)
            label = forum_label(band)
            nfid = struct["forums"][band]["id"]
            tag_id = struct["forums"][band].get("tags", {}).get(f.get("kategori"))
            msgs = film_messages(f, label)
            nt = post(f"/channels/{nfid}/threads",
                      json={"name": t["name"], "message": {"content": msgs[0]},
                            "applied_tags": [tag_id] if tag_id else []})
            for extra in msgs[1:]:
                post(f"/channels/{nt['id']}/messages", json={"content": extra})
                time.sleep(0.3)
            delete(f"/channels/{tid}")
            del state["done"][key]
            state["done"][f"{band}|{f['id']}|{title_of(f)}"] = nt["id"]
            save()
            print("moved:", t["name"], "->", band, flush=True)
            time.sleep(0.35)
        delete(f"/channels/{fid}")
        state["indexes"].pop(slug, None)
        save()
        print("deleted old forum:", slug, flush=True)

    # bant dizinleri
    for b in BANDS:
        if b in state["indexes"]:
            continue
        films = [f for f in main if band_of(f) == b]
        films.sort(key=lambda f: (-fit_score(f),
                                  norm(title_of(f))))
        msgs = index_messages(forum_label(b), [band_entry(f) for f in films],
                              "uygunluk sırası")
        t = post(f"/channels/{struct['forums'][b]['id']}/threads",
                 json={"name": f"{forum_label(b)} — Kayıt Dizini",
                       "message": {"content": msgs[0]}, "applied_tags": []})
        for extra in msgs[1:]:
            post(f"/channels/{t['id']}/messages", json={"content": extra})
            time.sleep(0.3)
        try:
            patch(f"/channels/{t['id']}", json={"flags": 2})
        except Exception as e:
            print("pin fail:", e)
        state["indexes"][b] = t["id"]
        save()
        print(f"[{b}] index ok ({len(films)} kayıt)", flush=True)

    # rehber kanallarının metinleri
    for slug, text in guide_contents(struct, counts_of(main, kesifler)).items():
        cid = struct["channels"][slug]["id"]
        msgs = channel_messages(cid, limit=20)
        msgs.reverse()
        if msgs and msgs[0]["content"] != text:
            patch(f"/channels/{cid}/messages/{msgs[0]['id']}", json={"content": text})
            print("guide patched:", slug, flush=True)
            time.sleep(0.3)


def run_split(main, kesifler, struct):
    """Ortak ANA ARŞİV bant forumlarını tür bazlı bant forumlarına böler.

    `4-5-ve-ustu` gibi karma forumlardaki kayıtlar `filmler-4-5-ve-ustu`,
    `diziler-4-5-ve-ustu` ... altına yeniden yazılır (thread taşınamaz);
    eski forum + boşalan ANA ARŞİV kategorisi silinir, yeni dizinler yazılır.
    İdempotent: eski forum yoksa geçilir.
    """
    state_p = os.path.join(WORK, "post_state.json")
    state = json.load(open(state_p))

    def save():
        json.dump(state, open(state_p, "w"), ensure_ascii=False)

    old_forums = {c["name"]: c["id"] for c in guild_channels()
                  if c.get("type") == 15 and c["name"] in BANDS}
    by_tid = {tid: key for key, tid in state["done"].items()}
    main_by_id = {str(f["id"]): f for f in main}
    old_index_tids = {state["indexes"].get(s) for s in BANDS}

    for slug in BANDS:
        fid = old_forums.get(slug)
        if not fid:
            continue
        for t in forum_threads(fid):
            tid = t["id"]
            if tid in old_index_tids:
                continue
            key = by_tid.get(tid)
            f = main_by_id.get(key.split("|")[1]) if key else None
            if f is None:
                print("!! bilinmeyen thread:", tid, t["name"], flush=True)
                continue
            nslug = forum_slug_of(f)
            nfid = struct["forums"][nslug]["id"]
            msgs = film_messages(f, forum_label(nslug))
            nt = post(f"/channels/{nfid}/threads",
                      json={"name": t["name"], "message": {"content": msgs[0]},
                            "applied_tags": []})
            for extra in msgs[1:]:
                post(f"/channels/{nt['id']}/messages", json={"content": extra})
                time.sleep(0.3)
            delete(f"/channels/{tid}")
            del state["done"][key]
            state["done"][f"{nslug}|{f['id']}|{title_of(f)}"] = nt["id"]
            save()
            print("moved:", t["name"], "->", nslug, flush=True)
            time.sleep(0.35)
        delete(f"/channels/{fid}")
        state["indexes"].pop(slug, None)
        save()
        print("deleted old forum:", slug, flush=True)

    # boşalan eski kategori
    for c in guild_channels():
        if c.get("type") == 4 and c["name"] == "ANA ARŞİV":
            delete(f"/channels/{c['id']}")
            print("deleted category: ANA ARŞİV", flush=True)

    # yeni forum dizinleri (uygunluk sırası + satır içi puanlar)
    for nslug in band_slugs():
        if nslug in state["indexes"]:
            continue
        films = [f for f in main if forum_slug_of(f) == nslug]
        if not films:
            continue
        films.sort(key=lambda f: (-fit_score(f),
                                  norm(title_of(f))))
        msgs = index_messages(forum_label(nslug), [band_entry(f) for f in films],
                              "uygunluk sırası")
        t = post(f"/channels/{struct['forums'][nslug]['id']}/threads",
                 json={"name": f"{forum_label(nslug)} — Kayıt Dizini",
                       "message": {"content": msgs[0]}, "applied_tags": []})
        for extra in msgs[1:]:
            post(f"/channels/{t['id']}/messages", json={"content": extra})
            time.sleep(0.3)
        try:
            patch(f"/channels/{t['id']}", json={"flags": 2})
        except Exception as e:
            print("pin fail:", e)
        state["indexes"][nslug] = t["id"]
        save()
        print(f"[{nslug}] index ok ({len(films)} kayıt)", flush=True)

    # hiç kayıt düşmeyen bant forumlarını sil (salt-okunur arşivde çıkmaz sokak)
    for nslug in band_slugs():
        ent = struct["forums"].get(nslug)
        if ent and not any(forum_slug_of(f) == nslug for f in main):
            delete(f"/channels/{ent['id']}")
            print("deleted empty forum:", nslug, flush=True)
            time.sleep(0.3)

    # rehber kanallarının metinleri
    for slug, text in guide_contents(struct, counts_of(main, kesifler)).items():
        cid = struct["channels"][slug]["id"]
        msgs = channel_messages(cid, limit=20)
        msgs.reverse()
        if msgs and msgs[0]["content"] != text:
            patch(f"/channels/{cid}/messages/{msgs[0]['id']}", json={"content": text})
            print("guide patched:", slug, flush=True)
            time.sleep(0.3)


def run_relabel(main, kesifler, struct):
    """Skor etiketi değişikliğini (Nut -> nMDB) canlı içeriğe uygular.

    Kart starter'ı (id == thread id), thread içindeki kart devamı,
    bant dizin thread'leri ve rehber metinleri karşılaştırma-PATCH'i.
    """
    state_p = os.path.join(WORK, "post_state.json")
    state = json.load(open(state_p))
    by_id = {str(f["id"]): f for f in main + kesifler}

    def sync_thread(tid, msgs):
        # channel_messages thread starter'ı da içerir (en eski mesaj) — cur[i] <-> msgs[i]
        cur = channel_messages(tid, limit=50)
        cur.reverse()
        for i, m in enumerate(cur):
            if i >= len(msgs):
                delete(f"/channels/{tid}/messages/{m['id']}")
                print("msg deleted (surplus):", tid, i, flush=True)
                time.sleep(0.3)
                continue
            if m["content"] != msgs[i]:
                patch(f"/channels/{tid}/messages/{m['id']}",
                      json={"content": msgs[i]})
                print("msg relabeled:", tid, i, flush=True)
                time.sleep(0.3)
        for i in range(len(cur), len(msgs)):
            post(f"/channels/{tid}/messages", json={"content": msgs[i]})
            print("msg posted (missing):", tid, i, flush=True)
            time.sleep(0.3)

    for key, tid in state["done"].items():
        slug = key.split("|")[0]
        if slug == "yonetmenler":
            continue
        f = by_id.get(key.split("|")[1])
        if f is None:
            continue
        sync_thread(tid, film_messages(f, forum_label(slug)))

    for b in band_slugs():
        tid = state["indexes"].get(b)
        if not tid:
            continue
        films = [f for f in main if forum_slug_of(f) == b]
        films.sort(key=lambda f: (-fit_score(f),
                                  norm(title_of(f))))
        sync_thread(tid, index_messages(forum_label(b),
                                      [band_entry(f) for f in films],
                                      "uygunluk sırası"))

    for slug, text in guide_contents(struct, counts_of(main, kesifler)).items():
        cid = struct["channels"][slug]["id"]
        cur = channel_messages(cid, limit=20)
        cur.reverse()
        if cur and cur[0]["content"] != text:
            patch(f"/channels/{cid}/messages/{cur[0]['id']}", json={"content": text})
            print("guide relabeled:", slug, flush=True)
            time.sleep(0.3)


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
    if phase in ("bands", "all"):
        run_bands(main_db, kesifler, struct)
    if phase in ("split", "all"):
        run_split(main_db, kesifler, struct)
    if phase in ("relabel", "all"):
        run_relabel(main_db, kesifler, struct)
    if phase in ("posts", "all"):
        run_posts(main_db, kesifler, struct)
    if phase in ("az", "all"):
        run_az(main_db, kesifler, struct)
    print("DONE", phase)


if __name__ == "__main__":
    main()
