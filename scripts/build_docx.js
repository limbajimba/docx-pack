#!/usr/bin/env node
// Build a .docx from a style spec (tokens) and a content file (blocks) with docx-js.
//
//   node scripts/build_docx.js --spec house/silvertree.style-spec.json --content content.json --out report.docx
//
// The spec carries every visual decision (page, font, colours, sizes, spacing, header/footer,
// component recipes). The content carries only words and data. Swap the spec to re-skin the
// same content for another template; run codify_template.py on a template to draft a spec.
//
// Content schema (JSON):
//   { "meta": { "title", "kicker", "date", "right_lines": [], "footer_title", "subject" },
//     "blocks": [ ...see BLOCKS below... ] }
// Inline text supports **bold** and *italic*; nothing else. No "\n" (use separate blocks).
// Text may also be an array of spans [{text, bold, italic, link}] (a converter's output); a span with
// `link` becomes an external hyperlink in the spec's link colour.
// h1/h2/h3 are Word Heading 1-3 (styles take the spec's look, so the navigation pane and a TOC work);
// `toc` inserts a table of contents built from them, with page numbers from --toc-pages pages.json.
"use strict";
const fs = require("fs"), path = require("path");
const D = require("docx");
const { Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType,
        ShadingType, BorderStyle, PageBreak, LevelFormat, Header, Footer, PageNumber, TabStopType, Tab,
        VerticalAlign, TableLayoutType, HeadingLevel, Bookmark, ExternalHyperlink, TableOfContents, PageOrientation } = D;

// ---------- args
const args = Object.fromEntries(process.argv.slice(2).map((a, i, arr) => a.startsWith("--") ? [a.slice(2), arr[i + 1]] : []).filter(Boolean));
if (!args.spec || !args.content || !args.out) {
  console.error("usage: build_docx.js --spec spec.json --content content.json --out file.docx");
  process.exit(2);
}
const spec = JSON.parse(fs.readFileSync(args.spec, "utf8"));
const content = JSON.parse(fs.readFileSync(args.content, "utf8"));
const specDir = path.dirname(path.resolve(args.spec));
const contentDir = path.dirname(path.resolve(args.content));
const meta = content.meta || {};

// ---------- token helpers
const C = (k) => (spec.colors[k] !== undefined ? spec.colors[k] : k);           // colour role or literal hex
const PT = (k) => (typeof k === "number" ? k : spec.sizes_pt[k]);                // size role or literal pt
const HP = (k) => Math.round(PT(k) * 2);                                          // half-points
const SP = spec.spacing_dxa, CMP = spec.components, FONT = spec.font.body;
const PAGE = spec.page, M = PAGE.margins_dxa;
const TEXT_W = PAGE.width_dxa - M.left - M.right;
// landscape: spec gives the page as seen (width > height); docx-js wants portrait numbers plus the orientation flag and swaps them
const LANDSCAPE = PAGE.orientation === "landscape";
const PAGE_SIZE = LANDSCAPE
  ? { width: Math.min(PAGE.width_dxa, PAGE.height_dxa), height: Math.max(PAGE.width_dxa, PAGE.height_dxa), orientation: PageOrientation.LANDSCAPE }
  : { width: PAGE.width_dxa, height: PAGE.height_dxa };
const cmToPx = (cm) => Math.round((cm * 360000) / 9525);
const resolveAsset = (p) => [path.resolve(contentDir, p), path.resolve(specDir, p), path.resolve(p)].find((f) => fs.existsSync(f));

// ---------- runs: **bold** and *italic* only
function runs(text, o = {}) {
  const base = { font: FONT, size: HP(o.size || "body"), color: C(o.color || "ink"), bold: o.bold, italics: o.italic, allCaps: o.caps };
  if (Array.isArray(text)) return text.map((t0) => {
    const { link, italic, ...t } = typeof t0 === "string" ? { text: t0 } : t0;
    const r = new TextRun({ ...base, ...t, italics: t.italics ?? italic ?? base.italics, size: t.size ? HP(t.size) : base.size,
      color: link ? C(CMP.link?.color || "link") : t.color ? C(t.color) : base.color, underline: link && CMP.link?.underline !== false ? {} : undefined, text: t.text });
    return link ? new ExternalHyperlink({ link, children: [r] }) : r;
  });
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0, m;
  while ((m = re.exec(String(text))) !== null) {
    if (m.index > last) out.push(new TextRun({ ...base, text: text.slice(last, m.index) }));
    const tok = m[0];
    if (tok.startsWith("**")) out.push(new TextRun({ ...base, bold: true, text: tok.slice(2, -2) }));
    else out.push(new TextRun({ ...base, italics: true, text: tok.slice(1, -1) }));
    last = m.index + tok.length;
  }
  if (last < String(text).length) out.push(new TextRun({ ...base, text: String(text).slice(last) }));
  return out;
}
const P = (text, o = {}) => new Paragraph({
  children: o.children || runs(text, o),
  style: o.style, heading: o.heading, pageBreakBefore: o.pageBreakBefore, indent: o.indent,
  spacing: { before: o.before ?? 0, after: o.after ?? SP.body_after, line: o.line ?? SP.body_line },
  alignment: o.align, keepNext: o.keepNext, keepLines: o.keepLines,
  border: o.rule ? { bottom: { style: BorderStyle.SINGLE, color: C(o.rule.color), size: o.rule.sz, space: o.rule.space } } : undefined,
  tabStops: o.tabStops,
});
const border = (style, color, sz) => ({ style, color: C(color), size: sz });
const NONE = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: NONE, bottom: NONE, left: NONE, right: NONE };
const cellMargins = (m) => ({ marginUnitType: WidthType.DXA, top: m.top, bottom: m.bottom, left: m.left, right: m.right });

function cell(children, w, o = {}) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    shading: o.fill ? { type: ShadingType.CLEAR, fill: C(o.fill), color: "auto" } : undefined,
    borders: o.borders || noBorders,
    margins: cellMargins(o.margins),
    verticalAlign: o.valign,
    columnSpan: o.span,
    children: Array.isArray(children) ? children : [children],
  });
}
const table = (rows, widths, o = {}) => new Table({
  width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
  columnWidths: widths, layout: TableLayoutType.FIXED,
  borders: { top: NONE, bottom: NONE, left: NONE, right: NONE, insideHorizontal: NONE, insideVertical: NONE },
  rows,
});
const spacer = (after) => new Paragraph({ spacing: { before: 0, after, line: SP.body_line }, children: [] });
const splitEven = (n, total) => { const w = Math.floor(total / n); const ws = Array(n).fill(w); ws[n - 1] += total - w * n; return ws; };
const plain = (t) => (Array.isArray(t) ? t.map((x) => (typeof x === "string" ? x : x.text)).join("") : String(t ?? "").replace(/\*\*([^*]+)\*\*|\*([^*]+)\*/g, "$1$2"));

// ---------- headings: Word Heading 1-3 with the spec's look, each bookmarked so a TOC entry can link to it
const HEADING = { h1: HeadingLevel.HEADING_1, h2: HeadingLevel.HEADING_2, h3: HeadingLevel.HEADING_3 };
const tocEntries = [];
let tocSeq = 0, hasTitlePage = false;
// Opt-in (meta.word_headings, or any toc block) so documents built before this change keep their structure.
const WORD_HEADINGS = meta.word_headings ?? content.blocks.some((b) => b.type === "toc");
function heading(kind, b, children) {
  if (b.toc === false || !WORD_HEADINGS) return { children };  // looks like a heading, stays out of the outline and the TOC
  const anchor = `_Toc${String(++tocSeq).padStart(5, "0")}`;
  tocEntries.push({ level: +kind.slice(1), title: plain(b.text), anchor });
  return { heading: HEADING[kind], children: [new Bookmark({ id: anchor, children })] };
}

// ---------- lists: every block restarts its numbering (continue: true joins the previous list); start sets the first number
const listRefs = new Map();
let listInstance = 0, lastNumbered = null;
function listRef(kind, start, style) {
  const ref = kind + (style === "sources" ? "-src" : "") + (kind === "numbers" && start !== 1 ? `-s${start}` : "");
  if (!listRefs.has(ref)) listRefs.set(ref, { kind, start, style });
  return ref;
}
// Sources style: the smaller paragraph style for a chapter's source list
const SRC = { size: "caption", color: "ink", after: 30, line: 240, indent_left: 360, hanging: 360, list_indent_left: 400, list_hanging: 400, ...(CMP.sources || {}) };
const listSpacing = (style) => (style === "sources" ? { before: 0, after: SRC.after, line: SRC.line } : { before: 0, after: 60, line: SP.body_line });

// ---------- BLOCKS
const B = {
  title_band(b) {
    const t = CMP.title_band, rw = t.right_col_dxa, lw = TEXT_W - rw;
    const left = [
      P(b.kicker || meta.kicker || "", { size: "kicker", color: t.text, bold: true, caps: true, after: 60, line: 240 }),
      P(b.title || meta.title || "", { size: "title", color: t.text, bold: true, caps: true, after: 0, line: 300 }),
    ];
    const right = [P(b.date || meta.date || "", { size: "date", color: t.text, bold: true, align: AlignmentType.RIGHT, after: 40, line: 240 })];
    for (const l of b.right_lines || meta.right_lines || []) right.push(P(l, { size: "kicker", color: t.text, align: AlignmentType.RIGHT, after: 40, line: 240 }));
    return [table([new TableRow({ children: [cell(left, lw, { fill: t.fill, margins: t.cell_margins, valign: VerticalAlign.CENTER }), cell(right, rw, { fill: t.fill, margins: t.cell_margins, valign: VerticalAlign.CENTER })] })], [lw, rw]), spacer(60)];
  },
  verdict(b) {
    const v = CMP.verdict_bar;
    return [table([new TableRow({ children: [cell(P(b.text, { size: "verdict", color: v.text, bold: true, after: 0, line: 264 }), TEXT_W, { fill: v.fill, margins: v.cell_margins })] })], [TEXT_W]), spacer(80)];
  },
  basis(b) { return [P(b.text, { size: CMP.basis.size, color: CMP.basis.color, after: SP.small_after, line: SP.small_line })]; },
  kpis(b) {
    const k = CMP.kpi_tiles, ws = splitEven(b.items.length, TEXT_W);
    const bd = { top: border(BorderStyle.SINGLE, k.top_border.color, k.top_border.sz), bottom: NONE, left: border(BorderStyle.SINGLE, k.gap_border.color, k.gap_border.sz), right: border(BorderStyle.SINGLE, k.gap_border.color, k.gap_border.sz) };
    const cells = b.items.map((it, i) => cell([
      P(it.label, { size: "tiny", color: k.label, caps: true, after: 60, line: 240, keepNext: true }),
      P(it.value, { size: it.text_value ? "kpi_text" : "kpi", color: it.tone === "bad" ? k.bad : it.tone === "good" ? k.good : k.value, bold: true, after: 40, line: 240, keepNext: true }),
      P(it.note || "", { size: "small", color: k.note, after: 0, line: 220, keepNext: true }),
    ], ws[i], { fill: k.fill, margins: k.cell_margins, borders: bd }));
    return [table([new TableRow({ children: cells })], ws), spacer(SP.after_table)];
  },
  // figure_grid: charts side by side, each with its caption (title, sources line, note) under it.
  // cells: [{path, width_cm?, height_cm?, title, sources, note, span?}], cols (default 2)
  figure_grid(b) {
    const cols = b.cols || 2, gap = b.gap_dxa ?? 240, colW = splitEven(cols, TEXT_W);
    const rows = [];
    let cur = [], used = 0;
    const flush = () => { if (!cur.length) return; if (used < cols) cur.push(cell([P("", { after: 0 })], colW.slice(used).reduce((a, x) => a + x, 0), { span: cols - used > 1 ? cols - used : undefined, margins: { top: 0, bottom: 0, left: 0, right: 0 } })); rows.push(new TableRow({ cantSplit: true, children: cur })); cur = []; used = 0; };
    for (const c of b.cells) {
      const span = Math.min(c.span || 1, cols);
      if (used + span > cols) flush();
      const w = colW.slice(used, used + span).reduce((a, x) => a + x, 0);
      const f = resolveAsset(c.path);
      if (!f) throw new Error(`figure not found: ${c.path}`);
      const buf = fs.readFileSync(f), ratio = buf.readUInt32BE(20) / buf.readUInt32BE(16);
      const maxCm = ((w - gap) / 1440) * 2.54, wcm = Math.min(c.width_cm || maxCm, maxCm), hcm = c.height_cm || wcm * ratio;
      // no keepNext inside the grid: Word and LibreOffice then hold the whole table with the next block and leave the headline alone
      const kids = [new Paragraph({ alignment: AlignmentType.LEFT, spacing: { before: 0, after: 40 },
        children: [new ImageRun({ type: "png", data: buf, transformation: { width: cmToPx(wcm), height: cmToPx(hcm) } })] })];
      if (c.title) kids.push(P(c.title, { size: "small", color: "ink", bold: true, after: 10, line: 220 }));
      if (c.sources) kids.push(P(c.sources, { size: "tiny", color: "muted", after: 10, line: 200 }));
      if (c.note) kids.push(P(c.note, { size: "tiny", color: "muted", after: 0, line: 200 }));
      cur.push(cell(kids, w, { span: span > 1 ? span : undefined, valign: VerticalAlign.TOP, margins: { top: 0, bottom: b.row_gap_dxa ?? 160, left: 0, right: gap } }));
      used += span;
      if (used === cols) flush();
    }
    flush();
    return [table(rows, colW), spacer(SP.after_table)];
  },
  image(b) {
    const f = resolveAsset(b.path);
    if (!f) throw new Error(`image not found: ${b.path}`);
    const wcm = b.width_cm || 16, hcm = b.height_cm || (() => { try { const { imageSize } = require("./imgsize"); return null; } catch { return null; } })();
    // derive height from PNG header if not given
    let ratio = b.aspect || null;
    if (!ratio) { const buf = fs.readFileSync(f); if (buf.toString("ascii", 1, 4) === "PNG") { const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20); ratio = h / w; } else ratio = 0.55; }
    const out = [new Paragraph({ alignment: b.align === "left" ? AlignmentType.LEFT : AlignmentType.CENTER, spacing: { before: 0, after: 60 }, children: [new ImageRun({ type: path.extname(f).slice(1).replace("jpeg", "jpg"), data: fs.readFileSync(f), transformation: { width: cmToPx(wcm), height: cmToPx(hcm || wcm * ratio) } })] })];
    if (b.caption) out.push(P(b.caption, { size: "small", color: "muted", after: SP.small_after, line: SP.small_line }));
    return out;
  },
  h1(b) {
    const h = CMP.h1, kids = runs(b.text, { size: "h1", color: h.color, bold: h.bold });
    return [P(null, { ...heading("h1", b, kids), before: b.page_break_before ? 0 : SP.h1_before, after: SP.h1_after, line: 240, rule: h.rule, keepNext: true, keepLines: true, pageBreakBefore: b.page_break_before })];
  },
  h2(b) {
    const h = CMP.h2;
    const children = runs(b.text, { size: "h2", color: h.color, bold: h.bold });
    if (b.meta) children.push(new TextRun({ font: FONT, size: HP(h.meta_size), color: C(h.meta_color), children: [new Tab(), b.meta] }));
    return [new Paragraph({ ...heading("h2", b, children), keepNext: true, keepLines: true, pageBreakBefore: b.page_break_before,
      spacing: { before: b.page_break_before ? 0 : SP.h2_before, after: SP.h2_after, line: 240 },
      tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W }],
      border: h.rule ? { bottom: { style: BorderStyle.SINGLE, color: C(h.rule.color), size: h.rule.sz, space: h.rule.space } } : undefined })];
  },
  h3(b) {
    const h = CMP.h3, kids = runs(b.text, { size: "h3", color: h.color, bold: h.bold });
    return [P(null, { ...heading("h3", b, kids), before: SP.h3_before, after: SP.h3_after, keepNext: true, keepLines: true })];
  },
  p(b) {
    if (b.style === "sources") return [P(b.text, { style: "Sources", size: SRC.size, color: SRC.color, after: SRC.after, line: SRC.line, indent: { left: SRC.indent_left, hanging: SRC.hanging }, keepNext: b.keep_next })];
    return [P(b.text, { size: b.size, color: b.color, after: b.after ?? (b.tight ? SP.tight_after : SP.body_after), align: b.align === "right" ? AlignmentType.RIGHT : undefined, keepNext: b.keep_next })];
  },
  bullets(b) {
    const ref = listRef("bullets", 1, b.style), src = b.style === "sources";
    return b.items.map((t) => new Paragraph({ style: src ? "Sources" : undefined, children: runs(t, { size: b.size || (src ? SRC.size : undefined), color: src ? SRC.color : undefined }), numbering: { reference: ref, level: 0 }, spacing: listSpacing(b.style) }));
  },
  numbered(b) {
    const src = b.style === "sources";
    const { ref, inst } = b.continue && lastNumbered ? lastNumbered : { ref: listRef("numbers", b.start || 1, b.style), inst: ++listInstance };
    lastNumbered = { ref, inst };
    return b.items.map((t) => new Paragraph({ style: src ? "Sources" : undefined, children: runs(t, { size: b.size || (src ? SRC.size : undefined), color: src ? SRC.color : undefined }), numbering: { reference: ref, level: 0, instance: inst }, spacing: listSpacing(b.style) }));
  },
  title_page(b) {
    // A title page: the house title band, set lower and larger, then any notes. The TOC (or the next block) starts page 2.
    const t = CMP.title_band, tp = { top_dxa: 2400, title_size: 20, kicker_size: 9, date_size: 11, line_size: 9, gap_dxa: 360, caps: true,
      cell_margins: { top: 360, bottom: 360, left: 300, right: 200 }, ...(CMP.title_page || {}) };
    const rw = t.right_col_dxa, lw = TEXT_W - rw;
    const left = [
      P(b.kicker || meta.kicker || "", { size: tp.kicker_size, color: t.text, bold: true, caps: true, after: 140, line: 240 }),
      P(b.title || meta.title || "", { style: "Title", size: tp.title_size, color: t.text, bold: true, caps: tp.caps, after: 0, line: tp.title_line || 250 }),
    ];
    const right = [P(b.date || meta.date || "", { size: tp.date_size, color: t.text, bold: true, align: AlignmentType.RIGHT, after: 80, line: 240 })];
    for (const l of b.right_lines || meta.right_lines || []) right.push(P(l, { size: tp.line_size, color: t.text, align: AlignmentType.RIGHT, after: 40, line: 240 }));
    const out = [spacer(tp.top_dxa), table([new TableRow({ children: [cell(left, lw, { fill: t.fill, margins: tp.cell_margins, valign: VerticalAlign.CENTER }), cell(right, rw, { fill: t.fill, margins: tp.cell_margins, valign: VerticalAlign.CENTER })] })], [lw, rw]), spacer(tp.gap_dxa)];
    for (const n of b.notes || []) out.push(P(n, { size: tp.note_size || "body", after: SP.body_after }));
    hasTitlePage = true;
    return out;
  },
  toc(b) { return [{ __toc: b }]; },  // filled after every heading is known
  snapshot(b) {
    const s = CMP.snapshot, lw = s.label_dxa, vw = TEXT_W - lw;
    const bd = { top: NONE, left: NONE, right: NONE, bottom: { style: BorderStyle.DOTTED, color: C(s.row_border.color), size: s.row_border.sz } };
    const keep = b.rows.length <= 12;  // short tables stay on one page; long ones may break
    const rows = b.rows.map(([l, v], i) => new TableRow({ cantSplit: true, children: [
      cell(P(l, { size: "meta", color: s.label_color, bold: true, after: 0, line: 240, keepNext: keep && i < b.rows.length - 1 }), lw, { fill: i % 2 ? s.zebra : undefined, margins: s.cell_margins, borders: bd }),
      cell(P(v, { size: "meta", after: 0, line: 240, keepNext: keep && i < b.rows.length - 1 }), vw, { fill: i % 2 ? s.zebra : undefined, margins: s.cell_margins, borders: bd }),
    ] }));
    return [table(rows, [lw, vw]), spacer(SP.after_table)];
  },
  table(b) {
    const t = CMP.table, cols = b.columns, ws = cols.map((c) => c.width);
    const sum = ws.reduce((a, x) => a + x, 0);
    if (sum !== TEXT_W) { const k = TEXT_W / sum; for (let i = 0; i < ws.length; i++) ws[i] = Math.round(ws[i] * k); ws[ws.length - 1] += TEXT_W - ws.reduce((a, x) => a + x, 0); }
    const size = b.size || "table";
    const al = (a) => (a === "right" ? AlignmentType.RIGHT : a === "center" ? AlignmentType.CENTER : undefined);
    const bd = { top: NONE, left: NONE, right: NONE, bottom: { style: BorderStyle.DOTTED, color: C(t.row_border.color), size: t.row_border.sz } };
    // short tables move as one piece (keepNext on every row but the last); long ones may break between rows
    const keep = b.keep_together ?? b.rows.length <= (t.keep_rows ?? 12);
    const head = new TableRow({ tableHeader: true, cantSplit: true, children: cols.map((c, i) => cell(P(c.header, { size, color: t.header_text, bold: true, after: 0, line: 240, align: al(c.align), keepNext: true }), ws[i], { fill: t.header_fill, margins: t.cell_margins })) });
    let zebra = 0;
    const body = b.rows.map((r, ri) => {
      const kn = keep && ri < b.rows.length - 1;
      if (r && r.group !== undefined) { zebra = 0; return new TableRow({ cantSplit: true, children: [cell(P(r.group, { size, color: t.group_text, bold: true, after: 0, line: 240, keepNext: true }), TEXT_W, { fill: t.group_fill, margins: t.cell_margins, span: cols.length })] }); }
      const fill = zebra++ % 2 ? t.zebra : undefined;
      return new TableRow({ cantSplit: true, children: r.map((v, i) => {
        const o = Array.isArray(v) ? { text: v } : typeof v === "object" && v !== null ? v : { text: v };
        return cell(P(Array.isArray(o.text) ? o.text : String(o.text ?? ""), { size: o.size || cols[i].size || size, color: o.color, bold: o.bold ?? cols[i].bold, after: 0, line: 240, align: al(o.align || cols[i].align), keepNext: kn }), ws[i], { fill, margins: t.cell_margins, borders: bd });
      }) });
    });
    const out = [table([head, ...body], ws)];
    if (b.note) out.push(spacer(40), P(b.note, { size: "small", color: "muted", after: SP.small_after, line: SP.small_line })); else out.push(spacer(SP.after_table));
    return out;
  },
  callout(b) {
    const c = CMP.callouts[b.kind] || { label: b.label, color: b.color || "ink", size: "callout" };
    const label = b.label || c.label;
    // Authors often type the label into the text as well ("Counter: Counter: ..."); keep one.
    const text = String(b.text).replace(new RegExp("^\\s*" + label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\s*", "i"), "");
    return [new Paragraph({ spacing: { before: 0, after: b.after ?? 40, line: SP.body_line }, children: [
      new TextRun({ font: FONT, size: HP(c.size), color: C(c.color), bold: true, text: label + " " }),
      ...runs(text, { size: c.size, color: c.color, italic: c.italic_text }),
    ] })];
  },
  finding(b) {
    const out = B.h2({ text: b.code ? `${b.code}  ${b.title}` : b.title, meta: b.meta });
    for (const t of Array.isArray(b.body) ? b.body : [b.body]) out.push(P(t, { after: SP.tight_after }));
    if (b.counter) out.push(...B.callout({ kind: "counter", text: b.counter }));
    if (b.gaps) out.push(...B.callout({ kind: "gaps", text: b.gaps, after: SP.small_after }));
    return out;
  },
  pagebreak() { return [new Paragraph({ children: [new PageBreak()] })]; },
  spacer(b) { return [spacer(b.after || 120)]; },
};

// ---------- header / footer
function header() {
  const h = spec.header, children = [];
  if (h.logo) { const f = resolveAsset(h.logo); if (f) children.push(new ImageRun({ type: "png", data: fs.readFileSync(f), transformation: { width: cmToPx(h.logo_cm[0]), height: cmToPx(h.logo_cm[1]) } })); }
  children.push(new TextRun({ font: FONT, size: HP("header"), color: C("muted"), italics: true, allCaps: true, children: [new Tab(), meta.confidential || h.right_text] }));
  return new Header({ children: [new Paragraph({ children, tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W }], spacing: { after: 60 },
    border: { bottom: { style: BorderStyle.SINGLE, color: C(h.rule.color), size: h.rule.sz, space: h.rule.space } } })] });
}
function footer(first = false) {
  const f = spec.footer;
  const left = f.left.replace("{footer_title}", meta.footer_title || meta.title || "").replace("{org}", spec.org || "");
  const r = (t) => new TextRun({ font: FONT, size: HP("footer"), color: C("muted"), text: t });
  const leftRun = new TextRun({ font: FONT, size: HP("footer"), color: C("muted"), italics: true, text: left });
  const rule = { top: { style: BorderStyle.SINGLE, color: C(f.rule.color), size: f.rule.sz, space: f.rule.space } };
  if (first) return new Footer({ children: [new Paragraph({ spacing: { before: 60 }, border: rule, children: [leftRun] })] });  // title page: no page number
  return new Footer({ children: [new Paragraph({ tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W }], spacing: { before: 60 },
    border: rule,
    children: [leftRun,
      new TextRun({ font: FONT, size: HP("footer"), color: C("muted"), children: [new Tab(), "Page "] }),
      new TextRun({ font: FONT, size: HP("footer"), color: C("muted"), children: [PageNumber.CURRENT] }), r(" of "),
      new TextRun({ font: FONT, size: HP("footer"), color: C("muted"), children: [PageNumber.TOTAL_PAGES] })] })] });
}

// ---------- table of contents: a Word TOC field whose cached result is filled in, so it reads correctly before
// anyone presses F9. Page numbers come from --toc-pages (a JSON map anchor -> page, e.g. measured on a render);
// without it the entries carry no numbers until Word updates the field.
const TOCS = { levels: 2, size1: "body", size2: 9.5, size3: 9, indent: 280, right_indent: 560, ...(CMP.toc || {}) };
function buildToc(b) {
  const max = b.levels || TOCS.levels;
  const pages = args["toc-pages"] ? JSON.parse(fs.readFileSync(args["toc-pages"], "utf8")) : {};
  class Toc extends TableOfContents { getTabStopsForLevel() { return [{ type: TabStopType.RIGHT, position: TEXT_W, leader: "dot" }]; } }
  const entries = tocEntries.filter((e) => e.level <= max).map((e) => ({ title: e.title, level: e.level, page: pages[e.anchor] ?? "", href: e.anchor }));
  const title = P(b.title || "Contents", { size: "h1", color: CMP.h1.color, bold: CMP.h1.bold, after: SP.h1_after, line: 240, rule: CMP.h1.rule, pageBreakBefore: b.page_break_before ?? hasTitlePage });
  return [title, new Toc(b.title || "Contents", { hyperlink: true, headingStyleRange: `1-${max}`, hideTabAndPageNumbersInWebView: true, useAppliedParagraphOutlineLevel: true, cachedEntries: entries, beginDirty: false })];
}

// ---------- assemble
const children = [];
for (const b of content.blocks) {
  if (!B[b.type]) throw new Error(`unknown block type: ${b.type}`);
  children.push(...B[b.type](b));
}
for (let i = 0; i < children.length; i++) if (children[i] && children[i].__toc) children.splice(i, 1, ...buildToc(children[i].__toc));
if (args["toc-out"]) fs.writeFileSync(args["toc-out"], JSON.stringify(tocEntries, null, 1));

const bl = CMP.bullets, nl = { indent_left: bl.indent_left, hanging: bl.hanging, ...(CMP.numbered || {}) };
const listLevel = (r) => {
  const src = r.style === "sources";
  const ind = src ? { left: SRC.list_indent_left, hanging: SRC.list_hanging } : r.kind === "bullets" ? { left: bl.indent_left, hanging: bl.hanging } : { left: nl.indent_left, hanging: nl.hanging };
  return r.kind === "bullets"
    ? { level: 0, format: LevelFormat.BULLET, text: bl.char, alignment: AlignmentType.LEFT, style: { paragraph: { indent: ind } } }
    : { level: 0, format: LevelFormat.DECIMAL, text: "%1.", start: r.start, alignment: AlignmentType.LEFT, style: { paragraph: { indent: ind } } };
};
listRefs.set("bullets", { kind: "bullets", start: 1 }); listRefs.set("numbers", { kind: "numbers", start: 1 });
const numberingConfig = [...listRefs].map(([reference, r]) => ({ reference, levels: [listLevel(r)] }));

// Styles: headings take the spec's look (docx-js would otherwise write Word's blue); TOC and Sources styles are named
// so a reader editing in Word finds them in the styles pane.
const hstyle = (k, lvl) => ({ run: { font: FONT, size: HP(k), bold: CMP[k].bold, color: C(CMP[k].color) },
  paragraph: { spacing: { before: SP[`${k}_before`], after: SP[`${k}_after`], line: 240 }, keepNext: true, keepLines: true, outlineLevel: lvl } });
const minor = { run: { font: FONT, size: HP("body"), bold: true, color: C(CMP.h3.color) }, paragraph: { keepNext: true } };
const tocStyle = (n, size, o = {}) => ({ id: `TOC${n}`, name: `toc ${n}`, basedOn: "Normal", next: "Normal", uiPriority: 39,
  run: { font: FONT, size: HP(size), color: C(o.color || "ink"), bold: o.bold },
  paragraph: { spacing: { before: o.before ?? 0, after: o.after ?? 40, line: 240 }, indent: { left: (n - 1) * TOCS.indent, right: TOCS.right_indent },
    tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W, leader: "dot" }] } });
const docStyles = {
  default: {
    document: { run: { font: FONT, size: HP("body"), color: C("ink") } },
    title: { run: { font: FONT, size: HP("title"), bold: true, color: C(CMP.h1.color) } },
    heading1: hstyle("h1", 0), heading2: hstyle("h2", 1), heading3: hstyle("h3", 2), heading4: minor, heading5: minor, heading6: minor,
    hyperlink: { run: { color: C(CMP.link?.color || "link"), underline: { type: "single" } } },
  },
  paragraphStyles: [
    tocStyle(1, TOCS.size1, { bold: true, color: CMP.h1.color, before: 120 }), tocStyle(2, TOCS.size2), tocStyle(3, TOCS.size3),
    { id: "Sources", name: "Sources", basedOn: "Normal", next: "Sources", quickFormat: true,
      run: { font: FONT, size: HP(SRC.size), color: C(SRC.color) }, paragraph: { spacing: { before: 0, after: SRC.after, line: SRC.line } } },
  ],
  characterStyles: [{ id: "IndexLink", name: "Index Link", basedOn: "DefaultParagraphFont", run: {} }],
};

const doc = new Document({
  creator: spec.metadata.creator, lastModifiedBy: spec.metadata.lastModifiedBy, title: meta.title, subject: meta.subject, description: meta.subject, revision: 1,
  styles: docStyles,
  numbering: { config: numberingConfig },
  sections: [{
    properties: { titlePage: hasTitlePage, page: { size: PAGE_SIZE, margin: { top: M.top, right: M.right, bottom: M.bottom, left: M.left, header: M.header, footer: M.footer, gutter: 0 } } },
    headers: hasTitlePage ? { default: header(), first: header() } : { default: header() },
    footers: hasTitlePage ? { default: footer(), first: footer(true) } : { default: footer() }, children,
  }],
});
Packer.toBuffer(doc).then((buf) => {
  fs.mkdirSync(path.dirname(path.resolve(args.out)), { recursive: true });
  fs.writeFileSync(args.out, buf);
  console.log(`wrote ${args.out} (${content.blocks.length} blocks, ${(buf.length / 1024).toFixed(0)} KB)`);
  // Metadata: docx-js leaves app.xml empty and cannot set Company/Application; finish with set_metadata.py.
  if (!("no-metadata" in args)) {
    const md = spec.metadata || {};
    const r = require("child_process").spawnSync("python3", [path.join(__dirname, "set_metadata.py"), args.out,
      "--creator", md.creator || spec.org || "", "--company", md.company || spec.org || "", "--last-modified-by", md.lastModifiedBy || md.creator || spec.org || "",
      "--application", md.application || "Microsoft Office Word", ...(meta.title ? ["--title", meta.title] : []), ...(meta.subject ? ["--subject", meta.subject] : [])], { encoding: "utf8" });
    process.stdout.write(r.status === 0 ? r.stdout : `set_metadata failed: ${r.stderr}\n`);
  }
  console.log(`next: bash scripts/render_preview.sh ${args.out} && python3 scripts/lint_docx.py ${args.out} --spec ${args.spec}`);
});
