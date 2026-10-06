"""Tests for the visual fact pack data layer. Run: python3 tests/test_viz_data.py"""
import json, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from viz import data  # noqa: E402


def fb():
    facts = [
        {"fid": "K1", "fact": "FY2026 revenue was $2,919 million, up 12%.", "quote": "Total revenue 2,919", "tag": "F1", "confidence": "High"},
        {"fid": "K2", "fact": "Acme bought Beta for $6.5 billion on 3 May 2021.", "quote": "", "tag": "F7", "confidence": "Medium"},
    ]
    reg = [{"tag": "F1", "url": "https://sec.gov/a.htm"}, {"tag": "F7", "url": "https://acme.example/x/"}]
    d = tempfile.mkdtemp()
    json.dump(facts, open(f"{d}/fb.json", "w")); json.dump(reg, open(f"{d}/reg.json", "w"))
    return data.FactBase(f"{d}/fb.json", f"{d}/reg.json")


def test_numbers_in():
    assert {"2919", "12"} <= data.numbers_in("revenue of $2,919 million, up 12%")
    assert {"1.5", "1500"} <= data.numbers_in("$1.5 billion")
    assert "2919" in data.numbers_in("2,919.0")


def test_validate_keeps_traceable_rows():
    good, probs = data.validate([{"fid": "K1", "rev": 2919}, {"fid": "K2", "price": 6500}], fb(), ["rev", "price"], name="t")
    assert len(good) == 2 and not probs
    assert good[0]["tag"] == ["F1"] and good[0]["conf"] == "High"


def test_validate_rejects_unknown_fid_and_untraced_number():
    good, probs = data.validate([{"fid": "K9", "v": 1}, {"fid": "K1", "v": 3000}], fb(), ["v"], name="t")
    assert not good and len(probs) == 2
    assert "unknown fid K9" in probs[0] and "v=3000" in probs[1]


def test_validate_calc_and_lowest_conf():
    good, probs = data.validate([{"fid": "K1;K2", "v": 123, "calc": "calculated from filings"}], fb(), ["v"])
    assert not probs and good[0]["conf"] == "Medium" and good[0]["tag"] == ["F1", "F7"]


def test_url_tag():
    assert fb().url_tag("https://acme.example/x") == "F7"


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
