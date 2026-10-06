"""Time-series and share charts: direct labels, no titles, no legends, house palette."""
import textwrap

import numpy as np

from .style import P, SERIES, EmptyData, figure, finish, fmt_of, require, tidy

CHARTS = ["bar_line", "multi_line", "range_vs_actual", "stacked_share", "small_multiples", "kpi_tiles"]

LAB = 7  # pt, value labels (print size)
SMALL = 6.8


def _xs(rows, x):
    return [str(r[x]) for r in rows]


def _set_xticks(ax, labels, wrap=True):
    n = len(labels)
    ax.set_xticks(range(n))
    ax.set_xticklabels([l.replace(" ", "\n", 1) if (wrap and n > 6 and " " in l) else l for l in labels],
                       fontsize=SMALL, linespacing=1.0)


def _spread(vals, lo, hi, gap):
    """Nudge label positions apart (data units, ascending sweep) so labels keep at least `gap` of the axis range."""
    g = gap * (hi - lo)
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    out = list(vals)
    for a, b in zip(order, order[1:]):
        if out[b] - out[a] < g:
            out[b] = out[a] + g
    over = out[order[-1]] - (hi - g * 0.5) if order else 0
    if over > 0:
        for i in order:
            out[i] -= over
    return out


def bar_line(rows, x, bar, *, line=None, bar_fmt="money", line_fmt="pct", bar_name="", line_name="",
             out, w_cm=12.4, h_cm=5.6):
    rows = require(rows)
    bf, lf = fmt_of(bar_fmt), fmt_of(line_fmt)
    fig, ax = figure(w_cm, h_cm)
    tidy(ax, "y")
    n = len(rows)
    xs = np.arange(n)
    vals = [r[bar] for r in rows]
    top = max(max(vals), 1)
    ax.bar(xs, vals, width=0.5, color=[P["red"] if r.get("flag") else P["navy"] for r in rows], zorder=2)
    ymax = top / (0.5 if line else 0.82)
    ax.set_ylim(0, ymax)
    for i, v in enumerate(vals):
        ax.text(i, v + ymax * 0.015, bf(v), ha="center", va="bottom", fontsize=LAB, color=P["ink"])
    ax.set_yticklabels([])
    ax.grid(False)
    _set_xticks(ax, _xs(rows, x))
    pad = 0.0
    names = []
    if bar_name:
        names.append(bar_name)
    if line_name:
        names.append(line_name)
    pad = 1.3 if names else 0.0
    ax.set_xlim(-0.6, n - 0.4 + pad)
    if bar_name:
        ax.text(n - 1 + 0.38, vals[-1] * 0.5, bar_name, ha="left", va="center", fontsize=LAB, color=P["navy"])
    if line:
        pts = [(i, r[line]) for i, r in enumerate(rows) if r.get(line) is not None]
        if pts:
            ax2 = ax.twinx()
            ax2.set_axis_off()
            ys = [p[1] for p in pts]
            lo, hi = min(ys), max(ys)
            span = (hi - lo) or abs(hi) or 1
            # line lives in the top band 0.66..0.86 of the axes, clear of bar labels
            ax2.set_ylim(lo - span * (0.66 / 0.20), lo + span * (1 - 0.66) / 0.20 + 0)
            ax2.set_xlim(ax.get_xlim())
            ax2.plot([p[0] for p in pts], ys, color=P["teal"], linewidth=1.1, marker="o", markersize=2.8, zorder=3)
            for i, v in pts:
                flagged = rows[i].get("flag")
                ax2.text(i, v + span * 0.12, lf(v), ha="center", va="bottom", fontsize=LAB, color=P["red"] if flagged else P["teal"])
            if line_name:
                ax2.text(pts[-1][0] + 0.2, pts[-1][1], line_name, ha="left", va="center", fontsize=LAB, color=P["teal"])
    return finish(fig, out, rows, w_cm, h_cm)


def multi_line(rows, x, series, *, names=None, fmt="num", zero=True, highlight=None, out, w_cm=12.4, h_cm=5.6):
    rows = require(rows)
    f = fmt_of(fmt)
    names = names or {}
    fig, ax = figure(w_cm, h_cm)
    tidy(ax, "y")
    n = len(rows)
    ends, allv = [], []
    for k, s in enumerate(series):
        pts = [(i, r[s]) for i, r in enumerate(rows) if r.get(s) is not None]
        if not pts:
            continue
        hl = highlight == s
        col = SERIES[k % len(SERIES)] if highlight is None else (P["navy"] if hl else P["pale"])
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=col, linewidth=1.8 if hl else 1.1,
                solid_capstyle="round", zorder=3 if hl else 2)
        ax.plot(*pts[-1], marker="o", markersize=3, color=col, zorder=4)
        for i, r in enumerate(rows):
            if r.get("flag") and r.get(s) is not None:
                ax.plot(i, r[s], marker="o", markersize=3.5, color=P["red"], zorder=5)
        allv += [p[1] for p in pts]
        ends.append((pts[-1], s, col if highlight is None or hl else P["muted"]))
    lo, hi = min(allv), max(allv)
    lo = 0 if zero and lo > 0 else lo - (hi - lo) * 0.08
    hi = hi + (hi - lo) * 0.08
    ax.set_ylim(lo, hi)
    ax.set_yticklabels([])
    ax.grid(True, axis="y", color=P["rule"], linewidth=0.6)
    labs = [f"{names.get(s, s)} {f(p[1])}" for p, s, _ in ends]
    maxlen = max(len(l) for l in labs)
    ax.set_xlim(-0.3, n - 1 + 0.25 + maxlen * 0.105 * (n / 6) ** 0.5)
    ys = _spread([p[1] for p, _, _ in ends], lo, hi, 0.1)
    for (p, s, col), y, lab in zip(ends, ys, labs):
        ax.text(p[0] + 0.2, y, lab, ha="left", va="center", fontsize=LAB, color=col)
    _set_xticks(ax, _xs(rows, x))
    return finish(fig, out, rows, w_cm, h_cm)


def range_vs_actual(rows, x, lo, hi, actual, *, fmt="money", out, w_cm=12.4, h_cm=5.6):
    rows = require(rows)
    f = fmt_of(fmt)
    fig, ax = figure(w_cm, h_cm)
    tidy(ax, "y")
    n = len(rows)
    for i, r in enumerate(rows):
        ax.bar(i, r[hi] - r[lo], bottom=r[lo], width=0.34, color=P["faint"], zorder=2)
    acts = [r[actual] for r in rows]
    ax.scatter(range(n), acts, s=14, zorder=4, color=[P["red"] if r.get("flag") else P["navy"] for r in rows])
    ymin = min(min(r[lo] for r in rows), min(acts))
    ymax = max(max(r[hi] for r in rows), max(acts))
    span = (ymax - ymin) or 1
    ax.set_ylim(ymin - span * 0.12, ymax + span * 0.22)
    for i, r in enumerate(rows):
        ax.text(i, max(r[hi], r[actual]) + span * 0.04, f(r[actual]), ha="center", va="bottom", fontsize=LAB, color=P["ink"])
    ax.set_yticklabels([])
    ax.set_xlim(-0.6, n - 0.4 + 1.5)
    _set_xticks(ax, _xs(rows, x))
    last = rows[-1]
    glo, ghi = ax.get_ylim()
    ys = [last[actual], min((last[lo] + last[hi]) / 2, last[actual] - 0.12 * (ghi - glo))]
    ax.text(n - 1 + 0.4, ys[0], "Actual", ha="left", va="center", fontsize=LAB, color=P["navy"])
    ax.text(n - 1 + 0.4, ys[1], "Guidance", ha="left", va="center", fontsize=LAB, color=P["muted"])
    return finish(fig, out, rows, w_cm, h_cm)


def stacked_share(rows, x, parts, *, names=None, out, w_cm=12.4, h_cm=5.6):
    rows = require(rows)
    names = names or {}
    fig, ax = figure(w_cm, h_cm)
    tidy(ax, "y")
    n = len(rows)
    bottoms = np.zeros(n)
    shares = []
    for r in rows:
        tot = sum(r[p] for p in parts) or 1
        shares.append([100.0 * r[p] / tot for p in parts])
    shares = np.array(shares)
    for k, p in enumerate(parts):
        col = SERIES[k % len(SERIES)]
        ax.bar(range(n), shares[:, k], bottom=bottoms, width=0.55, color=col, zorder=2, edgecolor="white", linewidth=0.8)
        dark = k < 3
        for i in range(n):
            if shares[i, k] >= 7:
                ax.text(i, bottoms[i] + shares[i, k] / 2, f"{shares[i, k]:.0f}%", ha="center", va="center",
                        fontsize=LAB, color="white" if dark else P["ink"])
        mid = bottoms[-1] + shares[-1, k] / 2
        ax.text(n - 1 + 0.38, mid, names.get(p, p), ha="left", va="center", fontsize=LAB, color=P["ink"])
        bottoms = bottoms + shares[:, k]
    ax.set_ylim(0, 102)
    ax.set_yticks([])
    ax.grid(False)
    ax.set_xlim(-0.6, n - 0.4 + 1.6)
    _set_xticks(ax, _xs(rows, x))
    return finish(fig, out, rows, w_cm, h_cm)


def small_multiples(panels, *, ncols=4, out, w_cm=12.4, h_cm=5.6):
    live = [p for p in (panels or []) if p.get("rows")]
    if not live:
        raise EmptyData("no panels with rows")
    nrows = -(-len(live) // ncols)
    ncols = min(ncols, len(live))
    fig, axes = figure(w_cm, h_cm, nrows, ncols, squeeze=False)
    allrows = []
    for a in axes.flat:
        a.set_axis_off()
    for ax, p in zip(axes.flat, live):
        ax.set_axis_on()
        tidy(ax, "y")
        rows = p["rows"]
        allrows += rows
        f = fmt_of(p.get("fmt", "num"))
        labels = _xs(rows, p["x"])
        ys = [r[p["y"]] for r in rows]
        n = len(ys)
        top = max(ys)
        base = 0 if p.get("kind") == "bar" or min(ys) >= 0 and min(ys) < top * 0.5 else min(ys) - (top - min(ys)) * 0.1
        rng = (top - base) or 1
        ax.set_ylim(base, top + rng * 0.42)
        if p.get("kind") == "bar":
            ax.bar(range(n), ys, width=0.5, color=[P["red"] if r.get("flag") else P["navy"] for r in rows], zorder=2)
        else:
            ax.plot(range(n), ys, color=P["teal"], linewidth=1.2, zorder=2)
        ax.plot(n - 1, ys[-1], "o", markersize=3, color=P["navy"], zorder=3)
        ax.text(n - 1 + 0.4, ys[-1] + rng * 0.16, f(ys[-1]), ha="right", va="bottom",
                fontsize=LAB, color=P["ink"])
        ax.set_title(p.get("title", ""), loc="left", fontsize=7.2, color=P["muted"], pad=3)
        ax.set_xlim(-0.6, n - 0.4)
        ax.set_yticklabels([])
        tk = sorted({0, n - 1})
        ax.set_xticks(tk)
        ax.set_xticklabels([labels[i] for i in tk], fontsize=SMALL)
        ax.get_xticklabels()[0].set_ha("left")
        if n > 1:
            ax.get_xticklabels()[-1].set_ha("right")
    return finish(fig, out, allrows, w_cm, h_cm, pad=0.4)


def kpi_tiles(tiles, *, ncols=4, out, w_cm=12.4, h_cm=5.6):
    tiles = require(tiles)
    nrows = -(-len(tiles) // ncols)
    fig, ax = figure(w_cm, h_cm)
    ax.set_axis_off()
    ax.set_xlim(0, ncols)
    ax.set_ylim(nrows, 0)
    gx, gy = 0.06, 0.08
    allrows = []
    for k, t in enumerate(tiles):
        cx, cy = k % ncols, k // ncols
        x0, y0 = cx + gx / 2, cy + gy / 2
        w, h = 1 - gx, 1 - gy
        ax.add_patch(__import__("matplotlib").patches.Rectangle((x0, y0), w, h, facecolor=P["fill"], edgecolor="none"))
        allrows += t.get("rows") or []
        tx = x0 + 0.06
        ax.text(tx, y0 + h * 0.13, t["label"], fontsize=SMALL, color=P["muted"], va="center", ha="left")
        ax.text(tx, y0 + h * 0.34, str(t["value"]), fontsize=13, color=P["red"] if t.get("flag") else P["navy"],
                fontweight="bold", va="center", ha="left")
        note = textwrap.wrap(t.get("note") or "", 26)[:2]
        ax.text(tx, y0 + h * 0.50, "\n".join(note), fontsize=SMALL, color=P["muted"], va="top", ha="left", linespacing=1.15)
        sp = t.get("spark")
        if sp and len(sp) > 1:
            xs = np.linspace(tx, x0 + w - 0.09, len(sp))
            lo, hi = min(sp), max(sp)
            yy = y0 + h * 0.92 - (np.array(sp) - lo) / ((hi - lo) or 1) * h * 0.2
            ax.plot(xs, yy, color=P["teal"], linewidth=1.0, solid_capstyle="round")
            ax.plot(xs[-1], yy[-1], "o", markersize=2.8, color=P["teal"])
    return finish(fig, out, allrows, w_cm, h_cm, pad=0.2)
