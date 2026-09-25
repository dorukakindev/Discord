import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "wh40k"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "filmarchive"))

import importlib.util  # noqa: E402


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_HERE = os.path.dirname(os.path.abspath(__file__))
wh = load("wh_dump", os.path.join(_HERE, "..", "wh40k", "dump_all.py"))
fa = load("fa_dump", os.path.join(_HERE, "..", "filmarchive", "dump_all.py"))


def test_unique_fname_first_wins():
    seen = set()
    assert wh.unique_fname(seen, "A B", "111") == "A B.md"
    assert wh.unique_fname(seen, "A!B", "222") != "A B.md"  # çakışma → id son eki


def test_unique_fname_uses_tid_suffix():
    seen = {"Stalker.md"}
    out = wh.unique_fname(seen, "Stalker", "1552514539344363610")
    assert out == "Stalker-3610.md"


def test_unique_fname_full_fallback():
    tid = "1552514539344363610"
    seen = {"X.md", f"X-{tid[-4:]}.md"}
    out = fa.unique_fname(seen, "X", tid)
    assert out == f"X-{tid}.md"


def test_unique_fname_distinct_threads_get_distinct_files():
    seen = set()
    f1 = fa.unique_fname(seen, "Film: A", "1")
    f2 = fa.unique_fname(seen, "Film A", "2")
    assert f1 != f2


def test_fsafe_and_dsan_parity_between_copies():
    for mod in (wh, fa):
        assert mod.unique_fname(set(), "T", "1") == "T.md"
