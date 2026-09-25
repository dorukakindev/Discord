"""lib/dapi — DRY_RUN kısa devresi ve channel_messages sayfalama."""
from lib import dapi


def test_dry_run_short_circuits_writes(monkeypatch, capsys):
    dapi.set_dry_run(True)
    try:
        assert dapi.post("/channels/1/messages", json={}) == {"id": "dry-run"}
        assert dapi.patch("/channels/1", json={}) is None
        assert dapi.delete("/channels/1") is None
        out = capsys.readouterr().out
        assert "[dry-run] POST" in out and "[dry-run] DELETE" in out
    finally:
        dapi.set_dry_run(False)


def test_dry_run_allows_get(monkeypatch):
    monkeypatch.setattr(dapi, "req", lambda m, p, **kw: {"ok": True})
    dapi.set_dry_run(True)
    try:
        assert dapi.get("/guilds/1") == {"ok": True}
    finally:
        dapi.set_dry_run(False)


def test_channel_messages_pagination(monkeypatch):
    # 250 mesajlı kanal: 100 + 100 + 50 sayfalama
    pages = iter([
        [{"id": str(i)} for i in range(300, 200, -1)],
        [{"id": str(i)} for i in range(200, 100, -1)],
        [{"id": str(i)} for i in range(100, 50, -1)],
    ])
    monkeypatch.setattr(dapi, "get", lambda path, **kw: next(pages, []))
    out = dapi.channel_messages("1")
    assert len(out) == 250 and out[0]["id"] == "300"


def test_channel_messages_limit_stops(monkeypatch):
    calls = []
    def fake_get(path, **kw):
        calls.append(kw.get("params", {}).get("limit"))
        return [{"id": str(i)} for i in range(100)]
    monkeypatch.setattr(dapi, "get", fake_get)
    out = dapi.channel_messages("1", limit=150)
    # 100 + 50 istenir; ikinci sayfa 100 döndürse de döngü limitte durur
    assert len(out) == 200 and calls == [100, 50]


def test_forum_threads_dedup_and_paging(monkeypatch):
    seq = iter([
        {"threads": [{"id": str(i), "thread_metadata": {"archive_timestamp": "t"}}
                     for i in range(100)]},
        {"threads": [{"id": str(i), "thread_metadata": {"archive_timestamp": "t"}}
                     for i in range(100, 150)]},
    ])
    def fake_get(path, **kw):
        if "threads/active" in path:
            return {"threads": [{"id": "aktif-1", "parent_id": "F"},
                                {"id": "baska", "parent_id": "OTHER"},
                                {"id": "5", "parent_id": "F"}]}
        return next(seq, None)
    monkeypatch.setattr(dapi, "get", fake_get)
    out = dapi.forum_threads("F")
    ids = [t["id"] for t in out]
    # aktif-1 + 5 (dedup: 5 arşivde de var) + 150 arşiv; 'baska' elenir
    assert "aktif-1" in ids and "baska" not in ids and len(out) == 151
