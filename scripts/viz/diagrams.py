"""Diagrams: Sankey (own bezier renderer), org chart and logo wall. No chart titles; house palette only.

Red is used only for rows that carry "flag": True. Layout helpers (sankey_layout, org_layout, logo_layout)
are pure and testable; the chart functions draw them in centimetre coordinates so text sizes stay true.
"""
import math

import matplotlib.patches as mpatches
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path
from matplotlib.textpath import TextPath

from .style import Chart, EmptyData, P, figure, fmt_of, provenance, require, setup  # noqa: F401
import matplotlib.pyplot as plt

CHARTS = ["sankey", "org_chart", "logo_wall"]
TOL = 0.005  # a node whose outflows fall short of its inflows by more than this gets an "other, calculated" flow


def finish(fig, out, rows, w_cm, h_cm, pad=0.0):
    """Like style.finish but without tight_layout: these axes are drawn in true centimetres and must not rescale."""
    fig.savefig(out, dpi=200, facecolor="white")
    plt.close(fig)
    sources, conf = provenance(rows)
    return Chart(str(out), sources, conf, w_cm, h_cm)


# ---------------------------------------------------------------- text helpers
def text_w(s, size, weight="normal"):
    """Width of a string in cm at the given point size."""
    if not s:
        return 0.0
    fp = FontProperties(family=setup(), weight=weight)
    return TextPath((0, 0), s, size=size, prop=fp).get_extents().width / 72 * 2.54


def fit_lines(text, width_cm, size, max_lines=2, weight="normal"):
    """Greedy word wrap into at most max_lines lines no wider than width_cm; the last line ends in an ellipsis
    if the text had to be cut."""
    words = str(text).split()
    if not words:
        return []
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if cur and text_w(t, size, weight) > width_cm:
            lines.append(cur)
            cur = w
        else:
            cur = t
    lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + [" ".join(lines[max_lines - 1:])]
        cut = True
    else:
        cut = False
    out = []
    for i, ln in enumerate(lines):
        last = i == len(lines) - 1
        if text_w(ln, size, weight) > width_cm or (last and cut):
            while ln and text_w(ln + "…", size, weight) > width_cm:
                ln = ln[:-1]
            ln = ln.rstrip() + "…"
        out.append(ln)
    return out


def _flagged(rows):
    return any(r.get("flag") for r in rows)


# ---------------------------------------------------------------- Sankey
def sankey_layout(nodes, flows, height=8.0, gap=0.5):
    """Place nodes in columns and flows between them.

    Returns (nodes, flows). Each node gets y, h (same unit as height), in_sum, out_sum, value, stub.
    Each flow gets h, y0 (top at the source) and y1 (top at the destination). Node height is the larger of
    inflow and outflow; a node whose outflows fall short of its inflows by more than 0.5 percent gets a flow
    to an "other, calculated" stub node in the next column, never a forced balance.
    """
    nodes = [dict(n, stub=False) for n in nodes]
    flows = [dict(f) for f in flows]
    ids = {n["id"] for n in nodes}
    for f in flows:
        if f["src"] not in ids or f["dst"] not in ids:
            raise KeyError(f"flow {f['src']}->{f['dst']} names an unknown node")

    def sums():
        i, o = {n["id"]: 0.0 for n in nodes}, {n["id"]: 0.0 for n in nodes}
        for f in flows:
            o[f["src"]] += f["value"]
            i[f["dst"]] += f["value"]
        return i, o
    ins, outs = sums()
    for n in list(nodes):
        i, o = ins[n["id"]], outs[n["id"]]
        if o > 0 and i > 0 and o < i * (1 - TOL):
            sid = f"_other_{n['id']}"
            nodes.append({"id": sid, "label": "Other, calculated", "col": n["col"] + 1, "stub": True})
            flows.append({"src": n["id"], "dst": sid, "value": i - o, "kind": "other", "tag": None, "conf": None})
    ins, outs = sums()
    for n in nodes:
        n["in_sum"], n["out_sum"] = ins[n["id"]], outs[n["id"]]
        n["value"] = max(n["in_sum"], n["out_sum"])
    cols = sorted({n["col"] for n in nodes})
    by_col = {c: [n for n in nodes if n["col"] == c] for c in cols}
    order = {n["id"]: k for k, n in enumerate(nodes)}

    scale = min((height - gap * (len(v) - 1)) / max(sum(n["value"] for n in v), 1e-12) for v in by_col.values())
    for n in nodes:
        n["h"] = n["value"] * scale
    by = {n["id"]: n for n in nodes}

    for ci, c in enumerate(cols):
        col = by_col[c]
        if ci == 0:
            col.sort(key=lambda n: order[n["id"]])
            total = sum(n["h"] for n in col) + gap * (len(col) - 1)
            y = (height - total) / 2
            for n in col:
                n["y"] = y
                y += n["h"] + gap
            continue
        want = {}
        for n in col:
            w = [(by[f["src"]]["y"] + by[f["src"]]["h"] / 2, f["value"]) for f in flows
                 if f["dst"] == n["id"] and "y" in by[f["src"]]]
            tot = sum(v for _, v in w)
            want[n["id"]] = sum(y * v for y, v in w) / tot if tot else height / 2
        col.sort(key=lambda n: (n["stub"], round(want[n["id"]], 6), order[n["id"]]))
        y = 0.0
        for n in col:
            n["y"] = max(want[n["id"]] - n["h"] / 2, y)
            y = n["y"] + n["h"] + gap
        over = y - gap - height
        if over > 0:
            y = height
            for n in reversed(col):
                n["y"] = min(n["y"], y - n["h"])
                y = n["y"] - gap

    for f in flows:
        f["h"] = f["value"] * scale
    for n in nodes:
        y = n["y"]
        for f in sorted((f for f in flows if f["src"] == n["id"]), key=lambda f: (by[f["dst"]]["y"], order[f["dst"]])):
            f["y0"] = y
            y += f["h"]
        y = n["y"]
        for f in sorted((f for f in flows if f["dst"] == n["id"]), key=lambda f: (by[f["src"]]["y"], order[f["src"]])):
            f["y1"] = y
            y += f["h"]
    return nodes, flows


def _band(ax, x0, ya, x1, yb, h, **kw):
    xm = (x0 + x1) / 2
    v = [(x0, ya), (xm, ya), (xm, yb), (x1, yb), (x1, yb + h), (xm, yb + h), (xm, ya + h), (x0, ya + h), (x0, ya)]
    c = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.CLOSEPOLY]
    ax.add_patch(mpatches.PathPatch(Path(v, c), **kw))


def sankey(nodes, flows, *, fmt="money", out, w_cm=25, h_cm=9):
    require(flows)
    f_ = fmt_of(fmt)
    size, bw, pad = 7, 0.2, 0.12
    max_lab = w_cm * 0.2

    def label_lines(n):
        v = f_(n["value"])
        lines = fit_lines(n["label"], max_lab, size, max_lines=2)
        lines[-1] = f"{lines[-1]}  {v}"
        return lines

    # label text needs node values, so run a first layout to get them
    n0, _ = sankey_layout(nodes, flows, height=h_cm - 0.5)
    labs = {n["id"]: label_lines(n) for n in n0}
    gap = 0.3 + 0.27 * (max(len(v) for v in labs.values()) - 1)
    height = h_cm - 0.5
    nl, fl = sankey_layout(nodes, flows, height=height, gap=gap)
    cols = sorted({n["col"] for n in nl})
    labs = {n["id"]: label_lines(n) for n in nl}

    def lw(n):
        return max(text_w(s, size) for s in labs[n["id"]])
    left = max(lw(n) for n in nl if n["col"] == cols[0]) + pad + 0.35
    right = max(lw(n) for n in nl if n["col"] == cols[-1]) + pad + 0.35
    x_first, x_last = left, w_cm - right - bw
    xs = {c: x_first + (x_last - x_first) * i / max(len(cols) - 1, 1) for i, c in enumerate(cols)}

    fig, ax = figure(w_cm, h_cm)
    ax.set_position([0, 0, 1, 1])
    ax.set_xlim(0, w_cm)
    ax.set_ylim(h_cm - 0.25, -0.25)
    ax.axis("off")
    by = {n["id"]: n for n in nl}
    colour = {"in": (P["teal"], 0.5), "profit": (P["navy"], 0.6), "cost": (P["pale"], 0.65)}
    for f in sorted(fl, key=lambda f: -f["value"]):
        x0, x1 = xs[by[f["src"]]["col"]] + bw, xs[by[f["dst"]]["col"]]
        red = f.get("flag")
        if f["kind"] == "other":
            kw = dict(facecolor="white", edgecolor=P["pale"], hatch="////", linewidth=0.5)
        else:
            c, a = colour.get(f["kind"], colour["cost"])
            kw = dict(facecolor=c, alpha=a, edgecolor=P["red"] if red else "none", linewidth=0.8 if red else 0)
        _band(ax, x0, f["y0"], x1, f["y1"], f["h"], **kw)
    for n in nl:
        x = xs[n["col"]]
        ax.add_patch(mpatches.Rectangle((x, n["y"]), bw, max(n["h"], 0.04),
                                        facecolor=P["pale"] if n["stub"] else P["slate"], edgecolor="none"))
        cy = n["y"] + n["h"] / 2
        txt = "\n".join(labs[n["id"]])
        if n["col"] == cols[0]:
            ax.text(x - pad, cy, txt, ha="right", va="center", fontsize=size, color=P["ink"], linespacing=1.15)
        else:
            ax.text(x + bw + pad, cy, txt, ha="left", va="center", fontsize=size, color=P["ink"], linespacing=1.15,
                    bbox=None if n["col"] == cols[-1] else dict(boxstyle="square,pad=0.15", facecolor="white",
                                                                edgecolor="none", alpha=0.85))
    return finish(fig, out, flows, w_cm, h_cm, pad=0.0)


# ---------------------------------------------------------------- Org chart
def org_layout(people, per_row=6):
    """Rows of boxes: root (first person in group "ceo") on row 0, each group below in order of first appearance,
    balanced over up to per_row boxes a row. Edges only where reports_to names a person on the chart."""
    people = [dict(p) for p in people]
    require(people)
    root = next((p for p in people if str(p.get("group", "")).lower() == "ceo"), people[0])
    groups = []
    for p in people:
        if p is not root and p.get("group") not in groups:
            groups.append(p.get("group"))
    rows = [[root]]
    labels = []
    for g in groups:
        members = [p for p in people if p is not root and p.get("group") == g]
        nrows = math.ceil(len(members) / per_row)
        size = math.ceil(len(members) / nrows)
        labels.append({"text": g, "row": len(rows)})
        for i in range(0, len(members), size):
            rows.append(members[i:i + size])
    ncols = max(len(r) for r in rows)
    boxes = []
    for ri, r in enumerate(rows):
        for ci, p in enumerate(r):
            col = (ncols - 1) / 2 if ri == 0 else float(ci)
            boxes.append({"id": p["id"], "name": p.get("name", ""), "title": p.get("title", ""), "start": p.get("start"),
                          "group": p.get("group"), "row": ri, "col": col, "flag": bool(p.get("flag"))})
    known = {b["id"] for b in boxes}
    edges = [{"from": p["reports_to"], "to": p["id"]} for p in people
             if p.get("reports_to") and p["reports_to"] in known and p["reports_to"] != p["id"]]
    return {"boxes": boxes, "edges": edges, "labels": labels, "ncols": ncols, "nrows": len(rows)}


def _since(s):
    s = "" if s is None else str(s).strip()
    return f"since {s}" if s.isdigit() else s


def org_chart(people, *, out, w_cm=25, h_cm=9):
    lay = org_layout(people)
    boxes = {b["id"]: b for b in lay["boxes"]}
    ncols, nrows = lay["ncols"], lay["nrows"]
    label_rows = {g["row"]: g["text"] for g in lay["labels"]}
    target_rows = {boxes[e["to"]]["row"] for e in lay["edges"]}
    lab_h, bus_h, base_gap, mx, my, gx = 0.42, 0.4, 0.18, 0.35, 0.12, 0.2

    fixed = my * 2 + sum((0 if r == 0 else base_gap) + (lab_h if r in label_rows else 0) + (bus_h if r in target_rows else 0)
                         for r in range(nrows))
    box_h = min(1.75, (h_cm - fixed) / nrows)
    box_w = (w_cm - mx - 0.15 - gx * (ncols - 1)) / ncols
    ytop, y = {}, my
    for r in range(nrows):
        y += (0 if r == 0 else base_gap) + (lab_h if r in label_rows else 0) + (bus_h if r in target_rows else 0)
        ytop[r] = y
        y += box_h

    def bx(b):
        return mx + b["col"] * (box_w + gx)

    fig, ax = figure(w_cm, h_cm)
    ax.set_position([0, 0, 1, 1])
    ax.set_xlim(0, w_cm)
    ax.set_ylim(h_cm, 0)
    ax.axis("off")
    ln = dict(color=P["slate"], linewidth=0.7, solid_capstyle="butt")

    def seg(xa, ya, xb, yb):
        ax.plot([xa, xb], [ya, yb], **ln)

    parents = {}
    for e in lay["edges"]:
        parents.setdefault(e["from"], []).append(boxes[e["to"]])
    for pid, kids in parents.items():
        p = boxes[pid]
        px, pb = bx(p) + box_w / 2, ytop[p["row"]] + box_h
        krows = sorted({k["row"] for k in kids})
        xt = mx - 0.17
        buses = {r: ytop[r] - bus_h / 2 for r in krows}
        if len(krows) == 1:
            xs_ = [bx(k) + box_w / 2 for k in kids] + [px]
            seg(px, pb, px, buses[krows[0]])
            seg(min(xs_), buses[krows[0]], max(xs_), buses[krows[0]])
        else:
            seg(px, pb, px, buses[krows[0]])
            seg(xt, buses[krows[0]], max([px] + [bx(k) + box_w / 2 for k in kids if k["row"] == krows[0]]), buses[krows[0]])
            seg(xt, buses[krows[0]], xt, buses[krows[-1]])
            for r in krows[1:]:
                seg(xt, buses[r], max(bx(k) + box_w / 2 for k in kids if k["row"] == r), buses[r])
        for k in kids:
            seg(bx(k) + box_w / 2, buses[k["row"]], bx(k) + box_w / 2, ytop[k["row"]])
    for r, t in label_rows.items():
        ax.text(mx, ytop[r] - (bus_h if r in target_rows else 0) - lab_h / 2 - 0.02, t, ha="left", va="center",
                fontsize=7, color=P["muted"], fontweight="bold")
    tier = _pick_tier(lay["boxes"], box_w, box_h)
    for b in lay["boxes"]:
        x, yt = bx(b), ytop[b["row"]]
        root = b["row"] == 0
        ax.add_patch(mpatches.Rectangle((x, yt), box_w, box_h, facecolor=P["navy"] if root else P["fill"],
                                        edgecolor=P["red"] if b["flag"] else (P["navy"] if root else P["pale"]),
                                        linewidth=1.0 if b["flag"] else 0.5))
        _box_text(ax, b, x, yt, box_w, box_h, root, tier)
    return finish(fig, out, people, w_cm, h_cm, pad=0.0)


TIERS = [(7.5, 6.5), (7, 6), (6.5, 5.7), (6, 5.3), (5.5, 5), (5, 4.5)]


def _box_parts(b, ns, ts, inner):
    start = _since(b["start"])
    name = fit_lines(b["name"], inner, ns, 1, "bold")
    title = fit_lines(b["title"], inner, ts, 2)
    n_lines = len(title) + (1 if start else 0)
    return start, name, title, (ns + ts * n_lines) * 1.22 / 72 * 2.54


def _pick_tier(boxes, w, h, pad=0.12):
    """One font tier for the whole chart: the largest where no text is cut and every box fits."""
    for ns, ts in TIERS:
        ok = True
        for b in boxes:
            _, name, title, lh = _box_parts(b, ns, ts, w - 2 * pad)
            if any(x.endswith("\u2026") for x in name + title) or lh > h - 0.1:
                ok = False
                break
        if ok:
            return ns, ts
    return TIERS[-1]


def _box_text(ax, b, x, yt, w, h, root, tier, pad=0.12):
    ns, ts = tier
    start, name, title, lines_h = _box_parts(b, ns, ts, w - 2 * pad)
    ty = yt + h / 2 - lines_h / 2
    fg, sub = (P["white"], P["faint"]) if root else (P["ink"], P["muted"])
    ax.text(x + w / 2, ty, name[0] if name else "", ha="center", va="top", fontsize=ns, fontweight="bold", color=fg)
    ty += ns * 1.22 / 72 * 2.54
    for t in title:
        ax.text(x + w / 2, ty, t, ha="center", va="top", fontsize=ts, color=sub)
        ty += ts * 1.22 / 72 * 2.54
    if start:
        ax.text(x + w / 2, ty, start, ha="center", va="top", fontsize=ts, color=sub)


# ---------------------------------------------------------------- Logo wall
def _load_logo(path):
    """Greyscale PIL image composited on white and trimmed of white margins, or None if missing or unreadable."""
    if not path:
        return None
    try:
        from PIL import Image
        im = Image.open(path)
        im.load()
        rgba = im.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        g = Image.alpha_composite(bg, rgba).convert("L")
        box = g.point(lambda v: 255 if v < 245 else 0).getbbox()
        if box:
            g = g.crop(box)
        return g if g.size[0] > 1 and g.size[1] > 1 else None
    except Exception:
        return None


def logo_layout(logos, ncols=6):
    require(logos)
    sectors = []
    for l in logos:
        if l.get("sector") not in sectors:
            sectors.append(l.get("sector"))
    cells, secs, row = [], [], 0
    for s in sectors:
        members = [l for l in logos if l.get("sector") == s]
        for i, l in enumerate(members):
            img = _load_logo(l.get("path"))
            cells.append({"name": l["name"], "sector": s, "kind": "image" if img else "text", "img": img,
                          "row": row + i // ncols, "col": i % ncols, "flag": bool(l.get("flag"))})
        nr = math.ceil(len(members) / ncols)
        secs.append({"name": s, "row": row, "rows": nr})
        row += nr
    return {"cells": cells, "sectors": secs, "nrows": row, "ncols": ncols}


def logo_wall(logos, *, ncols=6, out, w_cm=25, h_cm=9):
    lay = logo_layout(logos, ncols)
    nrows, nsec = lay["nrows"], len(lay["sectors"])
    size = 7
    lw_ = min(max(w_cm * 0.13, 1.8), 3.2)
    sec_gap, my = 0.22, 0.1
    row_h = min((h_cm - 2 * my - sec_gap * (nsec - 1)) / nrows, 2.0)
    cw = (w_cm - lw_ - 0.1) / ncols
    fig, ax = figure(w_cm, h_cm)
    ax.set_position([0, 0, 1, 1])
    ax.set_xlim(0, w_cm)
    ax.set_ylim(h_cm, 0)
    ax.axis("off")
    sy = {}
    for i, s in enumerate(lay["sectors"]):
        sy[s["name"]] = my + s["row"] * row_h + i * sec_gap
    for i, s in enumerate(lay["sectors"]):
        y0 = sy[s["name"]]
        if i:
            ax.plot([0.05, w_cm - 0.05], [y0 - sec_gap / 2] * 2, color=P["rule"], linewidth=0.6)
        lines = fit_lines(s["name"], lw_ - 0.3, size, 3, "bold")
        ax.text(0.25, y0 + 0.1, "\n".join(lines), ha="left", va="top", fontsize=size, color=P["muted"], fontweight="bold",
                linespacing=1.2)
    cap_h = 0.32
    for c in lay["cells"]:
        x0 = lw_ + c["col"] * cw
        y0 = sy[c["sector"]] + (c["row"] - next(s["row"] for s in lay["sectors"] if s["name"] == c["sector"])) * row_h
        name_col = P["red"] if c["flag"] else P["muted"]
        logo_h = row_h - cap_h - 0.2
        if c["kind"] == "image":
            iw, ih = c["img"].size
            bw_, bh_ = cw * 0.76, logo_h
            k = min(bw_ / iw, bh_ / ih)
            w, h = iw * k, ih * k
            cx = x0 + cw / 2
            ax.imshow(c["img"], cmap="gray", vmin=0, vmax=255, extent=(cx - w / 2, cx + w / 2, y0 + 0.1 + (logo_h + h) / 2, y0 + 0.1 + (logo_h - h) / 2),
                      interpolation="lanczos", aspect="auto", zorder=2)
            cap = fit_lines(c["name"], cw - 0.2, 6)
            ax.text(x0 + cw / 2, y0 + 0.1 + logo_h + 0.06, cap[0] if cap else "", ha="center", va="top", fontsize=6, color=name_col)
        else:
            lines = fit_lines(c["name"], cw - 0.3, size, 2, "bold")
            ax.text(x0 + cw / 2, y0 + 0.1 + logo_h / 2, "\n".join(lines), ha="center", va="center", fontsize=size,
                    color=P["red"] if c["flag"] else P["muted"], fontweight="bold", linespacing=1.15)
    ax.set_xlim(0, w_cm)
    ax.set_ylim(h_cm, 0)
    return finish(fig, out, logos, w_cm, h_cm, pad=0.0)
