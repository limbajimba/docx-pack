"""Tests for the visual fact pack chart library. Run: python3 tests/test_viz.py"""
import json, os, sys, tempfile, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "tests" / "out"
OUT.mkdir(exist_ok=True)

from viz import style  # noqa: E402


def png_ratio(path):
    from PIL import Image
    w, h = Image.open(path).size
    return h / w


def test_provenance_lowest_and_sorted():
    assert style.provenance([{"tag": "F2", "conf": "High"}, {"tag": ["F1", "F2"], "conf": "Low"}]) == (["F1", "F2"], "Low")
    assert style.provenance([]) == ([], "")
    assert style.provenance([{"tag": t} for t in ["table: fin_annual", "F10", "F2"]])[0] == ["F2", "F10", "table: fin_annual"]


def test_formats():
    assert style.money(2919) == "$2,919m"
    assert style.money(-149) == "-$149m"
    assert style.money_bn(2919) == "$2.9bn"
    assert style.pct(12.34) == "12%" and style.pct1(12.34) == "12.3%"
    assert style.num(5100) == "5,100"
    assert style.fmt_of("pct") is style.pct


def test_finish_and_require():
    fig, ax = style.figure(8, 4)
    ax.plot([1, 2], [1, 2])
    c = style.finish(fig, OUT / "core.png", [{"tag": "F1", "conf": "Medium"}], 8, 4)
    assert os.path.exists(c.png) and c.sources == ["F1"] and c.confidence == "Medium" and c.w_cm == 8
    try:
        style.require([])
        raise AssertionError("no EmptyData")
    except style.EmptyData:
        pass


if __name__ == "__main__":  # plain runner when pytest is not installed
    import traceback
    only = sys.argv[1:]
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn) and (not only or any(o in name for o in only)):
            try:
                fn(); print(f"ok   {name}")
            except Exception:
                fails += 1; print(f"FAIL {name}"); traceback.print_exc()
    sys.exit(1 if fails else 0)
