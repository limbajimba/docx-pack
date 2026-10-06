"""Chart library for visual fact packs: matplotlib, house palette, every chart returns its provenance.

Each chart function takes tidy rows (dicts that carry "tag" and "conf"), writes a PNG with no title
(the document caption carries the title) and returns a Chart with the source tags and lowest confidence.
"""
from .style import Chart, EmptyData, P, SERIES, fmt_of, provenance  # noqa: F401


def registry():
    """name -> chart function, for the assembler."""
    import importlib
    out = {}
    for name in ("series", "events", "diagrams"):
        try:
            mod = importlib.import_module(f"{__name__}.{name}")
        except ModuleNotFoundError as e:
            if e.name != f"{__name__}.{name}":
                raise
            continue
        out.update({n: getattr(mod, n) for n in getattr(mod, "CHARTS", [])})
    return out
