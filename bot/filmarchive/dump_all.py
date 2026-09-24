# -*- coding: utf-8 -*-
"""Live dump of The Film Archive guild -> repo files.

Writes:
  FilmArchive/forumlar/<cat> - <forum>/<post>.md
  FilmArchive/metin-kanallari/<cat>/<chan>.md
  FilmArchive/server_manifest.json
  docs/data/FilmArchive/<san>/<file>.md  (+ _txt/<cat>/<chan>.md for text channels)
  docs/manifest.json (FilmArchive node), docs/index.json (THE FILM ARCHIVE entries)
"""
import json, os, re, time, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dapi import req, get, guild_channels, channel_messages, forum_threads, GUILD

REPO = os.environ.get("DISCORD_REPO", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FILM = os.path.join(REPO, "FilmArchive")
DOCS = os.path.join(REPO, "docs")
SERVER_ID = "FilmArchive"
SERVER_TITLE = "THE FILM ARCHIVE"


def fsafe(name):
    n = re.sub(r'[\\/:*?"<>|]', '-', name).strip().strip('.')
    return n or "unnamed"


def dsan(name):
    return re.sub(r'[^A-Za-z0-9._\-]', '_', name)


def post_text(msgs):
    return "\n\n".join(m["content"] for m in msgs if m.get("content"))


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    chans = guild_channels()
    cats = [c for c in chans if c["type"] == 4]
    catname = {c["id"]: c["name"] for c in cats}
    forums = [c for c in chans if c["type"] == 15]
    texts = [c for c in chans if c["type"] == 0]
    roles = get(f"/guilds/{GUILD}/roles") or []
    roles = [{"id": r["id"], "name": r["name"]} for r in roles]

    guild = get(f"/guilds/{GUILD}") or {}
    manifest = {
        "guild": {"id": GUILD, "name": guild.get("name", "The Film Archive")},
        "roles": roles,
        "categories": [{"id": c["id"], "name": c["name"]} for c in cats],
        "channels": [{"id": c["id"], "name": c["name"], "type": c["type"],
                      "parent": c.get("parent_id")} for c in chans if c["type"] != 4],
        "threads": {},
        "exported": time.strftime("%Y-%m-%d"),
    }

    docs_index_new = []
    docs_forums = []
    docs_texts = []
    forumlar_root = os.path.join(FILM, "forumlar")
    docs_root = os.path.join(DOCS, "data", SERVER_ID)
    written_files = set()

    def mark(p):
        written_files.add(os.path.normpath(p))

    def sweep_stale(root):
        for dirpath, _, files in os.walk(root):
            for fn in files:
                if not fn.endswith(".md"):
                    continue
                fp = os.path.normpath(os.path.join(dirpath, fn))
                if fp not in written_files:
                    os.remove(fp)
                    print("stale removed:", fp)

    cat_children = {}
    for f in forums:
        cat_children.setdefault(catname.get(f.get("parent_id"), "?"), []).append(f)

    # keep category order as in the guild
    for cat, fs in cat_children.items():
        items = []
        for f in sorted(fs, key=lambda x: x["position"]):
            threads = forum_threads(f["id"])
            titles, posts = [], []
            for t in threads:
                tid = t["id"]
                msgs = get(f"/channels/{tid}/messages?limit=100") or []
                msgs.sort(key=lambda m: int(m["id"]))
                txt = post_text(msgs)
                if not txt:
                    continue
                title = t["name"]
                titles.append(title)
                fname = fsafe(title) + ".md"
                fdir = f"{cat} - {f['name']}"
                p1 = os.path.join(forumlar_root, fdir, fname)
                w(p1, txt); mark(p1)
                u = f"data/{SERVER_ID}/" + dsan(fdir) + "/" + dsan(fname)
                p2 = os.path.join(docs_root, dsan(fdir), dsan(fname))
                w(p2, txt); mark(p2)
                posts.append({"title": title, "file": u})
                docs_index_new.append({"s": SERVER_TITLE, "f": f["name"], "t": title, "u": u})
                time.sleep(0.12)
            manifest["threads"][f["name"]] = titles
            items.append({"name": f["name"], "posts": posts})
            print(f"forum {f['name']}: {len(posts)} posts")
        docs_forums.append({"cat": re.sub(r"^\d+・", "", cat), "items": items})

    # ---------- metin-kanallari (+ docs _txt) ----------
    mk_root = os.path.join(FILM, "metin-kanallari")
    txt_root = os.path.join(docs_root, "_txt")
    for c in sorted(texts, key=lambda x: (x.get("parent_id") or "", x["position"])):
        cat = catname.get(c.get("parent_id"), "?")
        msgs = channel_messages(c["id"], limit=500)
        msgs.sort(key=lambda m: int(m["id"]))
        txt = post_text(msgs)
        if not txt:
            continue
        p3 = os.path.join(mk_root, cat, fsafe(c["name"]) + ".md")
        w(p3, txt); mark(p3)
        u = f"data/{SERVER_ID}/_txt/" + dsan(cat) + "/" + dsan(fsafe(c["name"]) + ".md")
        p4 = os.path.join(txt_root, dsan(cat), dsan(fsafe(c["name"]) + ".md"))
        w(p4, txt); mark(p4)
        docs_texts.append({"title": c["name"], "file": u, "grp": cat})
        print(f"text {c['name']}: {len(msgs)} msgs")
        time.sleep(0.15)

    sweep_stale(forumlar_root)
    sweep_stale(mk_root)
    sweep_stale(docs_root)

    w(os.path.join(FILM, "server_manifest.json"), json.dumps(manifest, ensure_ascii=False, indent=2))

    # ---------- docs/manifest.json (FilmArchive node) ----------
    dm_path = os.path.join(DOCS, "manifest.json")
    dm = json.load(open(dm_path, encoding="utf-8"))
    node = next((s for s in dm["servers"] if s.get("id") == SERVER_ID), None)
    if not node:
        node = {"id": SERVER_ID, "title": SERVER_TITLE}
        dm["servers"].append(node)
    node["forums"] = docs_forums
    node["texts"] = docs_texts
    json.dump(dm, open(dm_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # ---------- docs/index.json ----------
    di_path = os.path.join(DOCS, "index.json")
    di = json.load(open(di_path, encoding="utf-8"))
    di = [e for e in di if e.get("s") != SERVER_TITLE] + docs_index_new
    json.dump(di, open(di_path, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("docs index:", len(docs_index_new), "film entries; total", len(di))


if __name__ == "__main__":
    main()
