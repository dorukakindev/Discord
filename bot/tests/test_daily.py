from datetime import datetime, timedelta, timezone

import lexicanum as lx

TR = timezone(timedelta(hours=3))


def mk(t, g):
    return {'t': t, 'g': g, 'i': '1', 'f': 'f', 'c': '', 'l': 'l', 's': 's', 'n': t}


def test_daily_pick_deterministic(monkeypatch):
    monkeypatch.setattr(lx, 'INDEX', [mk(f'k{i}', 'g1') for i in range(50)])
    a = lx.daily_pick('g1', '2026-09-25')
    b = lx.daily_pick('g1', '2026-09-25')
    c = lx.daily_pick('g1', '2026-09-26')
    assert a == b
    assert c is not None


def test_daily_pick_guild_scope_and_fallback(monkeypatch):
    monkeypatch.setattr(lx, 'INDEX', [mk('a', 'g1'), mk('b', 'g2')])
    assert lx.daily_pick('g2', '2026-09-25')['g'] == 'g2'
    # bilinmeyen gid → global pool'a düşer
    assert lx.daily_pick('yok', '2026-09-25') is not None


def test_daily_pick_empty(monkeypatch):
    monkeypatch.setattr(lx, 'INDEX', [])
    assert lx.daily_pick('g1') is None


def test_daily_due():
    now = datetime(2026, 9, 25, 10, 5, tzinfo=TR)
    assert lx.daily_due({'hour': 10, 'last': '2026-09-24'}, now)
    assert not lx.daily_due({'hour': 10, 'last': '2026-09-25'}, now)  # bugün oldu
    assert not lx.daily_due({'hour': 11, 'last': '2026-09-24'}, now)  # saat değil
    assert not lx.daily_due({'last': '2026-09-24'}, now)  # hour yok
