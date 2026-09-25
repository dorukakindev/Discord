"""Lexicanum kayıt indeksini üretir: tüm forum başlıklarını tarar,
title -> (sunucu, kategori, forum, link) haritası data/index.json'a yazar.
Kullanım: DISCORD_TOKEN=... python3 build_index.py"""
import os
import sys
import time

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.jsonio import read_json, write_json_atomic  # noqa: E402

TOKEN = os.environ['DISCORD_TOKEN']
H = {'Authorization': 'Bot ' + TOKEN, 'Content-Type': 'application/json'}
B = 'https://discord.com/api/v10'
HERE = os.path.dirname(os.path.abspath(__file__))
GUILDS = read_json(os.path.join(HERE, 'data', 'guilds.json'), default={})


def req(m, u, **kw):
    last = None
    for _ in range(12):
        try:
            r = requests.request(m, B + u, headers=H, timeout=30, **kw)
        except Exception as e:
            last = e
            time.sleep(2)
            continue
        if r.status_code == 429:
            time.sleep(r.json().get('retry_after', 1) + .4)
            continue
        return r
    raise RuntimeError(f'{m} {u} 12 denemede başarısız (son: {last!r})')


def scan(gid):
    """-> (thread_id -> kayıt, hatalı forum adları).

    Forum-bazlı HTTP hataları sessiz `break` yerine `bad` listesine yazılır —
    tek forumun 401/403/500'ü o forumu boş taramasın diye (N14)."""
    chs = req('GET', f'/guilds/{gid}/channels').json()
    cat = {c['id']: c['name'] for c in chs if c.get('type') == 4}
    forums = [c for c in chs if c.get('type') == 15]
    out, bad = {}, []
    for f in forums:
        cname = cat.get(f.get('parent_id'), '')
        before = None
        while True:
            u = f"/channels/{f['id']}/threads/archived/public?limit=100"
            if before:
                u += f'&before={before}'
            r = req('GET', u)
            if r.status_code != 200:
                bad.append(f"{f['name']} ({r.status_code})")
                break
            ts = r.json().get('threads', [])
            for t in ts:
                out[t['id']] = {'t': t['name'], 'g': gid, 'i': t['id'],
                                'f': f['name'], 'c': cname,
                                'l': f'https://discord.com/channels/{gid}/{t["id"]}'}
            if len(ts) < 100:
                break
            before = requests.utils.quote(ts[-1]['thread_metadata']['archive_timestamp'], safe='')
            time.sleep(.25)
    act = req('GET', f'/guilds/{gid}/threads/active')
    if act.status_code != 200:
        bad.append(f'aktif-threadler ({act.status_code})')
    else:
        pf = {c['id']: c for c in chs}
        for t in act.json().get('threads', []):
            p = pf.get(t['parent_id'])
            if p and p.get('type') == 15:
                out[t['id']] = {'t': t['name'], 'g': gid, 'i': t['id'],
                                'f': p['name'], 'c': cat.get(p.get('parent_id'), ''),
                                'l': f'https://discord.com/channels/{gid}/{t["id"]}'}
    return out, bad


def main():
    idx = []
    path = os.path.join(HERE, 'data', 'index.json')
    prev = read_json(path, default=[])
    prev_by_g = {}
    for r in prev:
        prev_by_g[str(r.get('g'))] = prev_by_g.get(str(r.get('g')), 0) + 1
    bad_all = []
    for gid, meta in GUILDS.items():
        recs, bad = scan(gid)
        for b in bad:
            bad_all.append(f"{meta['name']}: {b}")
            print(f'!! {meta["name"]}: forum taraması atlandı — {b}', flush=True)
        for r in recs.values():
            r['s'] = meta['name']
            idx.append(r)
        print(meta['name'], len(recs), flush=True)
        # guild-bazlı koruma: tek sunucu yarıdan fazla eksildiyse yazma
        pg = prev_by_g.get(gid, 0)
        if pg and len(recs) < pg * 0.5:
            raise SystemExit(
                f'REDDEDILDI: {meta["name"]} {pg} -> {len(recs)} kayıt '
                '(yarıdan fazla düşüş — olası tarama hatası); indeks korundu')
        time.sleep(1)
    if prev and len(idx) < len(prev) * 0.9:
        raise SystemExit(
            f'REDDEDILDI: {len(idx)} kayıt, mevcut {len(prev)} kaydın %90 altında — '
            'indeks korundu (olası tarama hatası)')
    write_json_atomic(path, idx)
    if bad_all:
        print('HATALI forumlar:', *bad_all, sep='\n  ')
    print('TOTAL', len(idx))


if __name__ == '__main__':
    main()
