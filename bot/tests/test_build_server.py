"""build_server.py'nin saf yardımcıları — nMDB/Discord olmadan test edilir."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "filmarchive"))

import build_server as bs  # noqa: E402


def test_fnum():
    assert bs.fnum("4.5") == 4.5
    assert bs.fnum("4.5/5") == 4.5
    assert bs.fnum("yok", 7.0) == 7.0
    assert bs.fnum(None) == 0.0
    assert bs.fnum(None, None) is None


def test_fit_score(film):
    film["sana_uygunluk"], film["kisisel_puan"] = "4.5/5", "8"
    assert bs.fit_score(film) == 4.5
    film["sana_uygunluk"], film["kisisel_puan"] = "-", "9"
    assert bs.fit_score(film) == 4.5   # 9/2 = 4.5 kisisel'den gelir


def test_band_of(film):
    film["sana_uygunluk"], film["kisisel_puan"] = "5/5", "-"
    assert bs.band_of(film) == "4-5-ve-ustu"
    film["sana_uygunluk"] = "4.2/5"
    assert bs.band_of(film) == "4-0-4-5"
    film["sana_uygunluk"] = "3.7/5"
    assert bs.band_of(film) == "3-5-4-0"
    film["sana_uygunluk"] = "2/5"
    assert bs.band_of(film) == "3-5-alti"


def test_chunks_paragraph_boundary():
    t = "a" * 100 + "\n\n" + "b" * 1900
    cs = bs.chunks(t, 1950)
    assert all(len(c) <= 1950 for c in cs)
    assert cs[0].endswith("a" * 100)


def test_chunks_hard_split_long_para():
    cs = bs.chunks("x" * 5000, 1950)
    assert all(len(c) <= 1950 for c in cs)
    assert "".join(cs) == "x" * 5000


def test_line_chunks_no_empty_or_oversize():
    lc = bs.line_chunks("kısa\n" + "x" * 3000 + "\nson", 1950)
    assert all(0 < len(c) <= 1950 for c in lc)
    assert bs.line_chunks("") == ["—"]


def test_band_entry_format(film):
    e = bs.band_entry(film)
    assert e.startswith("**Örnek Film (2020)**")
    assert e.count("**") == 2          # stray `**` yok (H6)
    assert "IMDb 8.1/10" in e and "nMDB 77" in e


def test_index_messages_balanced(film):
    entries = [bs.band_entry(film), "**Düz Başlık**"]
    msgs = bs.index_messages("Filmler · 4.5", entries)
    assert msgs[0].startswith("-# THE FILM ARCHIVE")
    body = msgs[-1]
    assert "• **Örnek Film (2020)** · IMDb" in body
    assert "• **Düz Başlık**" in body
    assert body.count("**") % 2 == 0   # bold markerlar dengeli


def test_forum_label():
    assert bs.forum_label("filmler-4-5-ve-ustu") == "Filmler · 4.5 ve Üstü"
    assert bs.forum_label("yonetmenler") == "Yönetmenler"


def test_film_messages_limits(film):
    msgs = bs.film_messages(film, "Filmler · 4.5 ve Üstü")
    assert msgs and all(len(m) <= 2000 for m in msgs)
    assert msgs[0].startswith("-#") or "Örnek Film" in msgs[0]
    joined = "\n".join(msgs)
    assert "Örnek Film (2020)" in joined and "nMDB **77**" in joined


def test_film_messages_bad_guven_no_crash(film):
    film["uygunluk_guveni"] = "yüksek"   # sayısız güven — M9 crash regresyonu
    msgs = bs.film_messages(film, "x")
    assert msgs and "güven" not in "\n".join(msgs)
