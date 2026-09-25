"""Live dump of the WH40K guild -> repo files.

Writes:
  Warhammer/forumlar/<cat> - <forum>/<post>.md
  Warhammer/metin-kanallari/<cat>/<chan>.md
  Warhammer/server_manifest.json
  docs/data/Warhammer/<san>/<file>.md  (+ _txt/<cat>/<chan>.md for text channels)
  docs/manifest.json (Warhammer node), docs/index.json (THE IMPERIAL ARCHIVE entries)

Flags: --dry-run (silmeleri sadece raporla), --force-sweep (>%30 stale olsa da sil)
Env: WH40K_GUILD_ID / DISCORD_GUILD_ID, DISCORD_BOT_TOKEN_WH40K veya DISCORD_TOKEN,
     DISCORD_REPO, DRY_RUN
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import dapi  # noqa: E402
from lib.dapi import channel_messages, forum_threads, get, guild_channels  # noqa: E402
from lib.jsonio import read_json, write_json_atomic, write_text  # noqa: E402

REPO = os.environ.get("DISCORD_REPO", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
WAR = os.path.join(REPO, "Warhammer")
DOCS = os.path.join(REPO, "docs")
SERVER_ID = "Warhammer"
SERVER_TITLE = "THE IMPERIAL ARCHIVE"

dapi.configure(guild=os.environ.get("WH40K_GUILD_ID", "1551561397031407626"))
GUILD = dapi.GUILD
DRY = '--dry-run' in sys.argv or dapi.DRY_RUN
FORCE_SWEEP = '--force-sweep' in sys.argv
dapi.set_dry_run(DRY)


def fsafe(name):
    # filesystem-safe name, keep unicode letters like existing dump
    n = re.sub(r'[\\/:*?"<>|]', '-', name).strip().rstrip('.').strip()
    return n or "unnamed"


def dsan(name):
    # docs/data path sanitize: keep [a-zA-Z0-9._-], rest -> _
    return re.sub(r'[^A-Za-z0-9._\-]', '_', name)


def unique_fname(seen, name, uid):
    # Aynı fsafe slug'a ayrışan isimler üst üste yazmasın — thread/kanal id son eki
    base = fsafe(name)
    fname = base + ".md"
    if fname in seen:
        fname = f"{base}-{str(uid)[-4:]}.md"
    if fname in seen:
        fname = f"{base}-{uid}.md"
    seen.add(fname)
    return fname


def post_text(msgs):
    parts = [m["content"] for m in msgs if m.get("content")]
    return "\n\n".join(parts)


def w(path, text):
    write_text(path, text)


def main():
    chans = guild_channels()
    cats = [c for c in chans if c["type"] == 4]
    catname = {c["id"]: c["name"] for c in cats}
    forums = [c for c in chans if c["type"] == 15]
    texts = [c for c in chans if c["type"] == 0]
    roles = get(f"/guilds/{GUILD}/roles") or []
    roles = [{"id": r["id"], "name": r["name"]} for r in roles]

    # ---------- manifest ----------
    manifest = {
        "guild": {"id": GUILD, "name": "The Imperial Archive"},
        "roles": roles,
        "categories": [{"id": c["id"], "name": c["name"]} for c in cats],
        "channels": [{"id": c["id"], "name": c["name"], "type": c["type"],
                      "parent": c.get("parent_id")} for c in chans if c["type"] != 4],
        "threads": {},
        "exported": time.strftime("%Y-%m-%d"),
    }

    # ---------- forumlar + docs/data/Warhammer ----------
    docs_index_new = []   # {s,f,t,u}
    docs_forums = []      # manifest forums for Warhammer server
    docs_texts = []
    forumlar_root = os.path.join(WAR, "forumlar")
    docs_war_root = os.path.join(DOCS, "data", SERVER_ID)
    written_files = set()

    def mark(p):
        written_files.add(os.path.normpath(p))

    def sweep_stale(root):
        stale = []
        for dirpath, _, files in os.walk(root):
            for fn in files:
                if not fn.endswith(".md"):
                    continue
                fp = os.path.normpath(os.path.join(dirpath, fn))
                if fp not in written_files:
                    stale.append(fp)
        total = len(written_files) + len(stale)
        if stale and len(stale) > total * 0.3 and not FORCE_SWEEP:
            print(f"!! sweep ATLANDI: {len(stale)}/{total} dosya stale "
                  "(>%30 — olası döküm hatası). Onay için --force-sweep")
            return
        for fp in stale:
            if DRY:
                print("[dry-run] stale silinecek:", fp)
            else:
                os.remove(fp)
                print("stale removed:", fp)

    cat_children = {}
    for f in forums:
        cat_children.setdefault(catname.get(f.get("parent_id"), "?"), []).append(f)

    for cat, fs in cat_children.items():
        items = []
        for f in sorted(fs, key=lambda x: x["position"]):
            threads = forum_threads(f["id"])          # active + archived public
            titles = []
            posts = []
            seen = set()
            for t in threads:
                tid = t["id"]
                msgs = channel_messages(tid)  # sınırsız — >100 mesajlı kayıtlar kesilmesin
                msgs.sort(key=lambda m: int(m["id"]))
                txt = post_text(msgs)
                if not txt:
                    continue
                title = t["name"]
                titles.append(title)
                fname = unique_fname(seen, title, tid)
                fdir = f"{fsafe(cat)} - {fsafe(f['name'])}"
                p1 = os.path.join(forumlar_root, fdir, fname)
                w(p1, txt); mark(p1)
                u = f"data/{SERVER_ID}/" + dsan(fdir) + "/" + dsan(fname)
                p2 = os.path.join(docs_war_root, dsan(fdir), dsan(fname))
                w(p2, txt); mark(p2)
                posts.append({"title": title, "file": u})
                docs_index_new.append({"s": SERVER_TITLE, "f": f["name"], "t": title, "u": u})
                time.sleep(0.12)
            manifest["threads"][f["name"]] = titles
            items.append({"name": f["name"], "posts": posts})
            print(f"forum {f['name']}: {len(posts)} posts")
        docs_forums.append({"cat": re.sub(r"^\d+・", "", cat), "items": items})

    # ---------- metin-kanallari (+ docs _txt) ----------
    mk_root = os.path.join(WAR, "metin-kanallari")
    txt_root = os.path.join(docs_war_root, "_txt")
    seen_txt = {}
    for c in sorted(texts, key=lambda x: (x.get("parent_id") or "", x["position"])):
        cat = catname.get(c.get("parent_id"), "?")
        msgs = channel_messages(c["id"])
        msgs.sort(key=lambda m: int(m["id"]))
        txt = post_text(msgs)
        if not txt:
            continue
        fname3 = unique_fname(seen_txt.setdefault(cat, set()), c["name"], c["id"])
        p3 = os.path.join(mk_root, fsafe(cat), fname3)
        w(p3, txt); mark(p3)
        u = f"data/{SERVER_ID}/_txt/" + dsan(cat) + "/" + dsan(fname3)
        p4 = os.path.join(txt_root, dsan(cat), dsan(fname3))
        w(p4, txt); mark(p4)
        docs_texts.append({"title": c["name"], "file": u, "grp": cat})
        print(f"text {c['name']}: {len(msgs)} msgs")
        time.sleep(0.15)

    sweep_stale(forumlar_root)
    sweep_stale(mk_root)
    sweep_stale(docs_war_root)

    write_json_atomic(os.path.join(WAR, "server_manifest.json"), manifest, indent=2)

    # ---------- docs/manifest.json (Warhammer node only) ----------
    dm_path = os.path.join(DOCS, "manifest.json")
    dm = read_json(dm_path, default={"servers": []})
    node = next((s for s in dm["servers"] if s.get("id") == SERVER_ID), None)
    if not node:
        node = {"id": SERVER_ID, "title": SERVER_TITLE}
        dm["servers"].append(node)
    node["forums"] = docs_forums
    node["texts"] = docs_texts
    write_json_atomic(dm_path, dm, indent=2)

    # ---------- docs/index.json (replace WH40K entries) ----------
    di_path = os.path.join(DOCS, "index.json")
    di = read_json(di_path, default=[])
    di = [e for e in di if e.get("s") != SERVER_TITLE] + docs_index_new
    write_json_atomic(di_path, di, indent=0)
    print("docs index:", len(docs_index_new), "wh40k entries; total", len(di))


if __name__ == "__main__":
    main()
