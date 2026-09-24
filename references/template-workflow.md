# Template workflow: codify any template, then build with it

Three build paths and one edit path. Pick by who owns the look.

| Situation | Path | Command |
|---|---|---|
| House document, house look (default) | **Spec build**: tokens in a style spec, words in a content file, docx-js renders | `node scripts/build_docx.js --spec house/silvertree.style-spec.json --content c.json --out out.docx` |
| A firm or client template must stay exactly as designed (letterhead, cover, legal footer, their styles) | **Fill template**: python-docx opens the .docx/.dotx, keeps styles/header/footer/page setup, writes the same content blocks with the template's named styles | `python3 scripts/fill_template.py --template Their.dotx --content c.json --out out.docx` |
| A template with `{{placeholders}}` to swap and nothing else | **Patch**: docx-js `patchDocument` (v9), or `fill_template.py --keep-body --placeholders '{...}'` | see below |
| An existing document to change in place (a paragraph, a table row, tracked changes, comments) | **OOXML edit**: unzip, merge runs, edit `word/document.xml`, zip, validate | Anthropic docx skill scripts, see below |
| Markdown draft to a passable Word file in one command, no tables of note | **pandoc reference doc**: `pandoc draft.md --reference-doc=Their.docx -o out.docx` | styles come from the reference doc; header and footer are kept; sections cannot vary |

Whatever the path: render it, look at every page, lint it, set metadata. Those four steps never change.

## Codify a template into a spec (once per template)

1. Get an exemplar: the template itself, or better, a finished document the owner is proud of.
2. Run the codifier:
   ```bash
   python3 scripts/codify_template.py Their.docx --out specs/their/ --outline 80
   ```
   It writes `style-spec.json` (page, fonts, sizes, colours, header/footer text and images, styles, numbering,
   body statistics), `STYLE.md` (the same, readable, plus a block-by-block outline of the exemplar's first 80
   body blocks) and `media/` (header/footer images, i.e. the logo).
3. Render the exemplar (`render_preview.sh`) and read `STYLE.md` next to the page images. Assign the colour
   roles by eye: which hex is ink, muted, the accent for headings, the flag colour, the rule, the zebra fill.
   The codifier ranks candidates by frequency; it does not know what they mean.
4. Copy `house/silvertree.style-spec.json` to `specs/their/their.style-spec.json` and replace values with the
   codified ones. Keep the `components` block; adjust fills and borders to match the exemplar's outline
   (`STYLE.md` shows each table's fills, borders and cell margins, and each paragraph's run and spacing).
   Set `roles_checked_by_eye: true` only after step 3.
5. Build `examples/acme-content.json` with the new spec and compare page 1 against the exemplar side by side.
   Adjust until the two look like siblings. Two or three rounds is normal.
6. Commit the spec, the logo and a page-1 preview under `specs/their/`.

The block outline is the codification. It shows how the exemplar composes components (a title band as a two-cell
navy table, a verdict as a one-cell teal table, tiles as a five-cell table with a top border) so a new component
can be added to `build_docx.js` from the recipe rather than guessed.

## Fill path notes (python-docx)

- `.dotx` is accepted; the script rewrites the content type in a temporary copy.
- The template's body is cleared (except the section properties) unless `--keep-body`.
- Blocks map to named styles: Title, Subtitle, Heading 1-3, Normal, List Bullet, List Number, Intense Quote,
  Caption, and the template's first table style. The script prints every style it could not find; send that
  list to the template owner or add the styles in Word (Home > Styles > New Style) and save the template.
- `h3` maps to Heading 3; put an `h2` before it or the lint flags a heading-level skip.
- Placeholders `{{title}}`, `{{date}}`, `{{footer_title}}` in the template's header, footer or body are replaced
  from `meta`; pass more with `--placeholders`.
- Fancy components (title band, tiles) degrade to Title/Subtitle and a plain table. That is the point: the
  template owner's look wins.

## Patch path notes (docx-js patchDocument)

```js
const { patchDocument, PatchType, TextRun, Paragraph } = require("docx");
const buf = await patchDocument({ outputType: "nodebuffer", data: fs.readFileSync("Their.docx"),
  keepOriginalStyles: true,
  patches: { date: { type: PatchType.PARAGRAPH, children: [new TextRun("24 September 2026")] },
             body: { type: PatchType.DOCUMENT, children: [new Paragraph("..."), /* tables too */] } } });
```
Placeholders are `{{name}}` in the template. `PARAGRAPH` patches replace inline text; `DOCUMENT` patches replace
a whole paragraph with blocks. Word splits placeholder text across runs when it has been edited; if a patch does
not apply, open the template, retype the placeholder in one go, save.

## OOXML edit path (Anthropic docx skill)

The Anthropic `docx` skill ships the scripts for in-place edits; it is installed under
`~/.claude/skills/synced/*/docx/` on this machine and published at github.com/anthropics/skills (skills/docx).
```bash
unzip -q in.docx -d unpacked/ && find unpacked -type l -delete
python <skill>/scripts/merge_runs.py unpacked/          # make phrases findable as one run
# edit unpacked/word/document.xml; do not pretty-print
(cd unpacked && rm -f ../out.docx && zip -Xr ../out.docx .)
python <skill>/scripts/office/validate.py out.docx --original in.docx   # XSD; --auto-repair
python <skill>/scripts/comment.py unpacked/ "text"       # Word comments
python <skill>/scripts/accept_changes.py in.docx out.docx
```
Tracked changes need `<w:ins>`/`<w:del>` with author and date; validate with `--author`. Use this path for
redlines a counterparty will see; use the spec build for anything you author.

## pandoc path notes

`pandoc in.md --reference-doc=ref.docx -o out.docx`. Body styles (Normal, Heading 1-n, Table, Caption,
Compact, Source Code) come from the reference file; its header, footer and page setup are kept; a "Different
First Page" header works. Limits: no per-section headers, no coloured table headers or tiles, no fine control of
widths. Good for a quick internal note; not for a document of record.

## Telling a template from a generated file

Run the codifier and read `paragraph_styles_used` in `STYLE.md`. A real template shows Normal, Heading 1-3,
List Bullet, Title, Caption and a table style in use. A generated exemplar (docx-js, python-docx) shows one or
two styles and hundreds of direct-formatted runs. Fill the first with `fill_template.py`; codify the second into a
spec and use `build_docx.js`. If an old deliverable is used as a template anyway, its header and footer text
survive unchanged; replace them with `--placeholders '{"Old Title — Old Subtitle": "New title"}'`.
