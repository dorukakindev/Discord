"""data/lexicanum.db — arşiv gövdelerinin FTS5 indeksini repo .md'lerinden üretir.

Her <Sunucu>/forumlar/**/kayıt.md ve metin-kanallari/**/*.md dosyası bir satır;
link (index.json 'l') (server, normalize-başlık) eşlemesiyle bulunur.
Eşleşmeyen dosyalar url='' kalır — yine aranır, sadece linksiz döner.

Çalıştırma: python3 build_fts.py   (repo kökünde veya bot/ içinden)
İdempotent: DELETE + yeniden insert; ~8000 dosya birkaç dakika."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.ftsdb import connect, rebuild  # noqa: E402
from lib.jsonio import read_json  # noqa: E402
from lib.textnorm import norm  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get('DISCORD_REPO', os.path.dirname(HERE))
DATA = os.path.join(HERE, 'data')

# guild slug -> repo sunucu dizini
SLUG_DIR = {
    'warhammer': 'Warhammer',
    'trench': 'TrenchCrusade',
    'rpg': 'BlackRPG',
    'mythica': 'Mythology',
    'filmarchive': 'FilmArchive',
}


def iter_rows(idx):
    """(title, forum, server_slug, url, body) — forumlar + metin kanalları."""
    for slug, sdir in SLUG_DIR.items():
        for kind in ('forumlar', 'metin-kanallari'):
            root = os.path.join(REPO, sdir, kind)
            if not os.path.isdir(root):
                continue
            for dirpath, _, files in os.walk(root):
                parent = os.path.basename(dirpath)
                forum = (parent.split(' - ', 1)[-1] if kind == 'forumlar'
                         else parent)
                for fn in files:
                    if not fn.endswith('.md'):
                        continue
                    path = os.path.join(dirpath, fn)
                    with open(path, encoding='utf-8') as f:
                        body = f.read()
                    title = fn[:-3]
                    url = idx.get((slug, norm(title)), '')
                    yield title, forum, slug, url, body


def main():
    # index.json 's' = görünen isim ("THE IMPERIAL ARCHIVE") → guilds.json slug
    index = read_json(os.path.join(DATA, 'index.json'), default=[])
    guilds = read_json(os.path.join(DATA, 'guilds.json'), default={})
    name2slug = {m['name']: m['slug'] for m in guilds.values()}
    idx = {(name2slug.get(r.get('s'), r.get('s')), norm(r['t'])): r.get('l', '')
           for r in index}

    t0 = time.time()
    db_path = os.path.join(DATA, 'lexicanum.db')
    db = connect(db_path)
    n = 0
    unmatched = 0
    rows = list(iter_rows(idx))
    for _, _, _, u, _ in rows:
        n += 1
        if not u:
            unmatched += 1
    rebuild(db, rows)
    db.close()
    sz = os.path.getsize(db_path) / 1e6
    print(f'lexicanum.db: {n} kayıt ({sz:.1f} MB), {unmatched} linksiz, '
          f'{time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
