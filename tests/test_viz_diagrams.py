"""Tests for the diagram charts (Sankey, org chart, logo wall). Run: python3 tests/test_viz_diagrams.py"""
import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "tests" / "out"
OUT.mkdir(exist_ok=True)
LOGOS = OUT / "logos"

from viz import diagrams  # noqa: E402

REV_NODES = [
    {"id": "sub", "label": "Subscription", "col": 0}, {"id": "ps", "label": "Professional services", "col": 0},
    {"id": "rev", "label": "Revenue", "col": 1},
    {"id": "cor", "label": "Cost of revenue", "col": 2}, {"id": "gp", "label": "Gross profit", "col": 2},
    {"id": "rd", "label": "R&D", "col": 3}, {"id": "sm", "label": "S&M", "col": 3},
    {"id": "ga", "label": "G&A", "col": 3}, {"id": "oi", "label": "Operating income", "col": 3},
]


def fl(src, dst, v, kind, tag="F1"):
    return {"src": src, "dst": dst, "value": v, "kind": kind, "tag": tag, "conf": "High"}


REV_FLOWS = [fl("sub", "rev", 2855, "in"), fl("ps", "rev", 64, "in"), fl("rev", "cor", 663, "cost"),
             fl("rev", "gp", 2256, "profit"), fl("gp", "rd", 616, "cost"), fl("gp", "sm", 1061, "cost"),
             fl("gp", "ga", 430, "cost"), fl("gp", "oi", 149, "profit")]

CASH_NODES = [{"id": "ocf", "label": "Operating cash flow", "col": 0}, {"id": "opt", "label": "Option proceeds", "col": 0},
              {"id": "cash", "label": "Cash available", "col": 1}, {"id": "cap", "label": "Capex", "col": 2},
              {"id": "bb", "label": "Buybacks", "col": 2}, {"id": "cv", "label": "Convertible note repayment", "col": 2},
              {"id": "acq", "label": "Acquisitions", "col": 2}, {"id": "chg", "label": "Change in cash and investments", "col": 2}]
CASH_FLOWS = [fl("ocf", "cash", 770, "in"), fl("opt", "cash", 90, "in"), fl("cash", "cap", 60, "cost"),
              fl("cash", "bb", 420, "cost"), fl("cash", "cv", 180, "cost"), fl("cash", "acq", 70, "cost"),
              fl("cash", "chg", 40, "profit")]


def others(flows):
    return [f for f in flows if f["kind"] == "other"]


def test_sankey_adds_other_for_shortfall():
    nodes = [{"id": "s", "label": "S", "col": 0}, {"id": "a", "label": "A", "col": 1},
             {"id": "b", "label": "B", "col": 2}, {"id": "c", "label": "C", "col": 2}]
    n, f = diagrams.sankey_layout(nodes, [fl("s", "a", 100, "in"), fl("a", "b", 60, "cost"), fl("a", "c", 30, "cost")])
    o = others(f)
    assert len(o) == 1 and abs(o[0]["value"] - 10) < 1e-9 and o[0]["src"] == "a"
    assert any(x["id"] == o[0]["dst"] for x in n)


def test_sankey_balanced_adds_none():
    n, f = diagrams.sankey_layout(REV_NODES, REV_FLOWS)
    assert others(f) == [] and len(f) == len(REV_FLOWS)


def test_sankey_tolerance_half_percent():
    nodes = [{"id": "s", "label": "S", "col": 0}, {"id": "a", "label": "A", "col": 1}, {"id": "b", "label": "B", "col": 2}]
    _, f = diagrams.sankey_layout(nodes, [fl("s", "a", 1000, "in"), fl("a", "b", 996, "cost")])
    assert others(f) == []
    _, f = diagrams.sankey_layout(nodes, [fl("s", "a", 1000, "in"), fl("a", "b", 990, "cost")])
    assert len(others(f)) == 1


def test_sankey_layout_geometry():
    n, f = diagrams.sankey_layout(CASH_NODES, CASH_FLOWS, height=8.0, gap=0.5)
    assert others(f), "cash sample is deliberately unbalanced"
    by = {x["id"]: x for x in n}
    for col in {x["col"] for x in n}:
        c = sorted((x for x in n if x["col"] == col), key=lambda x: x["y"])
        for a, b in zip(c, c[1:]):
            assert b["y"] - (a["y"] + a["h"]) >= 0.5 - 1e-9, "nodes overlap or gap too small"
        assert c[0]["y"] >= -1e-9 and c[-1]["y"] + c[-1]["h"] <= 8.0 + 1e-9
    for x in n:
        out = sum(g["h"] for g in f if g["src"] == x["id"])
        assert out <= x["h"] + 1e-9
    # one scale for every flow
    k = f[0]["h"] / f[0]["value"]
    assert all(abs(g["h"] - g["value"] * k) < 1e-9 for g in f)
    assert by["cash"]["h"] >= 860 * k - 1e-9


def test_sankey_no_crossings_at_node():
    n, f = diagrams.sankey_layout(REV_NODES, REV_FLOWS)
    by = {x["id"]: x for x in n}
    for nid in by:
        outs = sorted((g for g in f if g["src"] == nid), key=lambda g: g["y0"])
        ys = [by[g["dst"]]["y"] for g in outs]
        assert ys == sorted(ys), f"outflows of {nid} cross"
        ins = sorted((g for g in f if g["dst"] == nid), key=lambda g: g["y1"])
        ys = [by[g["src"]]["y"] for g in ins]
        assert ys == sorted(ys), f"inflows of {nid} cross"


def test_sankey_renders():
    c = diagrams.sankey(REV_NODES, REV_FLOWS, out=OUT / "diagrams_sankey_revenue.png", w_cm=25, h_cm=9)
    assert os.path.exists(c.png) and c.sources == ["F1"] and c.confidence == "High"
    c = diagrams.sankey(CASH_NODES, CASH_FLOWS, out=OUT / "diagrams_sankey_cash.png", w_cm=12, h_cm=7)
    assert os.path.exists(c.png)


def test_sankey_empty():
    try:
        diagrams.sankey([], [], out=OUT / "x.png", w_cm=10, h_cm=5)
        raise AssertionError("no EmptyData")
    except diagrams.EmptyData:
        pass


def P_(i, name, title, group, rt=None, start="2020", **kw):
    d = {"id": i, "name": name, "title": title, "start": start, "group": group, "reports_to": rt, "tag": "F3", "conf": "Medium"}
    d.update(kw)
    return d


PEOPLE = [P_("ceo", "Alex Morgan", "Chief Executive Officer and Co-Founder", "ceo", None, "2009")]
PEOPLE += [P_(f"e{i}", n, t, "Executive officers (proxy)", "ceo", s) for i, (n, t, s) in enumerate([
    ("Sam Patel", "Chief Financial Officer", "2020"), ("Jo Rivera", "President, Field Operations", "2021"),
    ("Lee Brooks", "Chief Legal Officer and Corporate Secretary", "2022"), ("Kim Novak", "Chief Legal Officer", "2018"),
    ("Pat Quinn", "President, Worldwide Field Operations", "2020"), ("Chris Young", "Chief Technology Officer", "2013"),
    ("Dana Fox", "Chief Customer and Revenue Officer", "2019")])]
PEOPLE += [P_(f"o{i}", n, t, "Other named leaders", None, s) for i, (n, t, s) in enumerate([
    ("Harold Lopez", "Chief Information Security Officer", "2021"), ("Anna Khan", "Chief Product Officer", "2022"),
    ("Joe Wan", "SVP Engineering", "2016"), ("Mei Chen", "Chief People Officer", "2023"),
    ("Peter Cole", "VP Investor Relations", "2017"), ("Nia Stone", "Chief Marketing Officer", "2024")])]


def test_org_layout_edges_only_with_reports_to():
    r = diagrams.org_layout(PEOPLE)
    assert len(r["boxes"]) == 14
    assert len(r["edges"]) == 7 and all(e["from"] == "ceo" for e in r["edges"])
    assert not any(e["to"].startswith("o") for e in r["edges"])
    ids = [b["id"] for b in r["boxes"]]
    assert len(set(ids)) == 14
    by = {b["id"]: b for b in r["boxes"]}
    assert by["ceo"]["row"] == 0
    per_row = {}
    for b in r["boxes"]:
        per_row.setdefault(b["row"], []).append(b)
    assert all(len(v) <= 6 for v in per_row.values())
    for v in per_row.values():
        cols = sorted(b["col"] for b in v)
        assert all(b - a >= 1 - 1e-9 for a, b in zip(cols, cols[1:])), "boxes overlap"
    assert [g["text"] for g in r["labels"]] == ["Executive officers (proxy)", "Other named leaders"]


def test_org_renders_and_wraps():
    c = diagrams.org_chart(PEOPLE, out=OUT / "diagrams_org.png", w_cm=25, h_cm=9)
    assert os.path.exists(c.png) and c.sources == ["F3"] and c.confidence == "Medium"
    c = diagrams.org_chart(PEOPLE, out=OUT / "diagrams_org_small.png", w_cm=12, h_cm=7)
    assert os.path.exists(c.png)


def test_org_text_fit():
    lines = diagrams.fit_lines("Chief Legal Officer and Corporate Secretary and Head of Everything", 3.0, 7, max_lines=2)
    assert len(lines) <= 2 and lines[-1].endswith("…")


def make_logos():
    from PIL import Image, ImageDraw
    LOGOS.mkdir(exist_ok=True)
    cols = [(200, 30, 30), (30, 90, 200), (20, 140, 70), (230, 150, 20), (110, 40, 160)]
    paths = []
    for i, (name, size) in enumerate([("Acme", (300, 100)), ("Globex", (200, 200)), ("Initech", (400, 80)),
                                      ("Umbrella", (240, 120)), ("Hooli", (160, 160))]):
        im = Image.new("RGBA" if i % 2 else "RGB", size, cols[i] + ((255,) if i % 2 else ()))
        ImageDraw.Draw(im).text((10, size[1] // 2 - 5), name.upper(), fill=(255, 255, 255, 255) if i % 2 else (255, 255, 255))
        p = LOGOS / f"{name.lower()}.png"
        im.save(p)
        paths.append(str(p))
    bad = LOGOS / "corrupt.png"
    bad.write_bytes(b"not an image")
    return paths, str(bad)


def logo_rows():
    paths, bad = make_logos()
    names = ["Acme", "Globex", "Initech", "Umbrella", "Hooli"]
    rows = [{"name": n, "sector": "Technology", "path": p, "tag": "F9", "conf": "High"} for n, p in zip(names, paths)]
    rows += [{"name": "Missing Bank", "sector": "Financial services", "path": str(LOGOS / "nope.png"), "tag": "F9", "conf": "High"},
             {"name": "Corrupt Retail", "sector": "Retail", "path": bad, "tag": "F10", "conf": "Medium"},
             {"name": "No Path Gov", "sector": "Government", "path": None, "tag": "F11", "conf": "High"},
             {"name": "Acme Two", "sector": "Financial services", "path": paths[0], "tag": "F9", "conf": "High"}]
    return rows


def test_logo_layout_text_fallback():
    cells = diagrams.logo_layout(logo_rows(), ncols=4)["cells"]
    kind = {c["name"]: c["kind"] for c in cells}
    assert kind["Missing Bank"] == "text" and kind["Corrupt Retail"] == "text" and kind["No Path Gov"] == "text"
    assert kind["Acme"] == "image" and len(cells) == 9
    assert next(c for c in cells if c["name"] == "Acme")["img"].mode == "L"
    secs = []
    for c in cells:
        if c["sector"] not in secs:
            secs.append(c["sector"])
    assert secs == ["Technology", "Financial services", "Retail", "Government"]
    assert max(c["col"] for c in cells) < 4


def test_logo_wall_renders():
    c = diagrams.logo_wall(logo_rows(), ncols=4, out=OUT / "diagrams_logos.png", w_cm=25, h_cm=9)
    assert os.path.exists(c.png) and c.sources == ["F9", "F10", "F11"] and c.confidence == "Medium"
    from PIL import Image
    im = Image.open(c.png).convert("RGB")
    px = list(im.resize((60, 30)).getdata())
    assert all(abs(r - g) < 40 and abs(g - b) < 40 for r, g, b in px), "logo wall must be greyscale"


def test_charts_registry():
    assert diagrams.CHARTS == ["sankey", "org_chart", "logo_wall"]


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
