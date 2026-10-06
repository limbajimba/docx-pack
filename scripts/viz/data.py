"""Data layer: look facts up by id, and keep only rows whose numbers appear in the facts they cite.

Every chart row carries provenance. Rows extracted from facts (events, people, logos) carry a fid
("K12" or "K12;K40"); validate() stamps their source tags and lowest confidence and drops any row
whose numbers cannot be found in the cited fact text or quote. Rows from a research table that names
its source get their provenance from table_rows().
"""
import csv
import json
import re

from .style import CONF_ORDER


def _norm_url(u):
    u = re.sub(r"#.*$", "", (u or "").strip())
    u = re.sub(r"[?&](utm_[^=&]+=[^&]*)", "", u)
    return u.rstrip("/")


class FactBase:
    def __init__(self, factbase_path, register_path=None):
        self.facts = {f["fid"]: f for f in json.load(open(factbase_path))}
        self.register = json.load(open(register_path)) if register_path else []
        self._by_url = {_norm_url(r["url"]): r["tag"] for r in self.register if r.get("url")}

    def __contains__(self, fid):
        return fid in self.facts

    def tag(self, fid):
        return self.facts[fid]["tag"]

    def conf(self, fid):
        return self.facts[fid]["confidence"]

    def text(self, fid):
        f = self.facts[fid]
        return f"{f['fact']} {f.get('quote') or ''}"

    def url_tag(self, url):
        return self._by_url.get(_norm_url(url))


def _canon(s):
    """'2,919.0' -> '2919'; '1.50' -> '1.5'; '-149' -> '149' (sign is carried by words in prose)."""
    s = s.replace(",", "").lstrip("-+")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


_NUM = re.compile(r"(?<![\w.])[-+]?\d[\d,]*(?:\.\d+)?")
_SCALE = re.compile(r"\s*(billion|bn|b\b)", re.I)


def numbers_in(text):
    """Every number in the text, normalised; '$1.5 billion' also yields its millions value '1500'."""
    out = set()
    for m in _NUM.finditer(text or ""):
        raw = m.group(0)
        c = _canon(raw)
        out.add(c)
        if _SCALE.match(text, m.end()):
            out.add(_canon(f"{float(raw.replace(',', '')) * 1000:.3f}"))
    return out


def _value_token(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return _canon(f"{v:.6f}")
    return _canon(str(v).replace("$", "").replace("%", "").strip())


def _lowest(confs):
    confs = [c for c in confs if c in CONF_ORDER]
    return max(confs, key=CONF_ORDER.index) if confs else ""


def validate(rows, fb, numeric_fields=(), *, name="table"):
    """Keep rows whose fids exist and whose numbers appear in the cited facts. Returns (good, problems)."""
    good, problems = [], []
    for n, r in enumerate(rows, 1):
        fids = [x.strip() for x in str(r.get("fid") or "").replace(",", ";").split(";") if x.strip()]
        if not fids:
            problems.append(f"{name} row {n}: no fid")
            continue
        missing = [f for f in fids if f not in fb]
        if missing:
            problems.append(f"{name} row {n}: unknown fid {', '.join(missing)}")
            continue
        if not r.get("calc"):
            have = set().union(*(numbers_in(fb.text(f)) for f in fids))
            bad = [fld for fld in numeric_fields if _value_token(r.get(fld)) not in (None, *have)]
            if bad:
                problems.append(f"{name} row {n}: {', '.join(f'{b}={r.get(b)}' for b in bad)} not in {';'.join(fids)}")
                continue
        out = dict(r)
        out["tag"] = sorted({fb.tag(f) for f in fids}, key=lambda t: int(t[1:]) if t[1:].isdigit() else 0)
        out["conf"] = _lowest(fb.conf(f) for f in fids)
        good.append(out)
    return good, problems


def _num(v):
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return s


def load_csv(path):
    with open(path, newline="") as fh:
        return [{k: _num(v) for k, v in r.items()} for r in csv.DictReader(fh)]


def table_rows(rows, *, tag, conf="High"):
    """Provenance for a research table that names its own source (tag may be a register tag or 'table: name')."""
    return [{**r, "tag": r.get("tag") or tag, "conf": r.get("conf") or conf} for r in rows]
