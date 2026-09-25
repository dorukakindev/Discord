"""Discord REST yardımcıları — döküm (`dump_all.py`) ve kurulum
(`build_server.py`) betiklerinin ortak modülü.

Önceden `filmarchive/dapi.py` ve `wh40k/dapi.py` olarak iki ayrışmış kopyaydı;
bu, sağlam olan film sürümünün birleştirilmiş hâli (ağ hatasında geri çekilme,
429/5xx/404/400 ayrımı, 40 sn timeout, 8 deneme).

Yapılandırma — her betik kendi guild'ini bildirir:

    import lib.dapi as dapi
    dapi.configure(guild='1551...')

Token ortamdan okunur: `DISCORD_BOT_TOKEN_WH40K`, yoksa `DISCORD_TOKEN`.
`DRY_RUN=1` ortam değişkeni veya `dapi.set_dry_run()` ile POST/PATCH/DELETE
istekleri yalnız loglanır, gönderilmez — canlı sunucuya yazan betiklerde
önce `--dry-run` ile plan görülebilir.
"""
import os
import time

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TOKEN = os.environ.get('DISCORD_BOT_TOKEN_WH40K') or os.environ.get('DISCORD_TOKEN', '')
GUILD = os.environ.get('DISCORD_GUILD_ID', '')
DRY_RUN = os.environ.get('DRY_RUN', '').lower() in ('1', 'true', 'yes')
BASE = 'https://discord.com/api/v10'
S = requests.Session()
_BOT_ID = None


def _auth():
    if TOKEN:
        S.headers.update({'Authorization': f'Bot {TOKEN}'})


def configure(token=None, guild=None, dry_run=None):
    global TOKEN, GUILD, DRY_RUN
    if token:
        TOKEN = token
    if guild:
        GUILD = str(guild)
    if dry_run is not None:
        DRY_RUN = bool(dry_run)
    _auth()


def set_dry_run(on=True):
    configure(dry_run=on)


_auth()


def req(method, path, retries=8, **kw):
    if DRY_RUN and method != 'GET':
        print(f'[dry-run] {method} {path}', flush=True)
        return {'id': 'dry-run'} if method == 'POST' else None
    for i in range(retries):
        try:
            r = S.request(method, BASE + path, timeout=40, **kw)
        except Exception:
            time.sleep(1.5 * (i + 1))
            continue
        if r.status_code == 429:
            time.sleep(r.json().get('retry_after', 1.0) + 0.15)
            continue
        if r.status_code >= 500:
            time.sleep(1.5 * (i + 1))
            continue
        if r.status_code == 404:
            return None
        if r.status_code == 400:
            raise RuntimeError(f'400 {method} {path}: {r.text[:600]}')
        r.raise_for_status()
        if r.status_code == 204:
            return None
        return r.json()
    raise RuntimeError(f'rate limited / failing: {method} {path}')


def get(path, **kw):
    return req('GET', path, **kw)


def post(path, **kw):
    return req('POST', path, **kw)


def patch(path, **kw):
    return req('PATCH', path, **kw)


def delete(path, **kw):
    return req('DELETE', path, **kw)


def bot_id():
    """Botun kendi kullanıcı id'si (ilk çağrıda önbelleğe alınır)."""
    global _BOT_ID
    if _BOT_ID is None:
        me = get('/users/@me')
        _BOT_ID = me['id'] if me else ''
    return _BOT_ID


def guild_channels():
    return get(f'/guilds/{GUILD}/channels')


def channel_messages(cid, limit=None):
    """Kanal/thread mesajları — Discord'un yeniden→eskiye sırasıyla.
    `limit=None` tam geçmişi sayfalar; sayısal limit en yeni N mesajı verir."""
    out, before = [], None
    while True:
        want = 100 if limit is None else min(100, limit - len(out))
        if want <= 0:
            break
        batch = get(f'/channels/{cid}/messages',
                    params={'limit': want, **({'before': before} if before else {})})
        if not batch:
            break
        out.extend(batch)
        if len(batch) < 100 or (limit is not None and len(out) >= limit):
            break
        before = batch[-1]['id']
    return out


def forum_threads(cid):
    """Forumun aktif + arşivli public thread'leri."""
    out = []
    g = get(f'/guilds/{GUILD}/threads/active')
    for t in (g.get('threads', []) if g else []):
        if t.get('parent_id') == cid:
            out.append(t)
    seen = {t['id'] for t in out}
    before = None
    while True:
        params = {'limit': 100}
        if before:
            params['before'] = before
        r = get(f'/channels/{cid}/threads/archived/public', params=params)
        if not r:
            break
        ths = r.get('threads', [])
        out.extend(t for t in ths if t['id'] not in seen)
        seen.update(t['id'] for t in ths)
        if len(ths) < 100:
            break
        before = ths[-1]['thread_metadata']['archive_timestamp']
        time.sleep(0.2)
    return out
