"""lexicanum FTS indeksi — arşiv kayıt gövdeleri üzerinde SQLite FTS5 araması.

Şema: `title`+`body` kolonları norm()'lu metin tutar (sorgular da norm()'lu
terimlerle gelir); `disp`/`url`/`forum`/`server`/`orig` UNINDEXED — gösterim,
filtre ve çıkarım. Üretim: `build_fts.py` repo .md dökümlerini + index.json
linklerini eşleyip `data/lexicanum.db` yazar; VM'e koddan bağımsız taşınır
(yoksa /sor eski thread-fetch yoluna düşer)."""
import sqlite3

from lib.textnorm import norm

DDL = (
    'CREATE VIRTUAL TABLE IF NOT EXISTS recs USING fts5('
    'title, body, disp UNINDEXED, url UNINDEXED, forum UNINDEXED, '
    'server UNINDEXED, orig UNINDEXED)'
)


def connect(path):
    db = sqlite3.connect(path)
    db.execute(DDL)
    return db


def rebuild(db, rows):
    """rows: iterable of (title, forum, server, url, body) — ham metin."""
    db.execute('DELETE FROM recs')
    db.executemany(
        'INSERT INTO recs(title, body, disp, url, forum, server, orig) '
        'VALUES (?,?,?,?,?,?,?)',
        [(norm(t), norm(b), t, u, f, s, b) for t, f, s, u, b in rows])
    db.commit()
    db.execute("INSERT INTO recs(recs) VALUES('optimize')")
    db.commit()


def _match(db, q, limit):
    # bm25(recs, ağırlıklar): title(0)=10x, body(1)=1x — başlık eşleşmesi önde
    return db.execute(
        'SELECT disp, url, forum, server, orig FROM recs '
        'WHERE recs MATCH ? ORDER BY bm25(recs, 10.0, 1.0) LIMIT ?',
        (q, limit)).fetchall()


def search(db, terms, server=None, limit=5):
    """Terimleri AND'le; bulamazsa OR'a düş. `server` slug filtresi sonradan
    uygulanır; sunucu daraltması hiç sonuç vermezse globale düşer."""
    if not terms:
        return []
    q = ' '.join(f'"{t}"' for t in terms)
    rows = _match(db, q, limit * 4)
    if not rows and len(terms) > 1:
        q = ' OR '.join(f'"{t}"' for t in terms)
        rows = _match(db, q, limit * 4)
    if server:
        local = [r for r in rows if r[3] == server]
        if local:
            rows = local
    return rows[:limit]
