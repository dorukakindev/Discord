# -*- coding: utf-8 -*-
"""Lexicanum kayıt indeksini üretir: tüm forum başlıklarını tarar,
title -> (sunucu, kategori, forum, link) haritası data/index.json'a yazar.
Kullanım: DISCORD_TOKEN=... python3 build_index.py"""
import json, os, requests, time

TOKEN = os.environ['DISCORD_TOKEN']
H = {'Authorization': 'Bot ' + TOKEN, 'Content-Type': 'application/json'}
B = 'https://discord.com/api/v10'
HERE = os.path.dirname(os.path.abspath(__file__))
GUILDS = json.load(open(os.path.join(HERE, 'data', 'guilds.json')))


def req(m, u, **kw):
    for _ in range(12):
        try:
            r = requests.request(m, B + u, headers=H, timeout=30, **kw)
        except Exception:
            time.sleep(2)
            continue
        if r.status_code == 429:
            time.sleep(r.json().get('retry_after', 1) + .4)
            continue
        return r


def scan(gid):
    chs = req('GET', f'/guilds/{gid}/channels').json()
    cat = {c['id']: c['name'] for c in chs if c.get('type') == 4}
    forums = [c for c in chs if c.get('type') == 15]
    out = {}
    for f in forums:
        cname = cat.get(f.get('parent_id'), '')
        before = None
        while True:
            u = f"/channels/{f['id']}/threads/archived/public?limit=100"
            if before:
                u += f'&before={before}'
            r = req('GET', u)
            if not r or r.status_code != 200:
                break
            ts = r.json().get('threads', [])
            for t in ts:
                out[t['name']] = {'t': t['name'], 'g': gid,
                                  'f': f['name'], 'c': cname,
                                  'l': f'https://discord.com/channels/{gid}/{t["id"]}'}
            if len(ts) < 100:
                break
            before = requests.utils.quote(ts[-1]['thread_metadata']['archive_timestamp'], safe='')
            time.sleep(.25)
    act = req('GET', f'/guilds/{gid}/threads/active')
    if act and act.status_code == 200:
        pf = {c['id']: c for c in chs}
        for t in act.json().get('threads', []):
            p = pf.get(t['parent_id'])
            if p and p.get('type') == 15:
                out[t['name']] = {'t': t['name'], 'g': gid,
                                  'f': p['name'], 'c': cat.get(p.get('parent_id'), ''),
                                  'l': f'https://discord.com/channels/{gid}/{t["id"]}'}
    return out


def main():
    idx = []
    for gid, meta in GUILDS.items():
        recs = scan(gid)
        for r in recs.values():
            r['s'] = meta['name']
            idx.append(r)
        print(meta['name'], len(recs), flush=True)
        time.sleep(1)
    json.dump(idx, open(os.path.join(HERE, 'data', 'index.json'), 'w'),
              ensure_ascii=False)
    print('TOTAL', len(idx))


if __name__ == '__main__':
    main()
