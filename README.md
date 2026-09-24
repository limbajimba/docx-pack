# docx-pack

How we make Word documents that read as written by a person who knows the subject, and look like ours.
A skill for Claude Code plus the scripts it drives: build from a style spec, fill any template, codify a new
template, chart in the palette, render every page for a visual check, lint for machine-writing tells, set metadata.

The exemplar is the September 2026 AI Defensibility assessment (SilverTree Equity, A4, Gill Sans MT, navy and
teal). Its look is codified in `house/silvertree.style-spec.json`; its components are documented in
`references/docx-js-recipes.md`. No client content is in this pack; the worked example (Acme Scheduling) is invented.

## Quick start

```bash
git clone <this repo> ~/Projects/docx-pack && cd ~/Projects/docx-pack
bash install.sh                      # npm deps, python deps check, symlink the skill into ~/.claude/skills/house-docx
node scripts/build_docx.js --spec house/silvertree.style-spec.json --content examples/acme-content.json --out /tmp/acme.docx
bash scripts/render_preview.sh /tmp/acme.docx /tmp/acme-preview 80     # then look at the page JPEGs
python3 scripts/lint_docx.py /tmp/acme.docx --spec house/silvertree.style-spec.json
python3 scripts/set_metadata.py /tmp/acme.docx --creator "SilverTree Equity" --company "SilverTree Equity" --title "Acme Scheduling"
```

In Claude Code, the skill triggers on any .docx deliverable once installed. To make it a named house skill,
add to `~/.claude/CLAUDE.md`:

```
# house-docx
- **house-docx** (`~/.claude/skills/house-docx/SKILL.md`) - build, restyle or review Word deliverables: spec build, any-template fill, codify a template, render-and-look, lint for AI tells, metadata. Trigger: `/house-docx`, or apply automatically to any .docx deliverable.
```

## What is in the pack

| Path | What |
|---|---|
| `SKILL.md` | The skill: the loop, block reference, rules, common mistakes |
| `references/writing-rules.md` | Structure, sentence and vocabulary rules; formatting and metadata tells; pre-send checks |
| `references/visual-review.md` | The render-and-look checklist, page 1 and every page, and where to fix each symptom |
| `references/docx-js-recipes.md` | Every house component with its tokens, and the docx-js details that bite |
| `references/template-workflow.md` | Spec build vs fill template vs patch vs OOXML edit vs pandoc; codifying a template |
| `scripts/build_docx.js` | style spec + content JSON -> .docx (docx 9.7, Node 18+) |
| `scripts/fill_template.py` | any .docx/.dotx template + content JSON -> .docx, template styles kept (python-docx) |
| `scripts/codify_template.py` | .docx/.dotx -> style-spec.json + STYLE.md (with block outline) + logo |
| `scripts/chart_bars.py` | horizontal bar chart PNG in the spec palette (matplotlib) |
| `scripts/render_preview.sh` | .docx -> PDF -> page JPEGs, with font-substitution check and aliases |
| `scripts/lint_docx.py` | text, formatting and metadata tells; exit 1 on FAIL |
| `scripts/set_metadata.py` | creator, company, application, timestamps |
| `house/` | SilverTree spec, logo, STYLE.md |
| `examples/` | Acme worked example: content, chart data and PNG, built .docx, page previews |
| `tests/` | pytest for the codifier and the linter |

## Requirements

Node 18+ (`cd scripts && npm install`), Python 3.10+ with `python-docx`, `matplotlib`, `Pillow`, LibreOffice
(`soffice` on PATH or in /Applications), Poppler (`pdftoppm`, `pdffonts`, `pdfinfo`), pandoc (read path only).
Fonts: the preview maps Gill Sans MT to Apple's Gill Sans; on Linux add the font or an alias in
`scripts/fonts/aliases.conf`.

## Why these steps

A test on 24 September 2026: the same two-page brief given to a capable model with no pack produced a memo with 17
em dashes, Title Case headings, a bold "VERDICT:" label, Word's Calibri, US Letter, python-docx as the author and no
header or footer. The same brief through the pack (a second run of the same model, reading only SKILL.md) produced the house look on A4,
the verdict in the teal bar, full-sentence section headings, Counter and Gaps lines under each finding, a chart, a
14-row evidence register, and one lint WARN (a false positive on "marks a"). The difference is not the model; it is
the content-first order, the spec, the render-and-look loop and the lint.

## Adding a template

See `references/template-workflow.md`. Short form: codify, assign roles by eye, copy the house spec and replace
values, build the example content, compare page 1 to the exemplar, commit under `specs/<name>/`.
