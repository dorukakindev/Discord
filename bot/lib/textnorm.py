"""Türkçe-duyarlı metin normalizasyonu — arama ve sıralama için tek ortak
tanım (önceden `lexicanum.py` ve `build_server.py` içinde iki ayrı kopyaydı)."""
import re
import unicodedata

_TR = str.maketrans({'ç': 'c', 'Ç': 'c', 'ğ': 'g', 'Ğ': 'g',
                     'ı': 'i', 'İ': 'i', 'ö': 'o', 'Ö': 'o',
                     'ş': 's', 'Ş': 's', 'ü': 'u', 'Ü': 'u'})


def norm(s):
    """Küçük harf, ASCII-only, tek-boşluklu normal form.

    `ı` NFKD ayrışmasına sahip olmadığı için önce Türkçe harfler
    translitere edilir — yoksa 'Sadık' → 'sadk' olur ve 'sadik'
    sorgusu eşleşmez.
    """
    s = str(s or "").translate(_TR)
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', s.lower()).split())
