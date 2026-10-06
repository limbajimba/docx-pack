---
name: house-docx
description: Use when producing, restyling or reviewing a Word (.docx) deliverable that a reader will judge (memo, read-out, assessment, DD report, IC paper), when a document must follow a house or client template, when a draft reads as machine-written, or when a .docx needs a visual check before it is sent.
---

# House DOCX

A document that reads as written by a person who knows the subject is built in that order: the words first
(answer, reasons, evidence), the look from a style spec (never hand-typed formatting), then every page rendered
and looked at, then the mechanical tells linted out, then the metadata set. The exemplar is the September 2026
AI Defensibility assessment; its look is codified in `house/silvertree.style-spec.json` and its components in
`references/docx-js-recipes.md`.

Pack root: `~/Projects/docx-pack` (this file's directory). Run scripts from the pack root.

## The loop

1. **Write the content file first**, as blocks in JSON (`examples/acme-content.json` is the model). Apply
   top-down-communication: verdict sentence, SCQA basis, Key Line as section headings, findings with
   Counter and Gaps lines, evidence register last. Read `references/writing-rules.md` before drafting.
2. **Pick the build path** (`references/template-workflow.md` has the full table):
   house look -> `node scripts/build_docx.js --spec house/silvertree.style-spec.json --content c.json --out out.docx`;
   client template must stay as designed -> `python3 scripts/fill_template.py --template T.dotx --content c.json --out out.docx`;
   change an existing file in place -> the OOXML edit path.
3. **Chart, if the numbers need one**: `python3 scripts/chart_bars.py --spec <spec> --data d.json --out chart.png`,
   then an `image` block. Every number on a chart also appears in a table.
4. **Render and look**: `bash scripts/render_preview.sh out.docx preview/ 80`, then Read every page JPEG against
   `references/visual-review.md`. Heed the font WARNING: it means the preview, not the document, is wrong.
5. **Lint**: `python3 scripts/lint_docx.py out.docx --spec <spec>`. Zero FAIL; each WARN a deliberate choice.
6. **Metadata**: the spec build sets it from `spec.metadata`; the fill path needs `--creator "SilverTree Equity" --company "SilverTree Equity"`;
   any other file: `python3 scripts/set_metadata.py out.docx --creator ... --company ... --title ...`. Lint reports it when missing.
7. Fix content or spec (never the .docx by hand), rebuild from step 2, re-render. Two or three loops is normal.

## Content blocks (quick reference)

| Block | Purpose |
|---|---|
| `title_band` | navy band: kicker, title, date, right-hand lines (from `meta`) |
| `verdict` | one-sentence governing thought in the teal bar |
| `basis` | small muted paragraph: subject description, evidence basis, table notes |
| `kpis` | one row of tiles `{label, value, note, tone: bad/good, text_value}` |
| `image` | PNG with `width_cm`; optional caption |
| `h1` / `h2` (+`meta`) / `h3` | section rule heading / finding heading with right-aligned meta / sub-heading |
| `p`, `bullets`, `numbered` | prose (`**bold**`, `*italic*` inline), one-sentence list items |
| `snapshot` | two-column label/value table |
| `table` | `columns [{header,width,align,bold}]`, `rows` of strings or `{text,color,bold,align}`, `{group}` rows, `note`, `size: table_small` |
| `finding` | `code, title, meta, body, counter, gaps` composed from h2 + p + callouts; `counter`/`gaps` carry the sentence only, the builder adds the label |
| `callout`, `pagebreak`, `spacer` | Counter/Gaps style lines; page break; vertical space |
| `figure_grid` | charts side by side: `cells [{path, title, sources, note, span}]`, `cols`; used by the visual fact pack |

## Visual fact pack (landscape charts companion to a fact pack)

`python3 scripts/build_visual_pack.py --plan plan.json --out out.docx` renders a plan's panels with the chart
library in `scripts/viz/` (bar_line, multi_line, range_vs_actual, stacked_share, small_multiples, kpi_tiles,
timeline_lanes, dot_rank, confidence_grid, sankey, org_chart, logo_wall) on `house/silvertree-landscape.style-spec.json`.
Every chart returns its source tags and lowest confidence for the caption; the build fails on banned words and on
headline numbers not found in the cited facts, and drops empty panels. The per-deal data module and plan templates,
and the worked example, live with the sdd-pack skill (deal material stays out of this repo).

## New template

`python3 scripts/codify_template.py Their.docx --out specs/their/` writes `style-spec.json`, `STYLE.md` (with a
block-by-block outline of how the exemplar composes its components) and the logo. Assign the colour roles by
eye against the rendered pages, copy the house spec and replace values, build the example content with it, compare
page 1 to the exemplar. Details in `references/template-workflow.md`.

## Rules that are not negotiable

- The first sentence a reader sees is the answer. Headings are full-sentence conclusions in sentence case.
- No em dashes, no parentheticals, no metaphors, no "not X but Y", no bold-label bullets, no emoji, no filler
  transitions. Full list and replacements in `references/writing-rules.md`.
- One typeface, the spec's palette, red only for flagged items. A heading in Word's default blue (2E74B5) means
  a block bypassed the spec.
- Numbers agree across tile, chart, prose and appendix; every bracketed tag resolves to a register row.
- Never send a .docx whose pages have not been rendered and read. Never hand-edit formatting in the .docx.

## Common mistakes

| Mistake | Fix |
|---|---|
| Drafting in the builder script or in Word | Words live in the content JSON; the spec owns the look |
| Judging typography from a preview with a font WARNING | Add the alias in `scripts/fonts/aliases.conf`, re-render |
| A fourth or fifth colour "for emphasis" | Palette roles only; red is a status colour |
| Bullets that carry the argument | Prose paragraphs; bullets for parallel items, one sentence each |
| "Un-named" author, empty app.xml | `set_metadata.py` before sending |
| Template with no named styles fed to `fill_template.py` | It is a generated file, not a template; codify it and use the spec build |
| Sending the .docx with the working files | exec-handoff package: cover note, DOCX of record, deck, evidence pack |

## Files

`scripts/build_docx.js` (spec + content -> .docx) · `scripts/fill_template.py` (any .docx/.dotx template) ·
`scripts/codify_template.py` (template -> spec) · `scripts/chart_bars.py` · `scripts/render_preview.sh` ·
`scripts/lint_docx.py` · `scripts/set_metadata.py` · `house/` (SilverTree spec, logo, STYLE.md) ·
`examples/` (Acme worked example: content, chart data, built .docx, page previews) ·
`references/` (writing-rules, visual-review, docx-js-recipes, template-workflow).

Works with: top-down-communication (structure of every artefact), exec-handoff (what surrounds the DOCX),
the Anthropic docx skill (OOXML edits, tracked changes, comments), dataviz (charts beyond bars).
