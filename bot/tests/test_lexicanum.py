"""lexicanum.py'nin saf yardımcıları — Discord'a değmeden test edilir."""
import lexicanum as lx


def mkrecs():
    return [
        {"t": "Star Wars Bölüm IV", "g": "1", "f": "Filmler", "c": "FİLMLER",
         "l": "https://discord.com/channels/1/100", "s": "THE FILM ARCHIVE",
         "i": "100", "n": lx.norm("Star Wars Bölüm IV")},
        {"t": "Çöl Güneşi", "g": "1", "f": "Filmler", "c": "FİLMLER",
         "l": "https://discord.com/channels/1/101", "s": "THE FILM ARCHIVE",
         "i": "101", "n": lx.norm("Çöl Güneşi")},
        {"t": "Chaos Silahları", "g": "2", "f": "Silahlar", "c": "",
         "l": "https://discord.com/channels/2/200", "s": "THE IMPERIAL ARCHIVE",
         "i": "200", "n": lx.norm("Chaos Silahları")},
    ]


def test_search_returns_rows_and_total(monkeypatch):
    monkeypatch.setattr(lx, "INDEX", mkrecs())
    rows, total = lx.search("star wars")
    assert len(rows) == total == 1
    assert rows[0]["t"] == "Star Wars Bölüm IV"


def test_search_turkish_normalization(monkeypatch):
    monkeypatch.setattr(lx, "INDEX", mkrecs())
    rows, _ = lx.search("col gunesi")   # Türkçesiz yazım da bulur
    assert rows and rows[0]["t"] == "Çöl Güneşi"


def test_search_guild_filter(monkeypatch):
    monkeypatch.setattr(lx, "INDEX", mkrecs())
    rows, _ = lx.search("silah", gid="2")
    assert rows and all(r["g"] == "2" for r in rows)


def test_search_empty_query(monkeypatch):
    monkeypatch.setattr(lx, "INDEX", mkrecs())
    assert lx.search("") == ([], 0)


def test_suggest_near_miss(monkeypatch):
    monkeypatch.setattr(lx, "INDEX", mkrecs())
    hits = lx.suggest(lx.norm("star wrs"))
    assert hits and hits[0]["t"] == "Star Wars Bölüm IV"


def test_join_body_hard_split():
    parts = ["x" * 2000, "y" * 2000, "kuyruk"]
    assert lx.join_body(parts) == "x" * 2000 + "y" * 2000 + "kuyruk"


def test_join_body_paragraph_split():
    parts = ["a" * 1950, "b" * 800]
    assert lx.join_body(parts) == "a" * 1950 + "\n\n" + "b" * 800


def test_join_body_single():
    assert lx.join_body(["tek"]) == "tek"


def test_split_for_modal_short():
    assert lx.split_for_modal("kısa") == ("kısa", "")


def test_split_for_modal_paragraph_boundary():
    old = "a" * 3000 + "\n\n" + "b" * 2000
    shown, tail = lx.split_for_modal(old, 4000)
    assert shown == "a" * 3000
    assert tail == "\n\n" + "b" * 2000
    assert shown + tail == old


def test_split_for_modal_hard_cut():
    old = "x" * 5000
    shown, tail = lx.split_for_modal(old, 4000)
    assert len(shown) == 4000 and shown + tail == old


def test_rec_id_match_i_field():
    r = {"t": "x", "i": "999", "l": "https://discord.com/channels/1/888"}
    assert (r.get("i") or str(r.get("l", "")).rsplit("/", 1)[-1]) == "999"


def test_rec_id_match_legacy_url():
    r = {"t": "x", "l": "https://discord.com/channels/1/888"}
    assert (r.get("i") or str(r.get("l", "")).rsplit("/", 1)[-1]) == "888"
