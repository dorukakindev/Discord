import requests, time, json, os, sys

TOKEN = os.environ["DISCORD_BOT_TOKEN_WH40K"]
BASE = "https://discord.com/api/v10"
GUILD = "1551561397031407626"
S = requests.Session()
S.headers.update({"Authorization": f"Bot {TOKEN}"})

def req(method, path, retries=6, **kw):
    for i in range(retries):
        try:
            r = S.request(method, BASE + path, timeout=30, **kw)
        except requests.exceptions.RequestException:
            if i == retries - 1:
                raise
            time.sleep(1.5 * (i + 1))
            continue
        if r.status_code == 429:
            wait = r.json().get("retry_after", 1.0)
            time.sleep(wait + 0.1)
            continue
        if r.status_code >= 500:
            time.sleep(1.5 * (i + 1))
            continue
        if r.status_code == 404:
            return None
        r.raise_for_status()
        if r.status_code == 204:
            return None
        return r.json()
    raise RuntimeError(f"rate limited / failing: {method} {path}")

def get(path, **kw): return req("GET", path, **kw)
def post(path, **kw): return req("POST", path, **kw)
def patch(path, **kw): return req("PATCH", path, **kw)
def delete(path, **kw): return req("DELETE", path, **kw)

def guild_channels():
    return get(f"/guilds/{GUILD}/channels")

def channel_messages(cid, limit=100):
    out, before = [], None
    while True:
        batch = get(f"/channels/{cid}/messages", params={"limit": min(100, limit - len(out)), **({"before": before} if before else {})})
        if not batch: break
        out.extend(batch)
        if len(batch) < 100 or len(out) >= limit: break
        before = batch[-1]["id"]
    return out

def forum_threads(cid):
    """Active + archived public threads of a forum channel."""
    out = []
    g = get(f"/guilds/{GUILD}/threads/active")
    for t in (g.get("threads", []) if g else []):
        if t.get("parent_id") == cid:
            out.append(t)
    seen = {t["id"] for t in out}
    before = None
    while True:
        params = {"limit": 100}
        if before: params["before"] = before
        r = get(f"/channels/{cid}/threads/archived/public", params=params)
        if not r: break
        ths = r.get("threads", [])
        out.extend(t for t in ths if t["id"] not in seen)
        if not r.get("has_more") or not ths: break
        before = ths[-1]["thread_metadata"]["archive_timestamp"]
    return out

if __name__ == "__main__":
    chans = guild_channels()
    print("total channels:", len(chans))
    import collections
    types = collections.Counter(c["type"] for c in chans)
    print(types)
