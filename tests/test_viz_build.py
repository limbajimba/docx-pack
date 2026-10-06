"""Tests for the visual pack assembler. Run: python3 tests/test_viz_build.py"""
import json, sys, tempfile, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_visual_pack as bvp  # noqa: E402
from viz import style  # noqa: E402

SPEC = ROOT / "house" / "silvertree-landscape.style-spec.json"


def fake_line(rows, *, out, w_cm, h_cm, **kw):
    style.require(rows)
    fig, ax = style.figure(w_cm, h_cm)
    ax.plot([r["x"] for r in rows], [r["y"] for r in rows])
    return style.finish(fig, out, rows, w_cm, h_cm)


def setup_plan(headline="Revenue was $2,919m in FY2026.", fids=("K1",), title="Revenue"):
    d = Path(tempfile.mkdtemp())
    json.dump([{"fid": "K1", "fact": "FY2026 revenue was $2,919 million.", "quote": "2,919", "tag": "F1", "confidence": "High"}], open(d / "fb.json", "w"))
    json.dump([{"tag": "F1", "url": "https://sec.gov/a"}], open(d / "reg.json", "w"))
    (d / "vd.py").write_text("def datasets(fb):\n    return {'good': [{'x': 1, 'y': 2, 'tag': 'F1', 'conf': 'High'}, {'x': 2, 'y': 3, 'tag': 'F1', 'conf': 'High'}], 'empty': []}\n")
    plan = {"meta": {"title": "T", "kicker": "K", "date": "1 Jan 2026"}, "factbase": "fb.json", "register": "reg.json", "data_module": "vd.py",
            "pages": [{"h1": "Financial position", "headline": headline, "headline_fids": list(fids), "missing": "Nothing.",
                       "panels": [{"id": "a", "chart": "line", "data": "good", "title": title}, {"id": "b", "chart": "line", "data": "empty", "title": "E"}]}]}
    (d / "plan.json").write_text(json.dumps(plan))
    return d


def run(d):
    orig = bvp.registry
    bvp.registry = lambda: {"line": fake_line}
    try:
        return bvp.build(d / "plan.json", d / "out.docx", SPEC)
    finally:
        bvp.registry = orig


def test_builds_and_drops_empty_panel():
    d = setup_plan()
    res = run(d)
    assert res["charts"] == 1 and len(res["dropped"]) == 1
    xml = zipfile.ZipFile(d / "out.docx").read("word/document.xml").decode()
    assert xml.count("<w:drawing>") == 1 and "Sources: F1" in xml and "lowest confidence: High" in xml


def _fails(d):
    try:
        run(d)
    except SystemExit:
        return True
    return False


def test_banned_word_fails():
    assert _fails(setup_plan(title="An attractive revenue line"))


def test_untraced_headline_number_fails():
    assert _fails(setup_plan(headline="Revenue was $3,100m in FY2026."))


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
