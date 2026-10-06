#!/usr/bin/env python3
"""Visual fact pack: render a plan's panels with the viz library and build a landscape house DOCX.

Usage:
  python3 scripts/build_visual_pack.py --plan plan.json --out out.docx \
      [--spec house/silvertree-landscape.style-spec.json] [--charts-dir dir] [--content-out c.json]

plan.json:
  meta            house-docx meta (title, kicker, date, right_lines, footer_title, subject)
  factbase, register, data_module   paths (relative to the plan file); data_module exposes
                  datasets(fb) -> {name: list | dict} and optionally PROBLEMS (list of strings)
  intro           optional blocks placed after the title band (e.g. a basis paragraph)
  pages           [{h1, headline, headline_fids, missing, panels: [{id, chart, data, args, title, note,
                    w_cm, h_cm, span, conflict}], cols}]
Checks (fail the build): banned words in any text; a headline number that is not in its cited facts;
"flag" rows (red) in a panel not marked "conflict". Empty panels are dropped and reported.
"""
import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from viz import registry  # noqa: E402
from viz.data import FactBase, numbers_in  # noqa: E402
from viz.style import EmptyData  # noqa: E402

BANNED = ["should", "recommend", "attractive", "upside", "next step", "strong fit", "we suggest", "valuation"]


def banned_in(text):
    t = (text or "").lower()
    return [w for w in BANNED if re.search(rf"\b{re.escape(w)}", t)]


def load_module(path):
    spec = importlib.util.spec_from_file_location("deal_viz_data", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def has_flag(data):
    rows = data if isinstance(data, list) else [x for v in (data or {}).values() if isinstance(v, list) for x in v]
    return any(isinstance(r, dict) and r.get("flag") for r in rows)


def caption_sources(chart, max_tags=40):
    tags = chart.sources
    shown = ", ".join(tags[:max_tags]) + (f" and {len(tags) - max_tags} more" if len(tags) > max_tags else "")
    parts = []
    if shown:
        parts.append(f"Sources: {shown}")
    if chart.confidence:
        parts.append(f"lowest confidence: {chart.confidence}")
    return "  ·  ".join(parts)


def build(plan_path, out, spec, charts_dir=None, content_out=None):
    plan_path = Path(plan_path).resolve()
    base = plan_path.parent
    plan = json.loads(plan_path.read_text())
    rel = lambda p: (base / p).resolve()  # noqa: E731
    fb = FactBase(rel(plan["factbase"]), rel(plan["register"]) if plan.get("register") else None)
    mod = load_module(rel(plan["data_module"]))
    sets = mod.datasets(fb)
    data_problems = list(getattr(mod, "PROBLEMS", []))
    charts = registry()
    cdir = Path(charts_dir) if charts_dir else Path(out).resolve().parent / (Path(out).stem + "-charts")
    cdir.mkdir(parents=True, exist_ok=True)

    problems, dropped, blocks = [], [], [{"type": "title_band"}]
    blocks += plan.get("intro", [])
    for pn, page in enumerate(plan["pages"]):
        label = page.get("h1", f"page {pn}")
        for field in ("h1", "headline", "missing"):
            for w in banned_in(page.get(field)):
                problems.append(f"{label}: banned word '{w}' in {field}")
        fids = page.get("headline_fids", [])
        if page.get("headline"):
            unknown = [f for f in fids if f not in fb]
            if unknown:
                problems.append(f"{label}: headline cites unknown {unknown}")
            have = set().union(*(numbers_in(fb.text(f)) for f in fids if f in fb)) if fids else set()
            extra = set(page.get("headline_numbers_from_data", []))
            for n in numbers_in(page["headline"]):
                if n not in have and n not in extra and not re.fullmatch(r"(19|20)\d\d", n):
                    problems.append(f"{label}: headline number {n} not in {fids or 'any cited fact'}")
        cells = []
        for pan in page.get("panels", []):
            for field in ("title", "note"):
                for w in banned_in(pan.get(field)):
                    problems.append(f"{label}/{pan['id']}: banned word '{w}' in {field}")
            fn = charts.get(pan["chart"])
            if not fn:
                problems.append(f"{label}/{pan['id']}: unknown chart {pan['chart']}")
                continue
            data = sets.get(pan["data"]) if pan.get("data") else None
            if pan.get("data") and data is None:
                dropped.append(f"{label}/{pan['id']}: no dataset '{pan['data']}'")
                continue
            if has_flag(data) and not pan.get("conflict"):
                problems.append(f"{label}/{pan['id']}: red-flagged rows in a panel not marked conflict")
            kw = dict(pan.get("args", {}))
            kw.update(out=str(cdir / f"{pn:02d}-{pan['id']}.png"), w_cm=pan.get("w_cm", 12.2), h_cm=pan.get("h_cm", 5.4))
            try:
                if isinstance(data, list):
                    ch = fn(data, **kw)
                elif isinstance(data, dict):
                    ch = fn(**data, **kw)
                else:
                    ch = fn(**kw)
            except EmptyData:
                dropped.append(f"{label}/{pan['id']}: empty")
                continue
            except Exception as e:
                raise RuntimeError(f"{label}/{pan['id']} ({pan['chart']}): {e}") from e
            cells.append({"path": ch.png, "width_cm": ch.w_cm, "height_cm": ch.h_cm, "title": pan.get("title", ""),
                          "sources": caption_sources(ch), "note": pan.get("note", ""), "span": pan.get("span", 1)})
        # a new page starts at its heading (page_break_before), so a full page never leaves a blank one behind it
        if page.get("h1"):
            blocks.append({"type": "h1", "text": page["h1"], "toc": False, "page_break_before": bool(pn)})
        elif pn:
            blocks.append({"type": "pagebreak"})
        if page.get("headline"):
            blocks.append({"type": "verdict", "text": page["headline"]})
        blocks += page.get("blocks_before", [])
        for name in page.get("blocks_data", []):  # house-docx blocks built by the data module (e.g. a sourced table)
            bl = sets.get(name)
            if bl:
                blocks += bl
            else:
                dropped.append(f"{label}: no blocks '{name}'")
        if cells:
            blocks.append({"type": "figure_grid", "cols": page.get("cols", 2), "cells": cells})
        if page.get("missing"):
            blocks.append({"type": "basis", "text": f"Missing: {page['missing']}"})

    for p in data_problems:
        print(f"data: {p}")
    for d in dropped:
        print(f"dropped: {d}")
    if problems:
        for p in problems:
            print(f"CHECK FAIL: {p}")
        raise SystemExit(f"{len(problems)} check failures; nothing built")
    content = {"meta": plan["meta"], "blocks": blocks}
    cpath = Path(content_out) if content_out else cdir / "content.json"
    cpath.write_text(json.dumps(content, indent=1, ensure_ascii=False))
    subprocess.run(["node", str(HERE / "build_docx.js"), "--spec", str(spec), "--content", str(cpath), "--out", str(out)], check=True)
    n_fig = sum(len(b["cells"]) for b in blocks if b["type"] == "figure_grid")
    print(f"{len(plan['pages'])} pages, {n_fig} charts, {len(dropped)} dropped, {len(data_problems)} data problems -> {out}")
    return {"charts": n_fig, "dropped": dropped, "data_problems": data_problems}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--spec", default=str(HERE.parent / "house" / "silvertree-landscape.style-spec.json"))
    ap.add_argument("--charts-dir")
    ap.add_argument("--content-out")
    a = ap.parse_args()
    build(a.plan, a.out, a.spec, a.charts_dir, a.content_out)
