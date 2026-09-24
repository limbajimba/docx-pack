#!/usr/bin/env python3
"""Fill any Word template (.docx or .dotx) with content blocks, keeping the template's own styles,
headers, footers, page setup, numbering and theme.

Use this when a client or firm template must stay exactly as designed (letterhead, cover, legal footer).
Use build_docx.js instead when you build a house document from a style spec.

Usage:
  python3 fill_template.py --template Firm.dotx --content content.json --out report.docx [--keep-body]
        [--placeholders '{"{{date}}": "24 September 2026", "{{client}}": "Acme"}']

Content is the same block JSON that build_docx.js reads. Blocks map to the template's named styles:
  h1/h2/h3 -> Heading 1/2/3 · p -> Normal · bullets -> List Bullet · numbered -> List Number
  title_band -> Title + Subtitle · verdict -> Intense Quote (else bold Normal) · basis -> Caption (else small Normal)
  kpis / snapshot / table -> tables in the template's first table style (else Table Grid), header row bold
  finding -> Heading 2 + Normal + italic Counter/Gaps lines · image -> inline picture · pagebreak
Missing styles fall back to Normal with direct formatting, and the fallback is printed so you can fix the template.
"""
import argparse, copy, json, os, re, shutil, sys, tempfile, zipfile
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.shared import Pt, Cm, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*)")
fallbacks = []


def dotx_to_docx(path):
    """python-docx refuses the template content type; rewrite it in a temp copy."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
    with zipfile.ZipFile(path) as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = data.replace(b"wordprocessingml.template.main+xml", b"wordprocessingml.document.main+xml")
            dst.writestr(item, data)
    return tmp


def has_style(doc, name):
    try:
        doc.styles[name]
        return True
    except KeyError:
        return False


def style_or(doc, *names):
    for n in names:
        if has_style(doc, n):
            return n
    fallbacks.append(" / ".join(names))
    return None


def add_runs(par, text, bold=None, italic=None, size=None, color=None):
    for tok in INLINE_RE.split(str(text)):
        if not tok:
            continue
        b, i, t = bold, italic, tok
        if tok.startswith("**"):
            b, t = True, tok[2:-2]
        elif tok.startswith("*"):
            i, t = True, tok[1:-1]
        r = par.add_run(t)
        if b is not None: r.bold = b
        if i is not None: r.italic = i
        if size: r.font.size = Pt(size)
        if color: r.font.color.rgb = RGBColor.from_string(color)


def para(doc, text, style=None, **fmt):
    if style and not has_style(doc, style):
        if style != "Normal":
            fallbacks.append(style)
        style = None
    p = doc.add_paragraph(style=style) if style else doc.add_paragraph()
    add_runs(p, text, **fmt)
    return p


def shade(cell, hex6):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex6)
    tcPr.append(shd)


def make_table(doc, header, rows, widths_cm=None, style=None, header_bold=True, small=False):
    t = doc.add_table(rows=1, cols=len(header))
    if style: t.style = style
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.text = ""
        add_runs(c.paragraphs[0], h, bold=header_bold, size=9 if small else None)
    for r in rows:
        if isinstance(r, dict) and "group" in r:
            row = t.add_row(); m = row.cells[0].merge(row.cells[-1]); m.text = ""
            add_runs(m.paragraphs[0], r["group"], bold=True, size=9 if small else None)
            continue
        cells = t.add_row().cells
        for i, v in enumerate(r):
            o = v if isinstance(v, dict) else {"text": v}
            cells[i].text = ""
            add_runs(cells[i].paragraphs[0], str(o.get("text", "")), bold=o.get("bold"), size=o.get("size") or (9 if small else None), color=o.get("color") if o.get("color") and re.fullmatch(r"[0-9A-Fa-f]{6}", o["color"]) else None)
            if o.get("align") == "right": cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if widths_cm:
        for w, col in zip(widths_cm, t.columns):
            for c in col.cells: c.width = Cm(w)
    return t


def replace_placeholders(doc, mapping):
    def fix(par):
        full = "".join(r.text for r in par.runs)
        if not any(k in full for k in mapping):
            return
        for k, v in mapping.items():
            full = full.replace(k, v)
        for r in par.runs[1:]:
            r.text = ""
        if par.runs:
            par.runs[0].text = full
    parts = [doc] + [s.header for s in doc.sections] + [s.footer for s in doc.sections] + [s.first_page_header for s in doc.sections] + [s.first_page_footer for s in doc.sections]
    for part in parts:
        for p in part.paragraphs:
            fix(p)
        for t in part.tables:
            for row in t.rows:
                for c in row.cells:
                    for p in c.paragraphs:
                        fix(p)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", required=True); ap.add_argument("--content", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--keep-body", action="store_true", help="append after the template's existing body instead of replacing it")
    ap.add_argument("--placeholders", help="JSON map of literal tokens to replace anywhere, e.g. {\"{{date}}\": \"...\"}")
    a = ap.parse_args()
    src = dotx_to_docx(a.template) if a.template.lower().endswith(".dotx") else a.template
    doc = Document(src)
    content = json.load(open(a.content)); meta = content.get("meta", {})
    cdir = os.path.dirname(os.path.abspath(a.content))

    if not a.keep_body:
        body = doc.element.body
        for el in list(body):
            if el.tag != qn("w:sectPr"):
                body.remove(el)

    tstyle = style_or(doc, *[s.name for s in doc.styles if s.type == 3 and s.name not in ("Normal Table",)][:1], "Table Grid")
    cap = "Caption" if has_style(doc, "Caption") else None
    for b in content["blocks"]:
        t = b["type"]
        if t == "title_band":
            para(doc, b.get("title") or meta.get("title", ""), style_or(doc, "Title"))
            sub = "  ·  ".join(x for x in [b.get("kicker") or meta.get("kicker"), b.get("date") or meta.get("date")] + list(b.get("right_lines") or meta.get("right_lines") or []) if x)
            if sub: para(doc, sub, style_or(doc, "Subtitle"))
        elif t == "verdict":
            s = style_or(doc, "Intense Quote", "Quote")
            para(doc, b["text"], s, bold=None if s else True, size=None if s else 12)
        elif t == "basis":
            para(doc, b["text"], cap, size=None if cap else 8, italic=None if cap else True)
        elif t == "kpis":
            make_table(doc, [i["label"] for i in b["items"]], [[i["value"] for i in b["items"]], [i.get("note", "") for i in b["items"]]], style=tstyle)
            doc.add_paragraph()
        elif t == "image":
            f = os.path.join(cdir, b["path"]) if not os.path.isabs(b["path"]) else b["path"]
            doc.add_picture(f, width=Cm(b.get("width_cm", 15)))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            if b.get("caption"): para(doc, b["caption"], cap, size=None if cap else 8)
        elif t in ("h1", "h2", "h3"):
            lvl = int(t[1]); s = style_or(doc, f"Heading {lvl}")
            p = para(doc, b["text"] + (("\t" + b["meta"]) if b.get("meta") else ""), s, bold=None if s else True)
        elif t == "p":
            para(doc, b["text"], "Normal", size=b.get("size") if isinstance(b.get("size"), (int, float)) else None)
        elif t == "bullets":
            s = style_or(doc, "List Bullet")
            for it in b["items"]: para(doc, ("• " if not s else "") + it, s)
        elif t == "numbered":
            s = style_or(doc, "List Number")
            for n, it in enumerate(b["items"], 1): para(doc, (f"{n}. " if not s else "") + it, s)
        elif t == "snapshot":
            tb = make_table(doc, ["Item", "Detail"], [[{"text": l, "bold": True}, v] for l, v in b["rows"]], widths_cm=[4, 12], style=tstyle)
            doc.add_paragraph()
        elif t == "table":
            make_table(doc, [c["header"] for c in b["columns"]], b["rows"], widths_cm=[c["width"] / 567 for c in b["columns"]], style=tstyle, small=b.get("size") == "table_small")
            if b.get("note"): para(doc, b["note"], cap, size=None if cap else 8)
            else: doc.add_paragraph()
        elif t == "finding":
            s = style_or(doc, "Heading 2")
            para(doc, (f"{b['code']}  " if b.get("code") else "") + b["title"] + (("\t" + b["meta"]) if b.get("meta") else ""), s, bold=None if s else True)
            for x in (b["body"] if isinstance(b["body"], list) else [b["body"]]): para(doc, x, "Normal")
            if b.get("counter"): para(doc, "**Counter:** *" + b["counter"] + "*", "Normal")
            if b.get("gaps"): para(doc, "**Gaps:** " + b["gaps"], "Normal", size=9)
        elif t == "callout":
            para(doc, f"**{b.get('label') or b.get('kind', '').title() + ':'}** " + b["text"], "Normal")
        elif t == "pagebreak":
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        elif t == "spacer":
            doc.add_paragraph()
        else:
            raise SystemExit(f"unknown block type: {t}")

    mapping = json.loads(a.placeholders) if a.placeholders else {}
    for k, v in (("{{title}}", meta.get("title")), ("{{date}}", meta.get("date")), ("{{footer_title}}", meta.get("footer_title"))):
        if v and k not in mapping: mapping[k] = v
    if mapping: replace_placeholders(doc, mapping)

    cp = doc.core_properties
    if meta.get("title"): cp.title = meta["title"]
    if meta.get("subject"): cp.subject = meta["subject"]
    doc.save(a.out)
    print(f"wrote {a.out} from template {os.path.basename(a.template)}; table style: {tstyle}")
    if fallbacks:
        print("styles missing in template (fell back to direct formatting): " + ", ".join(sorted(set(fallbacks))))
    print("next: python3 scripts/set_metadata.py to set creator/company; bash scripts/render_preview.sh to look at it")


if __name__ == "__main__":
    main()
