"""Category and event charts: timeline_lanes, dot_rank, confidence_grid.

No titles, no legend boxes, direct labels only. Text is never smaller than 6.5 pt at print size.
"""
import datetime as dt
import math
import textwrap

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from .style import CM, Chart, P, SERIES, fmt_of, figure, finish, provenance, require, tidy

CHARTS = ["timeline_lanes", "dot_rank", "confidence_grid"]

PT_CM = 2.54 / 72  # one point in cm
LABEL_PT = 7.0
PITCH = 0.32       # row pitch for timeline labels, cm
GAP = 0.24         # clearance between lane line and first label row, cm
AXIS_BAND = 0.55   # room for year ticks, cm


# ---------------------------------------------------------------- timeline

def _parse(d):
    d = str(d)
    if len(d) == 4:
        d += "-07-01"
    elif len(d) == 7:
        d += "-15"
    return dt.date.fromisoformat(d)


def _trunc(s, n):
    s = str(s)
    return s if len(s) <= n else s[: max(n - 1, 1)].rstrip() + "…"


def _ticks(a, b):
    """(date, label) ticks: years for long spans, then quarters, months, weeks."""
    span = (b - a).days
    out = []
    if span > 900:
        step = 1 if span < 365 * 13 else 2
        for y in range(a.year + (0 if a == dt.date(a.year, 1, 1) else 1), b.year + 1, step):
            out.append((dt.date(y, 1, 1), str(y)))
    elif span > 40:
        step = 3 if span > 150 else 1
        y, m = a.year, a.month
        while True:
            d = dt.date(y, m, 1)
            if d > b:
                break
            if d >= a and (m - 1) % step == 0:
                out.append((d, d.strftime("%b %Y")))
            m += 1
            if m > 12:
                y, m = y + 1, 1
    else:
        d = a + dt.timedelta(days=(7 - a.weekday()) % 7)
        while d <= b:
            out.append((d, f"{d.day} {d.strftime('%b')}"))
            d += dt.timedelta(days=7)
    return out


def _hits(b1, b2, px=0.12, py=0.02):
    return not (b1[1] + px <= b2[0] or b2[1] + px <= b1[0] or b1[3] + py <= b2[2] or b2[3] + py <= b1[2])


def _place_lane(items, x_min, x_max):
    """Greedy rows above/below the lane line. items: [(x, width)] in date order.
    Returns [(side, row, align, box)] and (rows_up, rows_down). Boxes are (x0, x1, y0, y1) relative to the lane line."""
    # Right to left: a label runs rightwards from its marker, so later (right-hand) markers must be placed first
    # or their leaders would be blocked by the boxes of the labels to their left.
    boxes, leaders, out = [], [], [None] * len(items)
    up = dn = 0
    for idx in reversed(range(len(items))):
        x, w = items[idx]
        done = None
        for r in range(1, 200):
            for side in (1, -1):
                for align in (("l",) if x - 0.03 + w <= x_max else ("r",)):  # right-aligned only when a label would run off the right edge
                    x0, x1 = (x - 0.03, x - 0.03 + w) if align == "l" else (x + 0.03 - w, x + 0.03)
                    if x0 < x_min or x1 > x_max:
                        continue
                    e = GAP + (r - 1) * PITCH
                    ya, yb = (e, e + PITCH - 0.02) if side > 0 else (-(e + PITCH - 0.02), -e)
                    box = (x0, x1, ya, yb)
                    lead = (x, x, min(0, side * e), max(0, side * e))
                    if any(_hits(box, o) for o in boxes):
                        continue
                    if any(lead[0] >= o[0] - 0.05 and lead[0] <= o[1] + 0.05 and lead[2] < o[3] and lead[3] > o[2] for o in boxes):
                        continue
                    if any(l[0] >= box[0] - 0.05 and l[0] <= box[1] + 0.05 and l[2] < box[3] and l[3] > box[2] for l in leaders):
                        continue
                    done = (side, r, align, box)
                    boxes.append(box)
                    leaders.append(lead)
                    break
                if done:
                    break
            if done:
                break
        if done is None:  # last resort: ignore leader crossings, keep labels from overprinting each other
            for r in range(1, 400):
                for side in (1, -1):
                    x0, x1 = (x - 0.03, x - 0.03 + w) if x - 0.03 + w <= x_max else (x + 0.03 - w, x + 0.03)
                    e = GAP + (r - 1) * PITCH
                    ya, yb = (e, e + PITCH - 0.02) if side > 0 else (-(e + PITCH - 0.02), -e)
                    box = (x0, x1, ya, yb)
                    if not any(_hits(box, o) for o in boxes):
                        done = (side, r, "l" if x0 >= x - 0.03 else "r", box)
                        boxes.append(box)
                        leaders.append((x, x, min(0, side * e), max(0, side * e)))
                        break
                if done:
                    break
        out[idx] = done
        if done is None:
            raise RuntimeError("timeline label could not be placed")
        if done[0] > 0:
            up = max(up, done[1])
        else:
            dn = max(dn, done[1])
    return out, (up, dn)


def build_timeline(events, *, lanes=None, start=None, end=None, size_fmt="money", label_max=34, w_cm=25, h_cm=6):
    """Lay out and draw the timeline. Returns {"fig","ax","texts","renderer","w_cm","h_cm"}; h_cm grows if labels need it."""
    require(events)
    f = fmt_of(size_fmt)
    ev = sorted(({**e, "_d": _parse(e["date"])} for e in events), key=lambda e: e["_d"])
    names = list(lanes) if lanes else []
    for e in ev:
        if e.get("lane") not in names:
            names.append(e.get("lane"))
    a = _parse(start) if start else ev[0]["_d"]
    b = _parse(end) if end else ev[-1]["_d"]
    if not start or not end:
        pad = dt.timedelta(days=max(int((b - a).days * 0.03), 3 if b > a else 30))
        a = a if start else a - pad
        b = b if end else b + pad

    fig0, _ = figure(w_cm, h_cm)
    r0 = fig0.canvas.get_renderer()

    def width(s, pt, **kw):
        t = fig0.text(0, 0, s, fontsize=pt, **kw)
        wd = t.get_window_extent(r0).width / fig0.dpi * 2.54
        t.remove()
        return wd

    wrapped = {n: textwrap.wrap(str(n), 17) or [""] for n in names}
    name_w = max(width(l, 7.5, fontweight="bold") for ls in wrapped.values() for l in ls)
    x0, x1 = 0.15 + name_w + 0.3, w_cm - 0.65
    span = max((b - a).days, 1)
    for e in ev:
        lab = _trunc(e["label"], label_max)
        e["_text"] = lab + (f"  {f(e['size'])}" if e.get("size") else "")
        e["_w"] = width(e["_text"], LABEL_PT) + 0.04
        e["_f"] = (e["_d"] - a).days / span
    # labels run rightwards from their marker, so shorten the axis until the last labels fit inside the figure
    for e in ev:
        if e["_f"] > 0.02:
            x1 = min(x1, x0 + (w_cm - 0.1 - e["_w"] - x0) / e["_f"])
    x1 = max(x1, x0 + 4)
    for e in ev:
        e["_x"] = x0 + e["_f"] * (x1 - x0)
    plt.close(fig0)

    placed, extents = {}, {}
    for n in names:
        mine = [e for e in ev if e.get("lane") == n]
        res, (up, dn) = _place_lane([(e["_x"], e["_w"]) for e in mine], x0 - 0.1, w_cm - 0.08)
        for e, p in zip(mine, res):
            placed[id(e)] = p
        extents[n] = (up, dn)

    need, below = {}, {}
    for n in names:
        up, dn = extents[n]
        ue = GAP + up * PITCH - (GAP if not up else 0) if up else 0.3
        de = GAP + dn * PITCH - (GAP if not dn else 0) if dn else 0.3
        if up:
            ue = GAP + (up - 1) * PITCH + PITCH
        if dn:
            de = GAP + (dn - 1) * PITCH + PITCH
        need[n] = max(ue + de + 0.12, len(wrapped[n]) * 0.32 + 0.14)
        below[n] = de + 0.06
    total = AXIS_BAND + 0.08 + sum(need.values())
    H = max(h_cm, total)
    extra = (H - total) / len(names)

    fig, ax = figure(w_cm, H)
    ax.set_position([0, 0, 1, 1])
    ax.set_xlim(0, w_cm)
    ax.set_ylim(0, H)
    ax.axis("off")

    ymax_marker = max([e["size"] for e in ev if e.get("size")] or [1])
    y_top = H - 0.08
    tops = {}
    for n in names:
        h = need[n] + extra
        tops[n] = (y_top, y_top - h)
        y_top -= h
    ybase = AXIS_BAND
    for n in names:
        t, bt = tops[n]
        cy = bt + below[n] + (t - bt - need[n]) / 2 + (0 if True else 0)
        cy = bt + below[n] + extra / 2
        ax.plot([x0, x1], [cy, cy], color=P["faint"], lw=0.6, zorder=1)
        ax.plot([0.1, w_cm - 0.1], [bt, bt], color=P["rule"], lw=0.8, zorder=0)
        ls = wrapped[n]
        ax.text(0.15, cy, "\n".join(ls), fontsize=7.5, fontweight="bold", color=P["slate"], ha="left", va="center",
                linespacing=1.15)
        tops[n] = (t, bt, cy)
    ax.plot([0.1, w_cm - 0.1], [ybase, ybase], color=P["pale"], lw=0.8, zorder=0)
    for d, lab in _ticks(a, b):
        x = x0 + (d - a).days / max((b - a).days, 1) * (x1 - x0)
        ax.plot([x, x], [ybase, ybase - 0.09], color=P["pale"], lw=0.8)
        ax.plot([x, x], [ybase, H - 0.08], color=P["rule"], lw=0.4, zorder=0)
        ax.text(x, ybase - 0.14, lab, fontsize=7, color=P["muted"], ha="center", va="top")

    texts = []
    for e in ev:
        n = e.get("lane")
        cy = tops[n][2]
        side, r, align, box = placed[id(e)]
        i = names.index(n)
        col = P["red"] if e.get("flag") else SERIES[min(i, 2)]
        s = 16 if not e.get("size") else 18 + 60 * math.sqrt(e["size"] / ymax_marker)
        ax.plot([e["_x"], e["_x"]], [cy, cy + (box[2] if side > 0 else box[3])], color=P["pale"], lw=0.5, zorder=2)
        ax.scatter([e["_x"]], [cy], s=s, facecolor=P["white"] if e.get("hollow") else col, edgecolor=col, linewidth=0.9, zorder=4)
        ty = cy + (box[2] + box[3]) / 2
        tx = box[0] if align == "l" else box[1]
        texts.append(ax.text(tx, ty, e["_text"], fontsize=LABEL_PT, color=P["red"] if e.get("flag") else P["ink"],
                             ha="left" if align == "l" else "right", va="center", zorder=5))
    return {"fig": fig, "ax": ax, "texts": texts, "renderer": fig.canvas.get_renderer(), "w_cm": w_cm, "h_cm": H}


def timeline_lanes(events, *, lanes=None, start=None, end=None, size_fmt="money", label_max=34, out, w_cm=25, h_cm=6):
    info = build_timeline(events, lanes=lanes, start=start, end=end, size_fmt=size_fmt, label_max=label_max, w_cm=w_cm, h_cm=h_cm)
    info["fig"].savefig(out, dpi=200, facecolor="white")
    plt.close(info["fig"])
    sources, conf = provenance(events)
    return Chart(str(out), sources, conf, w_cm, info["h_cm"])


# ---------------------------------------------------------------- dot rank

def build_dot_rank(rows, label, value, *, fmt="num", highlight=None, log=False, note_field=None, w_cm=12.4, h_cm=5.6):
    rows = [r for r in require(rows) if r.get(value) is not None]
    require(rows)
    order = sorted(rows, key=lambda r: -r[value])
    f = fmt_of(fmt)
    hl = set([highlight] if isinstance(highlight, str) else (highlight or []))
    fig, ax = figure(w_cm, h_cm)
    tidy(ax, grid="x")
    n = len(order)
    vals = [r[value] for r in order]
    lo = min(vals) / 2.5 if log else 0
    if log:
        ax.set_xscale("log")
    ax.set_xlim(lo, max(vals) * (3 if log else 1.3))
    ax.set_ylim(n - 0.4, -0.6)
    ax.set_yticks(range(n))
    ax.set_yticklabels([str(r[label]) for r in order], fontsize=7.5)
    ax.set_xticks([])
    ax.minorticks_off()
    ax.grid(False)
    ax.hlines(range(n), lo, vals, color=P["faint"], lw=0.8, zorder=1)
    texts = []
    for i, r in enumerate(order):
        is_hl = r[label] in hl
        col = P["red"] if r.get("flag") else (P["navy"] if is_hl else P["slate"])
        ax.scatter([r[value]], [i], s=30 if is_hl else 22, color=col, zorder=3)
        t = ax.annotate(f(r[value]), (r[value], i), xytext=(5, 0), textcoords="offset points", va="center", fontsize=7.5,
                        color=col if (is_hl or r.get("flag")) else P["ink"], fontweight="bold" if is_hl else "normal")
        texts.append(t)
        if note_field and r.get(note_field):
            texts.append(ax.annotate(str(r[note_field]), xy=(1, 0.5), xycoords=t, xytext=(5, 0), textcoords="offset points",
                                     va="center", fontsize=7, color=P["muted"]))
    for tl, r in zip(ax.get_yticklabels(), order):
        hot = r[label] in hl
        tl.set_color(P["red"] if r.get("flag") else (P["navy"] if hot else P["slate"]))
        tl.set_fontweight("bold" if hot else "normal")
    # widen the axis until every value/note label sits inside it
    for _ in range(6):
        fig.tight_layout(pad=0.3)
        rend = fig.canvas.get_renderer()
        bb = ax.get_window_extent(rend)
        right = max(t.get_window_extent(rend).x1 for t in texts)
        frac = (right - bb.x0) / bb.width
        if frac <= 0.985:
            break
        hi = ax.get_xlim()[1]
        ax.set_xlim(lo, hi ** (frac / 0.97) if log else hi * frac / 0.97)
        if log:
            ax.set_xlim(lo, math.exp(math.log(hi) + (math.log(hi) - math.log(lo)) * (frac / 0.97 - 1)))
    return fig, ax, order


def dot_rank(rows, label, value, *, fmt="num", highlight=None, log=False, note_field=None, out, w_cm=12.4, h_cm=5.6):
    fig, ax, order = build_dot_rank(rows, label, value, fmt=fmt, highlight=highlight, log=log, note_field=note_field,
                                    w_cm=w_cm, h_cm=h_cm)
    return finish(fig, out, order, w_cm, h_cm)


# ---------------------------------------------------------------- confidence grid

CONF_COLS = [("High", "High"), ("Medium", "Medium"), ("Low", "Low"), ("Not found", "Not found")]
COV_COLS = [("covered", "Covered"), ("partly", "Partly"), ("not public", "Not public")]


def build_confidence_grid(rows, *, w_cm=12.4, h_cm=5.6):
    rows = require(rows)
    has_cov = any(k in r for r in rows for k, _ in COV_COLS)
    has_conf = any(k in r for r in rows for k, _ in CONF_COLS)
    blocks = ([CONF_COLS] if has_conf or not has_cov else []) + ([COV_COLS] if has_cov else [])
    if any("in pack" in r for r in rows):  # facts carried into the fact pack, as its own block
        blocks.append([("in pack", "In fact pack")])
    fig, ax = figure(w_cm, h_cm)
    ax.axis("off")
    n = len(rows)
    xs, x = [], 0.0
    for bi, blk in enumerate(blocks):
        for key, head in blk:
            xs.append((bi, key, head, x))
            x += 1
        x += 0.45
    ncols = len(xs)
    ax.set_xlim(-0.05, x - 0.45 + 0.05)
    ax.set_ylim(n, -1.0)
    mx = {bi: max([int(r.get(k) or 0) for r in rows for k, _ in blk] + [1]) for bi, blk in enumerate(blocks)}
    cells = []
    for _, key, head, cx in xs:
        ax.text(cx + 0.5, -0.5, head, ha="center", va="center", fontsize=7, color=P["muted"], fontweight="bold")
    for i, r in enumerate(rows):
        ax.text(-0.12, i + 0.5, str(r["area"]), ha="right", va="center", fontsize=7.5, color=P["slate"], clip_on=False)
        for bi, key, head, cx in xs:
            c = int(r.get(key) or 0)
            if c:
                alpha = 0.10 + 0.90 * c / mx[bi]
                ax.add_patch(Rectangle((cx, i), 1, 1, facecolor=P["navy"], alpha=alpha, edgecolor="none"))
                tc = P["white"] if alpha > 0.5 else P["navy"]
            else:
                alpha = 0
                ax.add_patch(Rectangle((cx, i), 1, 1, facecolor=P["fill"], edgecolor="none"))
                tc = P["muted"]
            ax.add_patch(Rectangle((cx, i), 1, 1, facecolor="none", edgecolor=P["white"], linewidth=1.4))
            ax.text(cx + 0.5, i + 0.5, f"{c}", ha="center", va="center", fontsize=7.5, color=tc,
                    fontweight="bold" if c else "normal")
            cells.append((r["area"], key, c))
    fig.tight_layout(pad=0.3)
    return fig, ax, {"areas": [r["area"] for r in rows], "ncols": ncols, "cells": cells}


def confidence_grid(rows, *, out, w_cm=12.4, h_cm=5.6):
    fig, ax, info = build_confidence_grid(rows, w_cm=w_cm, h_cm=h_cm)
    return finish(fig, out, rows, w_cm, h_cm)
