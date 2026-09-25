from lib.textnorm import norm


def test_turkish_chars_normalized():
    assert norm("ŞÜĞÇÖI") == "sugcoi"
    assert norm("Çöl Güneşi") == "col gunesi"


def test_casefold_and_space_collapse():
    assert norm("  The   FILM  ") == "the film"


def test_non_alnum_stripped():
    assert norm("Star Wars: Bölüm-IV!") == "star wars bolum iv"


def test_none_and_empty():
    assert norm(None) == ""
    assert norm("") == ""


def test_diacritics():
    assert norm("Café Ñoño") == "cafe nono"
