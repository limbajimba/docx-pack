#!/usr/bin/env python3
"""Codify a Word template or exemplar document into a style spec.

Reads any .docx or .dotx and writes:
  <out>/style-spec.json   machine-readable tokens (page, fonts, sizes, colours, header/footer, tables)
  <out>/STYLE.md          the same, readable, plus a block outline of the first N body blocks
  <out>/media/            images used in headers/footers (logos); --all-media adds body images

The spec is a starting point. Colour ROLES (ink, muted, accent...) are inferred by frequency
and must be checked by eye against the rendered pages before the spec is used to build.

Usage:
  python3 codify_template.py template.docx --out house/ [--outline 80] [--all-media]
"""
import argparse, collections, json, os, re, shutil, sys, zipfile
import xml.etree.ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC = "http://purl.org/dc/elements/1.1/"
NS = {"w": W, "r": R, "a": A, "wp": WP, "pic": PIC, "cp": CP, "dc": DC}


def q(tag):
    p, t = tag.split(":")
    return f"{{{NS[p]}}}{t}"


def attr(el, name, default=None):
    return el.get(q(name), default) if el is not None else default


def hp_to_pt(v):
    try:
        return round(int(v) / 2, 1)
    except (TypeError, ValueError):
        return None


def dxa_to_cm(v):
    try:
        return round(int(v) / 567.0, 2)
    except (TypeError, ValueError):
        return None


class Pkg:
    def __init__(self, path):
        self.z = zipfile.ZipFile(path)
        self.names = set(self.z.namelist())

    def xml(self, name):
        if name not in self.names:
            return None
        return ET.fromstring(self.z.read(name))

    def rels(self, part):
        d, f = os.path.split(part)
        rel = f"{d}/_rels/{f}.rels"
        root = self.xml(rel)
        out = {}
        if root is None:
            return out
        for r in root:
            out[r.get("Id")] = (r.get("Type", "").rsplit("/", 1)[-1], r.get("Target"), r.get("TargetMode"))
        return out


def run_props(rpr):
    if rpr is None:
        return {}
    d = {}
    f = rpr.find("w:rFonts", NS)
    if f is not None:
        d["font"] = attr(f, "w:ascii") or attr(f, "w:hAnsi")
    sz = rpr.find("w:sz", NS)
    if sz is not None:
        d["pt"] = hp_to_pt(attr(sz, "w:val"))
    c = rpr.find("w:color", NS)
    if c is not None:
        d["color"] = attr(c, "w:val")
    if rpr.find("w:b", NS) is not None and attr(rpr.find("w:b", NS), "w:val", "1") not in ("0", "false"):
        d["bold"] = True
    if rpr.find("w:i", NS) is not None and attr(rpr.find("w:i", NS), "w:val", "1") not in ("0", "false"):
        d["italic"] = True
    if rpr.find("w:caps", NS) is not None:
        d["caps"] = True
    if rpr.find("w:u", NS) is not None:
        d["underline"] = attr(rpr.find("w:u", NS), "w:val")
    return d


def para_props(ppr):
    if ppr is None:
        return {}
    d = {}
    st = ppr.find("w:pStyle", NS)
    if st is not None:
        d["style"] = attr(st, "w:val")
    sp = ppr.find("w:spacing", NS)
    if sp is not None:
        for k in ("before", "after", "line"):
            v = attr(sp, f"w:{k}")
            if v is not None:
                d[f"space_{k}"] = int(v)
    jc = ppr.find("w:jc", NS)
    if jc is not None:
        d["align"] = attr(jc, "w:val")
    bdr = ppr.find("w:pBdr", NS)
    if bdr is not None:
        d["borders"] = {b.tag.split("}")[1]: {"color": attr(b, "w:color"), "sz": attr(b, "w:sz"), "space": attr(b, "w:space")} for b in bdr}
    shd = ppr.find("w:shd", NS)
    if shd is not None:
        d["fill"] = attr(shd, "w:fill")
    ind = ppr.find("w:ind", NS)
    if ind is not None:
        d["indent"] = {k: attr(ind, f"w:{k}") for k in ("left", "hanging", "firstLine") if attr(ind, f"w:{k}")}
    num = ppr.find("w:numPr", NS)
    if num is not None:
        d["numbered"] = True
    if ppr.find("w:keepNext", NS) is not None:
        d["keep_next"] = True
    return d


def para_text(p):
    return "".join(t.text or "" for t in p.iter(q("w:t")))


def para_summary(p):
    pp = para_props(p.find("w:pPr", NS))
    runs = [run_props(r.find("w:rPr", NS)) for r in p.findall("w:r", NS)]
    runs = [r for r in runs if r]
    first = runs[0] if runs else {}
    imgs = len(list(p.iter(q("pic:pic"))))
    return pp, first, para_text(p), imgs


def tbl_summary(tbl):
    rows = tbl.findall("w:tr", NS)
    ncols = max((len(r.findall("w:tc", NS)) for r in rows), default=0)
    grid = [attr(g, "w:w") for g in tbl.findall("w:tblGrid/w:gridCol", NS)]
    fills = collections.Counter()
    borders = {}
    tblpr = tbl.find("w:tblPr", NS)
    if tblpr is not None:
        b = tblpr.find("w:tblBorders", NS)
        if b is not None:
            borders = {c.tag.split("}")[1]: {"val": attr(c, "w:val"), "color": attr(c, "w:color"), "sz": attr(c, "w:sz")} for c in b}
    row_fills = []
    for r in rows[:6]:
        rf = []
        for tc in r.findall("w:tc", NS):
            shd = tc.find("w:tcPr/w:shd", NS)
            f = attr(shd, "w:fill") if shd is not None else None
            rf.append(f)
            if f:
                fills[f] += 1
        row_fills.append(rf)
    first_cell_text = ""
    if rows:
        tcs = rows[0].findall("w:tc", NS)
        first_cell_text = " | ".join(para_text(p) for tc in tcs for p in tc.findall("w:p", NS))[:160]
    cell_margins = None
    if rows:
        tc0 = rows[0].find("w:tc", NS)
        if tc0 is not None:
            m = tc0.find("w:tcPr/w:tcMar", NS)
            if m is not None:
                cell_margins = {c.tag.split("}")[1]: attr(c, "w:w") for c in m}
    return {"rows": len(rows), "cols": ncols, "grid_dxa": grid, "borders": borders, "fills": dict(fills),
            "row_fills": row_fills, "first_row": first_cell_text, "cell_margins": cell_margins}


def hdr_ftr(pkg, part):
    root = pkg.xml(part)
    if root is None:
        return None
    rels = pkg.rels(part)
    out = {"part": part, "paragraphs": [], "images": []}
    for p in root.iter(q("w:p")):
        pp, first, text, _ = para_summary(p)
        fields = [it.text.strip() for it in p.iter(q("w:instrText")) if it.text]
        tabs = [attr(t, "w:val") + "@" + str(attr(t, "w:pos")) for t in p.findall("w:pPr/w:tabs/w:tab", NS)]
        out["paragraphs"].append({"text": text, "fields": fields, "run": first, "para": pp, "tabs": tabs})
    for blip in root.iter(q("a:blip")):
        rid = blip.get(q("r:embed"))
        ext = None
        for anc in root.iter(q("wp:extent")):
            ext = {"cx_emu": int(anc.get("cx")), "cy_emu": int(anc.get("cy"))}
            break
        tgt = rels.get(rid, (None, None, None))[1]
        out["images"].append({"target": tgt, "extent": ext,
                              "cm": {"w": round(ext["cx_emu"] / 360000, 2), "h": round(ext["cy_emu"] / 360000, 2)} if ext else None})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docx")
    ap.add_argument("--out", required=True)
    ap.add_argument("--outline", type=int, default=80, help="body blocks to outline in STYLE.md")
    ap.add_argument("--all-media", action="store_true", help="also copy body images")
    ap.add_argument("--name", default=None, help="spec name (default: file stem)")
    a = ap.parse_args()

    pkg = Pkg(a.docx)
    os.makedirs(os.path.join(a.out, "media"), exist_ok=True)
    spec = {"name": a.name or re.sub(r"\W+", "-", os.path.splitext(os.path.basename(a.docx))[0]).lower(),
            "source": os.path.basename(a.docx), "roles_checked_by_eye": False}

    # ---- core props
    core = pkg.xml("docProps/core.xml")
    if core is not None:
        spec["metadata"] = {k: (core.findtext(k, namespaces=NS) or "") for k in ("dc:title", "dc:creator", "cp:lastModifiedBy")}
    app = pkg.xml("docProps/app.xml")
    spec["metadata"] = spec.get("metadata", {})
    spec["metadata"]["app_xml_empty"] = app is None or len(list(app)) == 0

    # ---- styles
    styles = pkg.xml("word/styles.xml")
    st_out = {}
    defaults = {}
    if styles is not None:
        rd = styles.find("w:docDefaults/w:rPrDefault/w:rPr", NS)
        defaults = run_props(rd)
        pd = styles.find("w:docDefaults/w:pPrDefault/w:pPr", NS)
        defaults.update({f"para_{k}": v for k, v in para_props(pd).items()})
        for s in styles.findall("w:style", NS):
            sid = attr(s, "w:styleId")
            d = {"type": attr(s, "w:type"), "name": s.find("w:name", NS).get(q("w:val")) if s.find("w:name", NS) is not None else sid}
            bo = s.find("w:basedOn", NS)
            if bo is not None:
                d["based_on"] = attr(bo, "w:val")
            d.update(run_props(s.find("w:rPr", NS)))
            d.update(para_props(s.find("w:pPr", NS)))
            st_out[sid] = d
    spec["defaults"] = defaults
    spec["styles"] = st_out

    # ---- document body
    doc = pkg.xml("word/document.xml")
    body = doc.find("w:body", NS)
    sect = body.find("w:sectPr", NS)
    if sect is None:
        for s in doc.iter(q("w:sectPr")):
            sect = s
    page = {}
    if sect is not None:
        pg = sect.find("w:pgSz", NS)
        mg = sect.find("w:pgMar", NS)
        if pg is not None:
            page["width_dxa"], page["height_dxa"] = int(attr(pg, "w:w")), int(attr(pg, "w:h"))
            page["orientation"] = attr(pg, "w:orient", "portrait")
            page["size"] = {(11906, 16838): "A4", (12240, 15840): "Letter"}.get((page["width_dxa"], page["height_dxa"]), "custom")
        if mg is not None:
            page["margins_dxa"] = {k: int(attr(mg, f"w:{k}")) for k in ("top", "right", "bottom", "left", "header", "footer", "gutter") if attr(mg, f"w:{k}") is not None}
            page["margins_cm"] = {k: dxa_to_cm(v) for k, v in page["margins_dxa"].items()}
        if page.get("width_dxa") and page.get("margins_dxa"):
            page["text_width_dxa"] = page["width_dxa"] - page["margins_dxa"].get("left", 0) - page["margins_dxa"].get("right", 0)
        page["header_parts"] = [attr(h, "w:type") for h in sect.findall("w:headerReference", NS)]
        page["footer_parts"] = [attr(f, "w:type") for f in sect.findall("w:footerReference", NS)]
        if sect.find("w:titlePg", NS) is not None:
            page["different_first_page"] = True
    spec["page"] = page

    fonts, sizes, colors, fills, pstyles, bcolors = (collections.Counter() for _ in range(6))
    n_tbl = n_p = n_img = 0
    outline = []
    blocks = [el for el in body if el.tag in (q("w:p"), q("w:tbl"))]
    for el in blocks:
        if el.tag == q("w:tbl"):
            n_tbl += 1
            ts = tbl_summary(el)
            if len(outline) < a.outline:
                outline.append(("TABLE", ts))
        else:
            n_p += 1
            pp, first, text, imgs = para_summary(el)
            n_img += imgs
            if len(outline) < a.outline:
                outline.append(("P", {"text": text[:110], "run": first, "para": pp, "images": imgs}))
    for rpr in body.iter(q("w:rPr")):
        rp = run_props(rpr)
        if rp.get("font"):
            fonts[rp["font"]] += 1
        if rp.get("pt"):
            sizes[rp["pt"]] += 1
        if rp.get("color"):
            colors[rp["color"]] += 1
    for shd in body.iter(q("w:shd")):
        f = attr(shd, "w:fill")
        if f and f.lower() not in ("auto", "ffffff"):
            fills[f] += 1
    for ps in body.iter(q("w:pStyle")):
        pstyles[attr(ps, "w:val")] += 1
    for tag in ("w:top", "w:bottom", "w:left", "w:right", "w:insideH", "w:insideV"):
        for b in body.iter(q(tag)):
            c = attr(b, "w:color")
            if c and c != "auto":
                bcolors[c] += 1
    spec["body_stats"] = {"paragraphs": n_p, "tables": n_tbl, "images": n_img,
                          "fonts": fonts.most_common(6), "sizes_pt": sizes.most_common(12),
                          "text_colors": colors.most_common(12), "fills": fills.most_common(8),
                          "border_colors": bcolors.most_common(6), "paragraph_styles_used": pstyles.most_common(12)}

    # ---- inferred roles (to be checked by eye)
    def is_grey(h):
        try:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        except ValueError:
            return False
        return max(r, g, b) - min(r, g, b) < 24
    text_sorted = [c for c, _ in colors.most_common()]
    greys = [c for c in text_sorted if is_grey(c)]
    accents = [c for c in text_sorted if not is_grey(c) and c.upper() != "FFFFFF"]
    spec["roles_inferred"] = {
        "font_body": defaults.get("font") or (fonts.most_common(1)[0][0] if fonts else None),
        "size_body_pt": defaults.get("pt") or (sizes.most_common(1)[0][0] if sizes else None),
        "ink": greys[0] if greys else (text_sorted[0] if text_sorted else "000000"),
        "muted": greys[1] if len(greys) > 1 else None,
        "accent_candidates": accents[:6],
        "fill_candidates": [f for f, _ in fills.most_common(4)],
        "rule_candidates": [c for c, _ in bcolors.most_common(3)],
    }

    # ---- header / footer
    doc_rels = pkg.rels("word/document.xml")
    hf = {"headers": [], "footers": []}
    for rid, (typ, tgt, _) in doc_rels.items():
        if typ in ("header", "footer"):
            part = "word/" + tgt if not tgt.startswith("/") else tgt.lstrip("/")
            info = hdr_ftr(pkg, part)
            if info:
                hf[typ + "s"].append(info)
                for im in info["images"]:
                    if im["target"]:
                        src = "word/" + im["target"]
                        if src in pkg.names:
                            dst = os.path.join(a.out, "media", os.path.basename(src))
                            with open(dst, "wb") as fh:
                                fh.write(pkg.z.read(src))
                            im["saved_as"] = os.path.relpath(dst, a.out)
    spec["header_footer"] = hf
    if a.all_media:
        for n in pkg.names:
            if n.startswith("word/media/"):
                with open(os.path.join(a.out, "media", os.path.basename(n)), "wb") as fh:
                    fh.write(pkg.z.read(n))

    # ---- numbering
    num = pkg.xml("word/numbering.xml")
    bullets = []
    if num is not None:
        for absn in num.findall("w:abstractNum", NS):
            lv = absn.find("w:lvl", NS)
            if lv is not None:
                fmt = attr(lv.find("w:numFmt", NS), "w:val")
                txt = attr(lv.find("w:lvlText", NS), "w:val")
                ind = lv.find("w:pPr/w:ind", NS)
                bullets.append({"format": fmt, "text": txt, "indent": {k: attr(ind, f"w:{k}") for k in ("left", "hanging")} if ind is not None else None})
    spec["numbering_level0"] = bullets[:6]

    with open(os.path.join(a.out, "style-spec.json"), "w") as fh:
        json.dump(spec, fh, indent=2, ensure_ascii=False)

    # ---- STYLE.md
    L = []
    L.append(f"# Style spec: {spec['name']}\n\nSource: `{spec['source']}`. Roles inferred by frequency; check them against the rendered pages, then set `roles_checked_by_eye: true`.\n")
    L.append("## Page\n")
    for k, v in page.items():
        L.append(f"- {k}: `{v}`")
    L.append("\n## Defaults (docDefaults)\n")
    L.append(f"`{defaults}`")
    L.append("\n## Inferred roles\n")
    for k, v in spec["roles_inferred"].items():
        L.append(f"- {k}: `{v}`")
    L.append("\n## Body statistics\n")
    for k, v in spec["body_stats"].items():
        L.append(f"- {k}: `{v}`")
    L.append("\n## Named styles that carry formatting\n")
    for sid, d in st_out.items():
        keys = {k: v for k, v in d.items() if k not in ("type", "name", "based_on")}
        if keys:
            L.append(f"- **{sid}** ({d['type']}): `{keys}`")
    L.append("\n## Header / footer\n")
    for kind in ("headers", "footers"):
        for h in hf[kind]:
            L.append(f"- {kind[:-1]} `{h['part']}`")
            for p in h["paragraphs"]:
                if p["text"].strip() or p["fields"]:
                    L.append(f"  - text: “{p['text'].strip()}” fields={p['fields']} run={p['run']} tabs={p['tabs']} borders={p['para'].get('borders')}")
            for im in h["images"]:
                L.append(f"  - image: {im.get('saved_as') or im['target']} size_cm={im['cm']}")
    L.append("\n## Bullets\n")
    for b in bullets[:6]:
        L.append(f"- `{b}`")
    L.append(f"\n## Block outline (first {min(a.outline, len(blocks))} of {len(blocks)} body blocks)\n")
    L.append("Read this top to bottom to see how the exemplar composes its components (title band, verdict bar, tiles, headings, tables).\n")
    for i, (kind, d) in enumerate(outline):
        if kind == "TABLE":
            L.append(f"{i:3d}. TABLE rows={d['rows']} cols={d['cols']} grid={d['grid_dxa']} fills={d['fills']} borders={ {k: v['color'] for k, v in d['borders'].items()} if d['borders'] else '-'} margins={d['cell_margins']}")
            L.append(f"      first row: “{d['first_row']}”")
            for rf in d["row_fills"][:4]:
                L.append(f"      row fills: {rf}")
        else:
            flags = []
            if d["para"].get("borders"):
                flags.append("borders=" + ",".join(f"{k}:{v['color']}" for k, v in d["para"]["borders"].items()))
            if d["para"].get("fill"):
                flags.append("fill=" + d["para"]["fill"])
            if d["images"]:
                flags.append(f"images={d['images']}")
            if d["para"].get("numbered"):
                flags.append("bullet")
            if d["para"].get("style"):
                flags.append("style=" + d["para"]["style"])
            sp = {k: v for k, v in d["para"].items() if k.startswith("space_")}
            L.append(f"{i:3d}. P {d['run']} {sp} {' '.join(flags)}")
            if d["text"].strip():
                L.append(f"      “{d['text']}”")
    with open(os.path.join(a.out, "STYLE.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"wrote {a.out}/style-spec.json, {a.out}/STYLE.md, media/ ({len(os.listdir(os.path.join(a.out, 'media')))} files)")


if __name__ == "__main__":
    main()
