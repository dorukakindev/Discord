# -*- coding: utf-8 -*-
"""Live dump of the WH40K guild -> repo files (branch: devin-wh40k-live-dump)."""
import json, os, re, time, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dapi import req, get, guild_channels, channel_messages, forum_threads, GUILD

REPO = os.environ.get("DISCORD_REPO", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
WAR = os.path.join(REPO, "Warhammer")
DOCS = os.path.join(REPO, "docs")

def fsafe(name):
    # filesystem-safe name, keep unicode letters like existing dump
    n = re.sub(r'[\\/:*?"<>|]', '-', name).strip().strip('.')
    return n or "unnamed"

def dsan(name):
    # docs/data path sanitize: keep [a-zA-Z0-9._-], rest -> _
    return re.sub(r'[^A-Za-z0-9._\-]', '_', name)

def post_text(msgs):
    parts = [m["content"] for m in msgs if m.get("content")]
    return "\n\n".join(parts)

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
    forumlar_root = os.path.join(WAR, "forumlar")
    docs_war_root = os.path.join(DOCS, "data", "Warhammer")
    written_files = set()   # files this dump produced; leftovers are stale

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

    for cat, fs in cat_children.items():
        items = []
        for f in sorted(fs, key=lambda x: x["position"]):
            threads = forum_threads(f["id"])          # active + archived public
            titles = []
            posts = []
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
                u = "data/Warhammer/" + dsan(fdir) + "/" + dsan(fname)
                p2 = os.path.join(docs_war_root, dsan(fdir), dsan(fname))
                w(p2, txt); mark(p2)
                posts.append({"title": title, "file": u})
                docs_index_new.append({"s": "THE IMPERIAL ARCHIVE", "f": f["name"], "t": title, "u": u})
                time.sleep(0.12)
            manifest["threads"][f["name"]] = titles
            items.append({"name": f["name"], "posts": posts})
            print(f"forum {f['name']}: {len(posts)} posts")
        docs_forums.append({"cat": re.sub(r"^\d+・", "", cat), "items": items})

    sweep_stale(forumlar_root)
    sweep_stale(docs_war_root)

    # ---------- metin-kanallari ----------
    mk_root = os.path.join(WAR, "metin-kanallari")
    for c in texts:
        cat = catname.get(c.get("parent_id"), "?")
        msgs = channel_messages(c["id"], limit=500)
        msgs.sort(key=lambda m: int(m["id"]))
        txt = post_text(msgs)
        if not txt:
            continue
        p3 = os.path.join(mk_root, cat, fsafe(c["name"]) + ".md")
        w(p3, txt); mark(p3)
        print(f"text {c['name']}: {len(msgs)} msgs")
        time.sleep(0.15)

    w(os.path.join(REPO, "server_manifest.json"), json.dumps(manifest, ensure_ascii=False, indent=2))

    # ---------- docs/manifest.json (Warhammer node only) ----------
    dm_path = os.path.join(DOCS, "manifest.json")
    dm = json.load(open(dm_path, encoding="utf-8"))
    for s in dm["servers"]:
        if s.get("id") == "Warhammer":
            s["forums"] = docs_forums
            break
    json.dump(dm, open(dm_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # ---------- docs/index.json (replace WH40K entries) ----------
    di_path = os.path.join(DOCS, "index.json")
    di = json.load(open(di_path, encoding="utf-8"))
    di = [e for e in di if e.get("s") != "THE IMPERIAL ARCHIVE"] + docs_index_new
    json.dump(di, open(di_path, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("docs index:", len(docs_index_new), "wh40k entries; total", len(di))

if __name__ == "__main__":
    main()
