"""House look and provenance for every chart: palette, font, number formats, save-and-return."""
import re
from dataclasses import dataclass, field

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

P = {"ink": "#2E3232", "muted": "#646A7A", "navy": "#132246", "teal": "#0B4E6F", "slate": "#44596D",
     "red": "#C0392B", "rule": "#E9EBEB", "fill": "#F2F2F2", "white": "#FFFFFF", "pale": "#A9B4C2", "faint": "#D5DBE2"}
SERIES = [P["navy"], P["teal"], P["slate"], "#7F93A8", "#B7C4D1"]
CONF_ORDER = ["High", "Medium", "Low", "Not found"]
CM = 1 / 2.54


class EmptyData(ValueError):
    """No rows to draw: the assembler drops the panel instead of padding the page."""


@dataclass
class Chart:
    png: str
    sources: list = field(default_factory=list)
    confidence: str = ""
    w_cm: float = 12.4
    h_cm: float = 5.6


_FONT = None


def setup():
    global _FONT
    if _FONT:
        return _FONT
    names = {f.name for f in font_manager.fontManager.ttflist}
    _FONT = next((n for n in ("Gill Sans", "Gill Sans MT", "Helvetica Neue", "Arial") if n in names), "DejaVu Sans")
    plt.rcParams.update({
        "font.family": _FONT, "font.size": 8, "text.color": P["ink"], "axes.labelcolor": P["muted"],
        "axes.edgecolor": P["rule"], "xtick.color": P["muted"], "ytick.color": P["muted"],
        "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "axes.titlesize": 8.5, "legend.frameon": False,
        "svg.fonttype": "none", "hatch.color": P["pale"], "hatch.linewidth": 0.6,
    })
    return _FONT


def figure(w_cm, h_cm, nrows=1, ncols=1, **kw):
    setup()
    return plt.subplots(nrows, ncols, figsize=(w_cm * CM, h_cm * CM), dpi=200, **kw)


def tidy(ax, grid="y"):
    """Tufte-light axes: no top/right spines, hairline grid on one axis, no tick marks."""
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_visible(grid != "y")
    ax.spines["bottom"].set_color(P["rule"])
    ax.spines["left"].set_color(P["rule"])
    ax.tick_params(length=0)
    if grid in ("x", "y", "both"):
        ax.grid(True, axis=grid, color=P["rule"], linewidth=0.6)
    ax.set_axisbelow(True)


def require(rows):
    if not rows:
        raise EmptyData("no rows")
    return rows


def _tag_key(t):
    m = re.fullmatch(r"([A-Z])(\d+)", t)
    return (0, m.group(1), int(m.group(2)), "") if m else (1, "", 0, t)


def provenance(rows):
    """Sorted unique source tags and the lowest confidence grade across rows."""
    tags, confs = set(), []
    for r in rows or []:
        t = r.get("tag")
        if isinstance(t, (list, tuple, set)):
            tags.update(x for x in t if x)
        elif t:
            tags.add(t)
        if r.get("conf") in CONF_ORDER:
            confs.append(r["conf"])
    conf = max(confs, key=CONF_ORDER.index) if confs else ""
    return sorted(tags, key=_tag_key), conf


def finish(fig, out, rows, w_cm, h_cm, pad=0.3):
    fig.tight_layout(pad=pad)
    fig.savefig(out, dpi=200, facecolor="white")
    plt.close(fig)
    sources, conf = provenance(rows)
    return Chart(str(out), sources, conf, w_cm, h_cm)


def _sign(v):
    return "-" if v < 0 else ""


def money(v):
    return f"{_sign(v)}${abs(v):,.0f}m"


def money1(v):
    return f"{_sign(v)}${abs(v):,.1f}m"


def money_bn(v):
    return f"{_sign(v)}${abs(v) / 1000:,.1f}bn"


def money_k(v):
    return f"{_sign(v)}${abs(v):,.0f}"


def pct(v):
    return f"{v:.0f}%"


def pct1(v):
    return f"{v:.1f}%"


def num(v):
    return f"{v:,.0f}"


def num1(v):
    return f"{v:,.1f}"


FORMATS = {"money": money, "money1": money1, "money_bn": money_bn, "money_k": money_k, "pct": pct, "pct1": pct1, "num": num, "num1": num1}


def fmt_of(f):
    if callable(f):
        return f
    if f in FORMATS:
        return FORMATS[f]
    raise KeyError(f"unknown format {f!r}; known: {sorted(FORMATS)}")
