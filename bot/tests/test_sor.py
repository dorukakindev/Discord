import lexicanum as lx


def test_question_terms_strips_stopwords():
    assert lx.question_terms("astartes nedir") == {"astartes"}
    assert lx.question_terms("Nurgle'in dünyası nasıl bir yer?") == {"dunyasi", "nurgle", "yer"}


def test_question_terms_all_stopwords_falls_back_empty():
    assert lx.question_terms("nedir ne") == set()


def test_thread_id_of_prefers_i_field():
    assert lx.thread_id_of({"i": "123", "l": "https://x/999"}) == "123"
    assert lx.thread_id_of({"l": "https://discord.com/channels/1/2/456"}) == "456"


def test_best_excerpt_picks_term_densest_paragraph():
    text = (
        "# Başlık\n\n"
        "Bu kısa bir giriş paragrafı.\n\n"
        "Astartes, Imperium'un genetik olarak geliştirilmiş süper askerleridir. "
        "Uzay denizcileri olarak da bilinirler ve her biri devasa zırhlar giyer.\n\n"
        "Bu paragraf konuyla ilgisizdir ve hiçbir şey içermez."
    )
    out = lx.best_excerpt(text, {"astartes"})
    assert "Astartes" in out and "süper asker" in out


def test_best_excerpt_empty_terms_returns_first_body_paragraph():
    text = "# header\n\nİlk gövde paragrafı burada.\n\nİkinci paragraf."
    assert lx.best_excerpt(text, set()) == "İlk gövde paragrafı burada."


def test_best_excerpt_skips_headers_and_ribbons():
    text = "-# şerit\n\n## Kayıt\n\nAsıl içerik burada."
    assert lx.best_excerpt(text, {"icerik"}) == "Asıl içerik burada."


def test_best_excerpt_respects_limit():
    text = "x " * 2000
    out = lx.best_excerpt(text, {"x"}, limit=500)
    assert len(out) <= 501 and out.endswith("…")


def test_best_excerpt_empty_text():
    assert lx.best_excerpt("", {"a"}) == ""
    assert lx.best_excerpt("# sadece başlık", {"a"}) == ""


def test_sor_query_via_terms(monkeypatch):
    """'astartes nedir' sorusu 'Adeptus Astartes' başlığını bulmalı."""
    recs = [
        {"t": "Adeptus Astartes", "n": lx.norm("Adeptus Astartes"), "g": "1",
         "l": "x", "f": "F", "s": "W", "i": "1"},
        {"t": "Nedir Kanunu", "n": lx.norm("Nedir Kanunu"), "g": "1",
         "l": "y", "f": "F", "s": "W", "i": "2"},
    ]
    monkeypatch.setattr(lx, "INDEX", recs)
    terms = lx.question_terms("astartes nedir")
    rows, _ = lx.search(" ".join(sorted(terms)), gid="1")
    assert rows and rows[0]["t"] == "Adeptus Astartes"
