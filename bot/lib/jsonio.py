"""utf-8 JSON/metin G/Ç yardımcıları — tüm `open()` çağrılarında kodlama
belirtmek yerine tek noktadan (Windows'ta varsayılan kodlama cp1254 olduğu
için `encoding` olmayan open() Türkçe karakterlerde çöküyordu)."""
import json
import os


def read_json(path, default=None):
    """utf-8 JSON oku; dosya yoksa `default` döndür."""
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def write_json_atomic(path, obj, **kw):
    """tmp + os.replace ile atomik JSON yaz (yarım dosya riski yok)."""
    kw.setdefault('ensure_ascii', False)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, **kw)
    os.replace(tmp, path)


def write_text(path, text):
    """utf-8 metin yaz; üst dizinleri gerekiyorsa oluştur."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
