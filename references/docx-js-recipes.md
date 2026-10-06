# docx-js recipes: the house components, codified

Every component below is implemented in `scripts/build_docx.js` and driven by tokens in the style spec. This file
is the reading copy: what each component is, the tokens it uses, and the docx-js details that bite. Values are
the SilverTree spec (`house/silvertree.style-spec.json`), codified from the September 2026 AI Defensibility
exemplar. Units: DXA (1/20 pt; 1440 = 1 inch; 567 = 1 cm), half-points for font sizes, EMU for images
(360000 = 1 cm; docx-js `transformation` takes pixels at 96 dpi: px = EMU / 9525).

## Page and defaults

A4 11906 x 16838. Margins top 1250, bottom 1100, left and right 1134 (2 cm), header 500, footer 500.
Text width 9638. One typeface throughout (Gill Sans MT), body 10 pt, ink 2E3232. docx-js sets this through
`styles.default.document.run`; every run still names `font` explicitly because Word's fallback is Calibri.

Palette roles: ink 2E3232 · muted 646A7A · navy 132246 · teal 0B4E6F · slate 44596D · red C0392B (flag) ·
rule E9EBEB · fill F2F2F2 (zebra, tiles) · white · link 0563C1. Red is a status colour: weakest area, N/E, FALSE.

## Header and footer

Header: one paragraph, logo `ImageRun` (2.86 x 1.06 cm) then a `TextRun` whose `children` are `[new Tab(),
"STRICTLY CONFIDENTIAL"]`, 7.5 pt italic muted all-caps, right tab stop at 9638, bottom border rule E9EBEB sz 4
space 4, spacing after 60.
Footer: top border rule; left italic 8 pt muted "<short title>  |  Strictly confidential  |  SilverTree Equity";
tab; "Page " `PageNumber.CURRENT` " of " `PageNumber.TOTAL_PAGES`.

## Title band (`title_band`)

One-row, two-cell table, both cells navy fill, no borders, fixed layout, widths 7000 + 2638, cell margins
top/bottom 200, left 220, right 90, vertical align centre. Left: kicker 8 pt bold all-caps white (spacing after
60, line 240) then title 17 pt bold all-caps white (line 300). Right: date 10 pt bold white right-aligned, then
up to three 8 pt lines right-aligned. A 60 spacer paragraph follows.

## Verdict bar (`verdict`)

One-cell table, teal fill, no borders, cell margins 130/130/220/220, one sentence 10.5 pt bold white, line 264.
80 spacer after. The sentence is the governing thought: 25 words or fewer.

## Basis lines (`basis`)

7.5 pt muted, line 240, after 80. Two uses: the one-paragraph description of the subject, and the "Basis:"
paragraph naming the evidence count, date, framework and scale. Also used for table notes and the chart note.

## Section heading (`h1`)

12 pt bold navy, before 320, after 140, line 240, bottom border navy sz 6 space 3, keepNext. Sentence case.
Appendix headings use a middle dot separator: "Appendix A  ·  Driver scores".

## Finding heading with meta (`h2`, and inside `finding`)

10 pt bold navy "A1  Workflow & user replacement by AI agents", then a run with `[new Tab(), meta]` in 7.5 pt
muted, right tab stop at 9638, bottom border E9EBEB sz 4 space 2, before 200, after 60, keepNext. Meta text is
"7.0 / 10   ·   weight 11%   ·   coverage 100%".

## Sub-heading (`h3`)

10 pt bold navy, before 120, after 80, no rule. Used for "What would prove this wrong" and "What moves the score".

## Body paragraph (`p`)

10 pt ink, line 276, after 140 (or 60 with `tight`, as inside findings). Inline `**bold**` and `*italic*` only.
Citations are plain text in square brackets [F11, F29].

## Callouts (`callout`, and `counter` / `gaps` inside `finding`)

Counter: 9 pt red, label bold, text italic, after 40. Gaps: 8 pt muted, label bold, text regular, after 80.
Both are single paragraphs with two run styles; no table, no shading.

## KPI tiles (`kpis`)

One-row table, one cell per tile, equal widths summing to 9638 (five tiles = 1927 each, last 1930). Cell fill
F2F2F2, top border navy sz 24, left and right borders white sz 12 (the gutters), no bottom border, margins
90/110/120/100. Three paragraphs per tile: label 7 pt muted all-caps (after 60, line 240); value 15 pt bold navy
(red when `tone: "bad"`, teal when `"good"`; 10 pt when `text_value: true`, e.g. "Neither"); note 7.5 pt ink (line
220). 100 spacer after.

## Snapshot (`snapshot`)

Two-column table 2400 + 7238, no outer borders, each cell bottom border dotted E9EBEB sz 4, zebra F2F2F2 on
odd rows, margins 45/45/80/80. Label 8.5 pt bold navy, value 8.5 pt ink, line 240, after 0.

## Data table (`table`)

Header row: navy fill, white 8 pt bold, `tableHeader: true` (repeats on page break), no borders. Body rows:
8 pt (7.5 pt with `size: "table_small"`), dotted E9EBEB bottom border, zebra F2F2F2, `cantSplit`. Group rows
(`{"group": "..."}`) span all columns, teal fill, white bold; zebra restarts after a group row. Column widths are
given in DXA and rescaled to 9638 if they do not sum to it. Cells may be strings or `{text, bold, color, align,
size}`; numbers right-aligned, evidence grades centred. Optional `note` renders a basis line under the table.

## Chart image (`image`)

`scripts/chart_bars.py` renders horizontal bars in the palette at 200 dpi: navy bars, flagged rows red (bar and
label), value labels bold ink at the bar end, dashed teal threshold line labelled inside the plot, recessive grid
in rule colour, no legend (single series), title 9.5 pt bold. Place with `width_cm` 15.5; height follows the
PNG aspect ratio. The chart is a picture in Word, so every number on it must also appear in a table.

## Lists (`bullets`, `numbered`)

`numbering.config` with `LevelFormat.BULLET` "•" (indent left 540, hanging 260) and `LevelFormat.DECIMAL` "%1.".
Never type "•" or "1." into text. One sentence per item, after 60. Each `numbered` block restarts at 1 (its own
numbering instance); `start: n` begins at n (a reference per start value, since docx-js writes the level's `start`
as the instance's startOverride); `continue: true` joins the previous list. A source list with gaps (1-9, 12,
14...) is one block per run of consecutive numbers, so Word shows the source's own numbers.

## Long documents: title page, headings, contents, sources

- `meta.word_headings: true` (or any `toc` block) makes `h1`/`h2`/`h3` real Heading 1-3 paragraphs. The styles
  are redefined from the spec (font, size, navy, spacing, `outlineLevel`), so no Word blue; each heading is
  wrapped in a `_Toc00001`-style bookmark. `page_break_before: true` on a heading starts it on a new page.
  Off by default so documents built earlier keep their structure.
- `title_page`: the title band set lower and larger (`components.title_page`), `kicker`, `title` (Title style),
  `date`, `right_lines`, then `notes` paragraphs. Turns on `titlePg`: the first page footer drops the page number.
- `toc`: a Word TOC field (`TOC \h \o "1-2" \u \z`, `levels` sets the depth) whose cached result is filled with
  the headings, linked to their bookmarks, `dirty` false, so it reads correctly without an update prompt. Page
  numbers come from `--toc-pages pages.json` (anchor to page); `--toc-out` writes the heading list. Measure pages
  on a render (LibreOffice writes the headings as the PDF outline: PyMuPDF `get_toc()`), rebuild, repeat until no
  entry moves. Styles `toc 1`-`toc 3` carry the look (right tab with dot leader at the text width).
- `style: "sources"` on `p`, `bullets` or `numbered`: the named Sources paragraph style (`components.sources`,
  8 pt, after 20-30, hanging indent), for a chapter's source list.
- Text may be an array of spans `{text, bold, italic, link}`; a `link` span is an `ExternalHyperlink` in the
  link colour. Table cells accept span arrays too.
- `table`: tables of 12 rows or fewer (`components.table.keep_rows`, or `keep_together`) move as one piece:
  `keepNext` on every row but the last.

## docx-js details that bite (docx 9.7)

- `require("docx")` works from `scripts/` (dependency in `scripts/package.json`). Do not `npm install` elsewhere.
- Tables need `columnWidths` **and** a `width` on every cell, all DXA; set `layout: TableLayoutType.FIXED`.
- Shading is `ShadingType.CLEAR` with `fill`; `SOLID` renders black in some viewers.
- Borders you do not want must be set to `BorderStyle.NONE` on the table **and** the cells; docx-js adds
  defaults otherwise.
- Tabs inside a run: `new TextRun({ children: [new Tab(), "text"] })`, with `tabStops` on the paragraph.
- `ImageRun` needs `type` ("png"/"jpg") and `transformation` in pixels.
- `PageBreak` goes inside a `Paragraph`. Never put "\n" in text; make another paragraph.
- Bottom rules are paragraph `border.bottom`, never a one-row table or a "____" line.
- `keepNext` on headings; `cantSplit` on rows; `tableHeader` on header rows.
- Document metadata: pass `creator`, `lastModifiedBy`, `title`, `description`; docx-js otherwise writes
  "Un-named". app.xml stays empty; `scripts/set_metadata.py` fills Application and Company.
- All-caps is `allCaps: true` on the run; do not upper-case the string (search and copy break).
- The `Heading1..6` styles docx-js writes by default carry Word's blue (2E74B5). The builder redefines them from
  the spec (`styles.default.heading1..6`), so a heading in that blue means a block bypassed the spec.
