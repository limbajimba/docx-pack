#!/usr/bin/env python3
"""Horizontal bar chart in the document's palette, as a PNG for a .docx.

Form: magnitude by category -> horizontal bars, one hue, weakest (or flagged) rows in the
status colour, direct value labels, optional threshold line. No legend (single series).

Usage:
  python3 chart_bars.py --spec house/silvertree.style-spec.json --data data.json --out chart.png
data.json: {"title": "...", "rows": [{"label": "A1 ...", "value": 7.0, "flag": false}, ...],
            "max": 10, "threshold": 7.0, "threshold_label": "7.0 Solid floor"}
"""
import argparse, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager


def pick_font(preferred):
    names = {f.name for f in font_manager.fontManager.ttflist}
    for n in preferred:
        if n in names:
            return n
    return "DejaVu Sans"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width-cm", type=float, default=15.5)
    ap.add_argument("--row-cm", type=float, default=0.62)
    a = ap.parse_args()
    spec = json.load(open(a.spec)); data = json.load(open(a.data))
    col = spec["colors"]
    font = pick_font([spec["font"].get("preview_alias", ""), spec["font"]["body"], "Gill Sans", "Helvetica Neue", "Arial"])
    plt.rcParams.update({"font.family": font, "font.size": 9})
    rows = data["rows"]; n = len(rows)
    ink, muted, base, flag, rule = "#" + col["ink"], "#" + col["muted"], "#" + col["navy"], "#" + col["red"], "#" + col["rule"]
    w_in = a.width_cm / 2.54; h_in = (a.row_cm * n + 1.6) / 2.54
    fig, ax = plt.subplots(figsize=(w_in, h_in), dpi=200)
    ys = list(range(n))[::-1]
    vals = [r["value"] for r in rows]
    colors = [flag if r.get("flag") else base for r in rows]
    ax.barh(ys, vals, height=0.52, color=colors, linewidth=0)
    for y, v, r in zip(ys, vals, rows):
        ax.text(v + data.get("max", 10) * 0.012, y, f"{v:.1f}", va="center", ha="left", fontsize=8.5, color=ink, fontweight="bold")
    ax.set_yticks(ys)
    ax.set_yticklabels([r["label"] for r in rows], fontsize=8.5)
    for tick, r in zip(ax.get_yticklabels(), rows):
        tick.set_color(flag if r.get("flag") else ink)
        if r.get("flag"):
            tick.set_fontweight("bold")
    ax.set_xlim(0, data.get("max", 10))
    ax.set_xticks(range(0, int(data.get("max", 10)) + 1, 2))
    ax.tick_params(axis="x", colors=muted, labelsize=8, length=0)
    ax.tick_params(axis="y", length=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(rule)
    ax.xaxis.grid(True, color=rule, linewidth=0.6)
    ax.set_axisbelow(True)
    if data.get("threshold") is not None:
        t = data["threshold"]
        ax.axvline(t, color="#" + col["teal"], linewidth=0.9, linestyle=(0, (3, 2)))
        mx = data.get("max", 10); right_side = t < mx * 0.6
        ax.text(t + (0.08 if right_side else -0.08), -0.75, data.get("threshold_label", f"{t}"), fontsize=7, color="#" + col["teal"], va="center", ha="left" if right_side else "right")
    if data.get("title"):
        ax.set_title(data["title"], fontsize=9.5, color=ink, fontweight="bold", loc="center", pad=8)
    ax.set_ylim(-1.1, n - 0.4)
    fig.tight_layout(pad=0.4)
    fig.savefig(a.out, dpi=200, facecolor="white")
    print(f"wrote {a.out} ({n} rows, font {font})")


if __name__ == "__main__":
    main()
