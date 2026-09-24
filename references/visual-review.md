# Visual review: render every page and look at it before it leaves the machine

Word files cannot be judged from the XML. Render to PDF, rasterise each page, and read the images with the
Read tool. One pass per build; fix the spec or the content, rebuild, render again. Two or three loops is normal.

```bash
bash scripts/render_preview.sh out.docx preview/ 80      # -> preview/out-page-1.jpg ...
```

The script prints the page count, the JPEG paths, the fonts the document asks for and the fonts the PDF
embeds. **If it prints a WARNING, the preview typography is wrong**, not the document: LibreOffice substituted
a font. Add an alias in `scripts/fonts/aliases.conf` (Gill Sans MT -> Gill Sans, Calibri -> Carlito,
Cambria -> Caladea are in there) or install the font, then re-render before judging spacing or line breaks.
Word on the reader's machine will use the real font; metric-compatible aliases keep line breaks close.

## Page 1 (the page that gets read)

- Title band, verdict bar, basis lines, first heading and the scorecard tiles all fit above the fold of an A4
  page. If the chart pushes the snapshot table to page 2, that is acceptable; if the verdict is not on page 1,
  it is not.
- The verdict bar text is one sentence and does not wrap to three lines.
- Tiles: labels one or two lines, values on one line, notes two lines at most. A value that wraps means the
  tile is too narrow: cut the label or drop a tile.
- Chart: crisp at the printed size (render at 200 dpi, width in cm set in the content), labels not clipped,
  weakest item in the status colour, threshold line labelled inside the plot.
- Header logo not squashed (aspect ratio preserved), "STRICTLY CONFIDENTIAL" on the same baseline as the logo.
- Footer: short title | Strictly confidential | Firm on the left, "Page 1 of N" on the right, N correct.

## Every page

- No heading stranded at the bottom of a page with its body on the next (the builder sets keepNext; a heading
  followed by a table can still strand: add a one-line lead paragraph or move a page break).
- No table row split across pages (rows are cantSplit; check anyway for very long cells).
- Table header row repeats on the continuation page (tableHeader is set; confirm).
- No last page that is less than a quarter full. Tighten spacing or cut, do not pad.
- No single-line widows or orphans in body prose where they can be avoided with a small edit.
- Right-aligned meta on finding headings ("7.0 / 10 · weight 11% · coverage 100%") sits on one line; if it wraps,
  shorten the heading or the meta.
- Columns: numbers right-aligned, text left-aligned; no column so narrow that words break mid-word; no column so
  wide that the text is a ribbon. Widths are in the content JSON (DXA; 9638 is the full text width on A4 with
  2 cm margins).
- Zebra shading alternates without a double stripe across a group row.
- Red appears only on the items that are flagged (weakest area, N/E, FALSE). Teal only on group rows and the
  verdict. Anything else in colour is a mistake.
- Consistent gap between a section's last block and the next h1 (spacer after tables is in the spec).
- No empty paragraphs used as spacing; no bare horizontal rules.
- Long URLs in evidence tables break reasonably; shorten to the domain plus path if not.
- Hyphens, en dashes and minus signs used correctly in ranges and negatives ("5.5 to 6.9" is the house form).

## Whole document

- Page count matches the brief (a screen is 2 to 4 pages plus appendices; an IC memo is longer).
- The same number appears identically wherever it occurs: tile, chart, prose, appendix table.
- Every bracketed tag in the body resolves to a row in the evidence appendix.
- Headings read in sequence tell the story (the top-down test), and look the same weight at the same level.
- Open the .docx in Word or Pages once if it will be edited by the reader; check tracked changes are off and the
  comments pane is empty.

## What to change, and where

| Symptom | Change |
|---|---|
| Wrong font in preview only | `scripts/fonts/aliases.conf` |
| Colours, sizes, spacing, header, footer, table look | the style spec (`house/*.style-spec.json`) |
| Words, numbers, table widths, block order, page breaks | the content JSON |
| A component that does not exist yet | `scripts/build_docx.js` BLOCKS map, then add it to `docx-js-recipes.md` |
| Template's own styles wrong (fill path) | the template file; report the missing styles the script prints |
