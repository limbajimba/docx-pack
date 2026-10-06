"""Tests for viz.series. Run: python3 tests/test_viz_series.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "tests" / "out"
OUT.mkdir(exist_ok=True)

from viz import series, style  # noqa: E402

YEARS = [f"FY{y}" for y in range(2019, 2027)]
REV = [399, 586, 835, 1300, 1858, 2263, 2610, 2919]
GROW = [None, 47, 43, 56, 43, 22, 15, 12]
ROWS = [{"x": y, "rev": r, "g": g, "tag": f"F{i + 1}", "conf": "High" if i else "Medium"}
        for i, (y, r, g) in enumerate(zip(YEARS, REV, GROW))]


def ratio(path):
    from PIL import Image
    w, h = Image.open(path).size
    return h / w


def check(c, w, h, tags):
    assert abs(ratio(c.png) - h / w) < 0.02 * h / w, ratio(c.png)
    assert c.sources == tags, c.sources


def empty(fn, *a, **k):
    try:
        fn(*a, out=OUT / "x.png", **k)
        raise AssertionError("no EmptyData")
    except style.EmptyData:
        pass


def test_charts_list():
    assert series.CHARTS == ["bar_line", "multi_line", "range_vs_actual", "stacked_share", "small_multiples", "kpi_tiles"]


def test_bar_line():
    c = series.bar_line(ROWS, "x", "rev", line="g", out=OUT / "t_bl.png", bar_name="Revenue", line_name="Growth")
    check(c, 12.4, 5.6, [f"F{i}" for i in range(1, 9)])
    c = series.bar_line(ROWS, "x", "rev", out=OUT / "t_bl2.png", w_cm=8, h_cm=4)
    check(c, 8, 4, [f"F{i}" for i in range(1, 9)])
    empty(series.bar_line, [], "x", "rev")


def test_multi_line():
    rows = [{"x": f"Q{i}", "a": i * 2, "b": None if i == 3 else i, "tag": "F1"} for i in range(1, 7)]
    c = series.multi_line(rows, "x", ["a", "b"], names={"a": "Alpha"}, out=OUT / "t_ml.png")
    check(c, 12.4, 5.6, ["F1"])
    empty(series.multi_line, [], "x", ["a"])


def test_range_vs_actual():
    rows = [{"x": f"Q{i} FY27", "lo": 100 + i, "hi": 105 + i, "actual": 108 + i, "tag": "F9"} for i in range(10)]
    check(series.range_vs_actual(rows, "x", "lo", "hi", "actual", out=OUT / "t_rv.png"), 12.4, 5.6, ["F9"])
    empty(series.range_vs_actual, [], "x", "lo", "hi", "actual")


def test_stacked_share():
    rows = [{"x": y, "w": 59 - i, "c": 41 + i, "tag": "F3"} for i, y in enumerate(["FY24", "FY25", "FY26"])]
    check(series.stacked_share(rows, "x", ["w", "c"], names={"w": "Workforce"}, out=OUT / "t_ss.png"), 12.4, 5.6, ["F3"])
    empty(series.stacked_share, [], "x", ["w"])


def test_small_multiples():
    rows = [{"x": y, "v": v, "tag": "F4"} for y, v in zip(YEARS, REV)]
    panels = [{"title": "Revenue", "rows": rows, "x": "x", "y": "v", "kind": "line", "fmt": "money"},
              {"title": "Revenue bars", "rows": rows, "x": "x", "y": "v", "kind": "bar", "fmt": "money"},
              {"title": "Empty", "rows": [], "x": "x", "y": "v", "kind": "line", "fmt": "money"}]
    check(series.small_multiples(panels, ncols=2, out=OUT / "t_sm.png"), 12.4, 5.6, ["F4"])
    empty(series.small_multiples, [{"title": "e", "rows": [], "x": "x", "y": "v", "kind": "bar", "fmt": "num"}])


def test_kpi_tiles():
    tiles = [{"label": "ARR", "value": "$3.0bn", "note": "FY26", "spark": [1, 2, 3, 5], "rows": [{"tag": "F7", "conf": "Low"}]},
             {"label": "Staff", "value": "5,100", "note": "", "spark": None, "rows": [{"tag": "F8"}]}]
    c = series.kpi_tiles(tiles, ncols=2, out=OUT / "t_kt.png")
    check(c, 12.4, 5.6, ["F7", "F8"])
    assert c.confidence == "Low"
    empty(series.kpi_tiles, [])


if __name__ == "__main__":
    import traceback
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print(f"ok   {name}")
            except Exception:
                fails += 1; print(f"FAIL {name}"); traceback.print_exc()
    sys.exit(1 if fails else 0)
