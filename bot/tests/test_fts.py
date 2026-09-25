import os
import tempfile

from lib.ftsdb import connect, rebuild, search


def mkdb(rows):
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    db = connect(path)
    rebuild(db, rows)
    return db, path


ROWS = [
    ('Adeptus Astartes', 'forum-35', 'warhammer', 'l1',
     'Astartes, Imperium\'un süper askerleridir.\n\nZırhlı savaşçılardır.'),
    ('Stalker', 'film', 'filmarchive', 'l2',
     'Sovyet bilimkurgu filmi. Bölge\'ye girerler.'),
    ('Nurgle', 'tanrilar', 'warhammer', 'l3',
     'Kaos tanrısıdır. Çürüme ve hastalık temsilcisi.'),
]


def test_fts_and_match():
    db, p = mkdb(ROWS)
    rows = search(db, ['astartes'])
    assert rows and rows[0][0] == 'Adeptus Astartes'
    db.close(); os.unlink(p)


def test_fts_or_fallback():
    db, p = mkdb(ROWS)
    rows = search(db, ['astartes', 'kaos'])
    assert rows  # AND yok → OR'a düşer, ikisini de bulur
    db.close(); os.unlink(p)


def test_fts_normed_body_turkish():
    db, p = mkdb(ROWS)
    rows = search(db, ['curume'])  # 'çürüme' → norm 'curume'
    assert rows and rows[0][0] == 'Nurgle'
    db.close(); os.unlink(p)


def test_fts_server_filter():
    db, p = mkdb(ROWS)
    rows = search(db, ['astartes'], server='filmarchive')
    assert rows  # film'de yok → global'e düşer (boş değil)
    rows2 = search(db, ['stalker'], server='filmarchive')
    assert rows2 and rows2[0][3] == 'filmarchive'
    db.close(); os.unlink(p)


def test_fts_empty_terms():
    db, p = mkdb(ROWS)
    assert search(db, []) == []
    db.close(); os.unlink(p)
