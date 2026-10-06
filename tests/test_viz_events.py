"""Tests for scripts/viz/events.py. Run: /opt/homebrew/bin/python3 tests/test_viz_events.py"""
import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "tests" / "out"
OUT.mkdir(exist_ok=True)

from viz import events, style  # noqa: E402


def png_ratio(path):
    from PIL import Image
    w, h = Image.open(path).size
    return h / w


def crowded():
    names = ["Alder", "Birch", "Cedar", "Scale", "Storm", "Delta", "Elm", "Zeta", "Nimbus", "Orbit", "Quill", "Raven", "Sable"]
    ev = []
    for i in range(25):
        d = f"2026-{4 + (i * 3) // 25:02d}-{1 + (i * 2) % 27:02d}"
        ev.append({"date": d, "lane": "Acquisitions", "label": f"{names[i % 13]} Security Holdings {i}",
                   "size": None if i % 3 == 0 else 50.0 + 40 * i, "hollow": i % 4 == 0, "tag": f"F{i + 1}", "conf": "Medium"})
    return ev


def company():
    rows = [("2015-06-01", "Early seed", None), ("2017-03-07", "Alder Labs", 0.0), ("2018-05-01", "Birch IO", None),
            ("2019-07-10", "Cedar", None), ("2021-03-01", "Delta", None), ("2021-05-03", "Beta", 6500.0),
            ("2024-03-12", "Elm Security", None), ("2025-09-01", "Fir Security", None)]
    ev = [{"date": d, "lane": "Acquisitions", "label": n, "size": s or None, "hollow": s is None, "tag": "F1", "conf": "High"} for d, n, s in rows]
    ev += [{"date": "2017-04-01", "lane": "Funding", "label": "Series F", "size": 75.0, "tag": "F2", "conf": "High"},
           {"date": "2017-04-07", "lane": "Funding", "label": "IPO", "size": 187.0, "tag": "F2", "conf": "High"},
           {"date": "2023-02-01", "lane": "People", "label": "CFO change", "tag": "F3", "conf": "Medium"},
           {"date": "2026-01-15", "lane": "People", "label": "New CRO named at group level", "tag": "F4", "conf": "Low"}]
    return ev


def assert_no_overlap(info):
    boxes = [t.get_window_extent(info["renderer"]) for t in info["texts"]]
    assert boxes
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            assert not boxes[i].overlaps(boxes[j]), (info["texts"][i].get_text(), info["texts"][j].get_text())
    fb = info["fig"].bbox
    for t, b in zip(info["texts"], boxes):
        assert b.x0 >= fb.x0 - 1 and b.x1 <= fb.x1 + 1 and b.y0 >= fb.y0 - 1 and b.y1 <= fb.y1 + 1, t.get_text()
        assert t.get_fontsize() >= 6.5


def test_timeline_crowded_quarter_no_overlap():
    info = events.build_timeline(crowded(), w_cm=25, h_cm=6)
    assert len(info["texts"]) == 25
    assert_no_overlap(info)
    import matplotlib.pyplot as plt
    plt.close(info["fig"])


def test_timeline_company_spread_no_overlap_and_render():
    info = events.build_timeline(company(), lanes=["Acquisitions", "Funding", "People"], w_cm=25, h_cm=6)
    assert_no_overlap(info)
    import matplotlib.pyplot as plt
    plt.close(info["fig"])
    c = events.timeline_lanes(company(), lanes=["Acquisitions", "Funding", "People"], out=OUT / "events_timeline.png", w_cm=25, h_cm=6)
    assert os.path.exists(c.png) and c.sources == ["F1", "F2", "F3", "F4"] and c.confidence == "Low"
    assert abs(png_ratio(c.png) - c.h_cm / c.w_cm) < 0.02


def test_timeline_crowded_render():
    c = events.timeline_lanes(crowded(), out=OUT / "events_timeline_crowded.png", w_cm=25, h_cm=6)
    assert os.path.exists(c.png)


def test_timeline_truncates_label():
    ev = [{"date": "2020-01-01", "lane": "A", "label": "x" * 80, "tag": "F1"}]
    info = events.build_timeline(ev, label_max=34, w_cm=12, h_cm=4)
    assert len(info["texts"][0].get_text()) <= 34
    import matplotlib.pyplot as plt
    plt.close(info["fig"])


def test_dot_rank_descending_and_render():
    rows = [{"name": f"Co{i}", "v": float((i * 37) % 11 + 1) * 100, "tag": "F1", "conf": "High"} for i in range(12)]
    rows.append({"name": "Acme", "v": 2919.0, "tag": ["F2"], "conf": "Medium"})
    fig, ax, order = events.build_dot_rank(rows, "name", "v", fmt="money", highlight="Acme", w_cm=12, h_cm=5.6)
    vals = [r["v"] for r in order]
    assert vals == sorted(vals, reverse=True)
    import matplotlib.pyplot as plt
    plt.close(fig)
    c = events.dot_rank(rows, "name", "v", fmt="money", highlight="Acme", out=OUT / "events_dot_rank.png", w_cm=12, h_cm=5.6)
    assert os.path.exists(c.png) and "F2" in c.sources and abs(png_ratio(c.png) - 5.6 / 12) < 0.02


def test_dot_rank_log_and_note():
    rows = [{"n": "A", "v": 10.0, "note": "company est."}, {"n": "B", "v": 10000.0, "note": "filing"}, {"n": "C", "v": 300.0}]
    c = events.dot_rank(rows, "n", "v", log=True, note_field="note", out=OUT / "events_dot_rank_log.png", w_cm=12, h_cm=4)
    assert os.path.exists(c.png)


def grid_rows():
    areas = ["Business model", "Customers", "Financials", "Products", "Competition", "Management", "Ownership", "Legal",
             "Technology", "Market", "Risks"]
    return [{"area": a, "High": (i * 3) % 7, "Medium": (i * 5) % 6, "Low": i % 3, "Not found": (i + 1) % 4,
             "covered": 4 + i % 3, "partly": i % 4, "not public": i % 2, "tag": f"F{i + 1}", "conf": "Medium"}
            for i, a in enumerate(areas)]


def test_confidence_grid_11_rows():
    fig, ax, info = events.build_confidence_grid(grid_rows(), w_cm=12, h_cm=5.6)
    assert len(info["areas"]) == 11 and info["ncols"] == 7
    assert len(info["cells"]) == 11 * 7
    import matplotlib.pyplot as plt
    plt.close(fig)
    c = events.confidence_grid(grid_rows(), out=OUT / "events_confidence_grid.png", w_cm=12, h_cm=5.6)
    assert os.path.exists(c.png) and abs(png_ratio(c.png) - 5.6 / 12) < 0.02


def test_confidence_grid_without_coverage():
    rows = [{k: v for k, v in r.items() if k not in ("covered", "partly", "not public")} for r in grid_rows()]
    fig, ax, info = events.build_confidence_grid(rows, w_cm=12, h_cm=5.6)
    assert info["ncols"] == 4
    import matplotlib.pyplot as plt
    plt.close(fig)


def test_empty_raises():
    for fn, args in ((events.timeline_lanes, ([],)), (events.dot_rank, ([], "a", "b")), (events.confidence_grid, ([],))):
        try:
            fn(*args, out=OUT / "x.png", w_cm=10, h_cm=4)
            raise AssertionError("no EmptyData")
        except style.EmptyData:
            pass


def test_charts_list():
    assert events.CHARTS == ["timeline_lanes", "dot_rank", "confidence_grid"]


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
