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
"use strict";
const fs = require("fs"), path = require("path");
const D = require("docx");
const { Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType,
        ShadingType, BorderStyle, PageBreak, LevelFormat, Header, Footer, PageNumber, TabStopType, Tab,
        VerticalAlign, TableLayoutType } = D;

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
const cmToPx = (cm) => Math.round((cm * 360000) / 9525);
const resolveAsset = (p) => [path.resolve(contentDir, p), path.resolve(specDir, p), path.resolve(p)].find((f) => fs.existsSync(f));

// ---------- runs: **bold** and *italic* only
function runs(text, o = {}) {
  const base = { font: FONT, size: HP(o.size || "body"), color: C(o.color || "ink"), bold: o.bold, italics: o.italic, allCaps: o.caps };
  if (Array.isArray(text)) return text.map((t) => new TextRun({ ...base, ...t, size: t.size ? HP(t.size) : base.size, color: t.color ? C(t.color) : base.color, text: t.text }));
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
  children: runs(text, o),
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
      P(it.label, { size: "tiny", color: k.label, caps: true, after: 60, line: 240 }),
      P(it.value, { size: it.text_value ? "kpi_text" : "kpi", color: it.tone === "bad" ? k.bad : it.tone === "good" ? k.good : k.value, bold: true, after: 40, line: 240 }),
      P(it.note || "", { size: "small", color: k.note, after: 0, line: 220 }),
    ], ws[i], { fill: k.fill, margins: k.cell_margins, borders: bd }));
    return [table([new TableRow({ children: cells })], ws), spacer(SP.after_table)];
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
  h1(b) { const h = CMP.h1; return [P(b.text, { size: "h1", color: h.color, bold: h.bold, before: SP.h1_before, after: SP.h1_after, line: 240, rule: h.rule, keepNext: true })]; },
  h2(b) {
    const h = CMP.h2;
    const children = runs(b.text, { size: "h2", color: h.color, bold: h.bold });
    if (b.meta) children.push(new TextRun({ font: FONT, size: HP(h.meta_size), color: C(h.meta_color), children: [new Tab(), b.meta] }));
    return [new Paragraph({ children, keepNext: true, spacing: { before: SP.h2_before, after: SP.h2_after, line: 240 },
      tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W }],
      border: h.rule ? { bottom: { style: BorderStyle.SINGLE, color: C(h.rule.color), size: h.rule.sz, space: h.rule.space } } : undefined })];
  },
  h3(b) { const h = CMP.h3; return [P(b.text, { size: "h3", color: h.color, bold: h.bold, before: SP.h3_before, after: SP.h3_after, keepNext: true })]; },
  p(b) { return [P(b.text, { size: b.size, color: b.color, after: b.after ?? (b.tight ? SP.tight_after : SP.body_after), align: b.align === "right" ? AlignmentType.RIGHT : undefined })]; },
  bullets(b) { return b.items.map((t) => new Paragraph({ children: runs(t, { size: b.size }), numbering: { reference: "bullets", level: 0 }, spacing: { before: 0, after: 60, line: SP.body_line } })); },
  numbered(b) { return b.items.map((t) => new Paragraph({ children: runs(t, { size: b.size }), numbering: { reference: "numbers", level: 0 }, spacing: { before: 0, after: 60, line: SP.body_line } })); },
  snapshot(b) {
    const s = CMP.snapshot, lw = s.label_dxa, vw = TEXT_W - lw;
    const bd = { top: NONE, left: NONE, right: NONE, bottom: { style: BorderStyle.DOTTED, color: C(s.row_border.color), size: s.row_border.sz } };
    const rows = b.rows.map(([l, v], i) => new TableRow({ cantSplit: true, children: [
      cell(P(l, { size: "meta", color: s.label_color, bold: true, after: 0, line: 240 }), lw, { fill: i % 2 ? s.zebra : undefined, margins: s.cell_margins, borders: bd }),
      cell(P(v, { size: "meta", after: 0, line: 240 }), vw, { fill: i % 2 ? s.zebra : undefined, margins: s.cell_margins, borders: bd }),
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
    const head = new TableRow({ tableHeader: true, cantSplit: true, children: cols.map((c, i) => cell(P(c.header, { size, color: t.header_text, bold: true, after: 0, line: 240, align: al(c.align) }), ws[i], { fill: t.header_fill, margins: t.cell_margins })) });
    let zebra = 0;
    const body = b.rows.map((r) => {
      if (r && r.group !== undefined) { zebra = 0; return new TableRow({ cantSplit: true, children: [cell(P(r.group, { size, color: t.group_text, bold: true, after: 0, line: 240 }), TEXT_W, { fill: t.group_fill, margins: t.cell_margins, span: cols.length })] }); }
      const fill = zebra++ % 2 ? t.zebra : undefined;
      return new TableRow({ cantSplit: true, children: r.map((v, i) => {
        const o = typeof v === "object" && v !== null ? v : { text: v };
        return cell(P(String(o.text ?? ""), { size: o.size || cols[i].size || size, color: o.color, bold: o.bold ?? cols[i].bold, after: 0, line: 240, align: al(o.align || cols[i].align) }), ws[i], { fill, margins: t.cell_margins, borders: bd });
      }) });
    });
    const out = [table([head, ...body], ws)];
    if (b.note) out.push(spacer(40), P(b.note, { size: "small", color: "muted", after: SP.small_after, line: SP.small_line })); else out.push(spacer(SP.after_table));
    return out;
  },
  callout(b) {
    const c = CMP.callouts[b.kind] || { label: b.label, color: b.color || "ink", size: "callout" };
    return [new Paragraph({ spacing: { before: 0, after: b.after ?? 40, line: SP.body_line }, children: [
      new TextRun({ font: FONT, size: HP(c.size), color: C(c.color), bold: true, text: (b.label || c.label) + " " }),
      ...runs(b.text, { size: c.size, color: c.color, italic: c.italic_text }),
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
function footer() {
  const f = spec.footer;
  const left = f.left.replace("{footer_title}", meta.footer_title || meta.title || "").replace("{org}", spec.org || "");
  const r = (t) => new TextRun({ font: FONT, size: HP("footer"), color: C("muted"), text: t });
  return new Footer({ children: [new Paragraph({ tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W }], spacing: { before: 60 },
    border: { top: { style: BorderStyle.SINGLE, color: C(f.rule.color), size: f.rule.sz, space: f.rule.space } },
    children: [new TextRun({ font: FONT, size: HP("footer"), color: C("muted"), italics: true, text: left }),
      new TextRun({ font: FONT, size: HP("footer"), color: C("muted"), children: [new Tab(), "Page "] }),
      new TextRun({ font: FONT, size: HP("footer"), color: C("muted"), children: [PageNumber.CURRENT] }), r(" of "),
      new TextRun({ font: FONT, size: HP("footer"), color: C("muted"), children: [PageNumber.TOTAL_PAGES] })] })] });
}

// ---------- assemble
const children = [];
for (const b of content.blocks) {
  if (!B[b.type]) throw new Error(`unknown block type: ${b.type}`);
  children.push(...B[b.type](b));
}
const bl = CMP.bullets;
const doc = new Document({
  creator: spec.metadata.creator, lastModifiedBy: spec.metadata.lastModifiedBy, title: meta.title, subject: meta.subject, description: meta.subject, revision: 1,
  styles: { default: { document: { run: { font: FONT, size: HP("body"), color: C("ink") } } } },
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: bl.char, alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: bl.indent_left, hanging: bl.hanging } } } }] },
    { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: bl.indent_left, hanging: bl.hanging } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: PAGE.width_dxa, height: PAGE.height_dxa }, margin: { top: M.top, right: M.right, bottom: M.bottom, left: M.left, header: M.header, footer: M.footer, gutter: 0 } } },
    headers: { default: header() }, footers: { default: footer() }, children,
  }],
});
Packer.toBuffer(doc).then((buf) => { fs.mkdirSync(path.dirname(path.resolve(args.out)), { recursive: true }); fs.writeFileSync(args.out, buf); console.log(`wrote ${args.out} (${content.blocks.length} blocks, ${(buf.length / 1024).toFixed(0)} KB)`); });
