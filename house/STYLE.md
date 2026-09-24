# Style spec: silvertree

Source: the September 2026 AI Defensibility exemplar, reproduced here through `examples/acme-memo.docx` (invented content). Roles are assigned in `silvertree.style-spec.json`.

## Page

- width_dxa: `11906`
- height_dxa: `16838`
- orientation: `portrait`
- size: `A4`
- margins_dxa: `{'top': 1250, 'right': 1134, 'bottom': 1100, 'left': 1134, 'header': 500, 'footer': 500, 'gutter': 0}`
- margins_cm: `{'top': 2.2, 'right': 2.0, 'bottom': 1.94, 'left': 2.0, 'header': 0.88, 'footer': 0.88, 'gutter': 0.0}`
- text_width_dxa: `9638`
- header_parts: `['default']`
- footer_parts: `['default']`

## Defaults (docDefaults)

`{'font': 'Gill Sans MT', 'pt': 10.0, 'color': '2E3232'}`

## Inferred roles

- font_body: `Gill Sans MT`
- size_body_pt: `10.0`
- ink: `2E3232`
- muted: `646A7A`
- accent_candidates: `['132246', 'C0392B', '0B4E6F']`
- fill_candidates: `['F2F2F2', '132246', '0B4E6F']`
- rule_candidates: `['FFFFFF', 'E9EBEB', '132246']`

## Body statistics

- paragraphs: `43`
- tables: `6`
- images: `1`
- fonts: `[('Gill Sans MT', 156)]`
- sizes_pt: `[(7.5, 65), (8.0, 33), (10.0, 18), (8.5, 16), (12.0, 7), (9.0, 6), (7.0, 5), (15.0, 4), (17.0, 1), (10.5, 1)]`
- text_colors: `[('2E3232', 81), ('132246', 24), ('646A7A', 21), ('FFFFFF', 19), ('C0392B', 9), ('0B4E6F', 2)]`
- fills: `[('F2F2F2', 35), ('132246', 13), ('0B4E6F', 3)]`
- border_colors: `[('FFFFFF', 349), ('E9EBEB', 81), ('132246', 12)]`
- paragraph_styles_used: `[('ListParagraph', 3)]`

## Named styles that carry formatting

- **Title** (paragraph): `{'pt': 28.0}`
- **Heading1** (paragraph): `{'pt': 16.0, 'color': '2E74B5'}`
- **Heading2** (paragraph): `{'pt': 13.0, 'color': '2E74B5'}`
- **Heading3** (paragraph): `{'pt': 12.0, 'color': '1F4D78'}`
- **Heading4** (paragraph): `{'color': '2E74B5', 'italic': True}`
- **Heading5** (paragraph): `{'color': '2E74B5'}`
- **Heading6** (paragraph): `{'color': '1F4D78'}`
- **Strong** (paragraph): `{'bold': True}`
- **Hyperlink** (character): `{'color': '0563C1', 'underline': 'single'}`
- **FootnoteText** (paragraph): `{'pt': 10.0, 'space_after': 0, 'space_line': 240}`
- **FootnoteTextChar** (character): `{'pt': 10.0}`
- **EndnoteText** (paragraph): `{'pt': 10.0, 'space_after': 0, 'space_line': 240}`
- **EndnoteTextChar** (character): `{'pt': 10.0}`

## Header / footer

- header `word/header1.xml`
  - text: “STRICTLY CONFIDENTIAL” fields=[] run={'font': 'Gill Sans MT', 'pt': 7.5, 'color': '646A7A', 'italic': True, 'caps': True} tabs=['right@9638'] borders={'bottom': {'color': 'E9EBEB', 'sz': '4', 'space': '4'}}
  - image: media/9682b94ebf509a92f123298dc811e8ef0fe26e91.png size_cm={'w': 2.86, 'h': 1.06}
- footer `word/footer1.xml`
  - text: “Acme Scheduling — AI Defensibility Assessment  |  Strictly confidential  |  SilverTree EquityPage  of” fields=['PAGE', 'NUMPAGES'] run={'font': 'Gill Sans MT', 'pt': 8.0, 'color': '646A7A', 'italic': True} tabs=['right@9638'] borders={'top': {'color': 'E9EBEB', 'sz': '4', 'space': '4'}}

## Bullets

- `{'format': 'bullet', 'text': '●', 'indent': {'left': '720', 'hanging': '360'}}`
- `{'format': 'bullet', 'text': '•', 'indent': {'left': '540', 'hanging': '260'}}`
- `{'format': 'decimal', 'text': '%1.', 'indent': {'left': '540', 'hanging': '260'}}`

## Block outline (first 40 of 49 body blocks)

Read this top to bottom to see how the exemplar composes its components (title band, verdict bar, tiles, headings, tables).

  0. TABLE rows=1 cols=2 grid=['7000', '2638'] fills={'132246': 2} borders={'top': 'FFFFFF', 'left': 'FFFFFF', 'bottom': 'FFFFFF', 'right': 'FFFFFF', 'insideH': 'FFFFFF', 'insideV': 'FFFFFF'} margins={'top': '200', 'left': '220', 'bottom': '200', 'right': '90'}
      first row: “AI Defensibility Assessment  ·  Framework v2.0 structure  ·  worked example | Acme Scheduling | 24 September 2026 | Public-record screen | Not a portfolio compa”
      row fills: ['132246', '132246']
  1. P {} {'space_before': 0, 'space_after': 60, 'space_line': 276} 
  2. TABLE rows=1 cols=1 grid=['9638'] fills={'0B4E6F': 1} borders={'top': 'FFFFFF', 'left': 'FFFFFF', 'bottom': 'FFFFFF', 'right': 'FFFFFF', 'insideH': 'FFFFFF', 'insideV': 'FFFFFF'} margins={'top': '130', 'left': '220', 'bottom': '130', 'right': '220'}
      first row: “Acme Scheduling scores as a feature, not a company.”
      row fills: ['0B4E6F']
  3. P {} {'space_before': 0, 'space_after': 80, 'space_line': 276} 
  4. P {'font': 'Gill Sans MT', 'pt': 7.5, 'color': '646A7A'} {'space_before': 0, 'space_after': 80, 'space_line': 240} 
      “Public course schedule and student planner for US colleges, fed by a one-way SQL export from the institution's”
  5. P {'font': 'Gill Sans MT', 'pt': 7.5, 'color': '646A7A'} {'space_before': 0, 'space_after': 80, 'space_line': 240} 
      “Basis: 45 dated, sourced public facts gathered on 22 September 2026 (evidence log in Appendix B); scored again”
  6. P {'font': 'Gill Sans MT', 'pt': 12.0, 'color': '132246', 'bold': True} {'space_before': 320, 'space_after': 140, 'space_line': 240} borders=bottom:132246
      “Scorecard”
  7. TABLE rows=1 cols=5 grid=['1927', '1927', '1927', '1927', '1930'] fills={'F2F2F2': 5} borders={'top': 'FFFFFF', 'left': 'FFFFFF', 'bottom': 'FFFFFF', 'right': 'FFFFFF', 'insideH': 'FFFFFF', 'insideV': 'FFFFFF'} margins={'top': '90', 'left': '120', 'bottom': '110', 'right': '100'}
      first row: “Structural defensibility | 4.9 | Eroding | AI execution | 3.1 | below 7.0 threshold | Quadrant | Neither | threshold 7.0 on both axes | Weakest evidenced area |”
      row fills: ['F2F2F2', 'F2F2F2', 'F2F2F2', 'F2F2F2', 'F2F2F2']
  8. P {} {'space_before': 0, 'space_after': 100, 'space_line': 276} 
  9. P {} {'space_before': 0, 'space_after': 60} images=1
 10. P {'font': 'Gill Sans MT', 'pt': 7.5, 'color': '646A7A'} {'space_before': 0, 'space_after': 80, 'space_line': 240} 
      “Weighted geometric mean 4.8; arithmetic minus geometric gap 0.2 (a wide gap means the weakness sits in one pla”
 11. P {'font': 'Gill Sans MT', 'pt': 12.0, 'color': '132246', 'bold': True} {'space_before': 320, 'space_after': 140, 'space_line': 240} borders=bottom:132246
      “Company snapshot”
 12. TABLE rows=8 cols=2 grid=['2400', '7238'] fills={'F2F2F2': 6} borders={'top': 'FFFFFF', 'left': 'FFFFFF', 'bottom': 'FFFFFF', 'right': 'FFFFFF', 'insideH': 'FFFFFF', 'insideV': 'FFFFFF'} margins={'top': '45', 'left': '80', 'bottom': '45', 'right': '80'}
      first row: “Legal entity | Not disclosed; no registry, Crunchbase or LinkedIn record”
      row fills: [None, None]
      row fills: ['F2F2F2', 'F2F2F2']
      row fills: [None, None]
      row fills: ['F2F2F2', 'F2F2F2']
 13. P {} {'space_before': 0, 'space_after': 100, 'space_line': 276} 
 14. P {'font': 'Gill Sans MT', 'pt': 12.0, 'color': '132246', 'bold': True} {'space_before': 320, 'space_after': 140, 'space_line': 240} borders=bottom:132246
      “Reading”
 15. P {'font': 'Gill Sans MT', 'pt': 10.0, 'color': '2E3232'} {'space_before': 0, 'space_after': 140, 'space_line': 276} 
      “Acme Scheduling scores as a feature, not a company. It is a read-only presentation and analytics layer over th”
 16. P {'font': 'Gill Sans MT', 'pt': 10.0, 'color': '2E3232'} {'space_before': 0, 'space_after': 140, 'space_line': 276} 
      “The company itself is barely visible. The domain is five months old [F20]; three of four logos on the site are”
 17. P {'font': 'Gill Sans MT', 'pt': 10.0, 'color': '132246', 'bold': True} {'space_before': 120, 'space_after': 80, 'space_line': 276} 
      “What would prove this wrong”
 18. P {'font': 'Gill Sans MT', 'pt': 10.0, 'color': '2E3232'} {'space_before': 0, 'space_after': 140, 'space_line': 276} 
      “A very young product should not be expected to have renewals, certifications or reviews; the framework measure”
 19. P {'font': 'Gill Sans MT', 'pt': 10.0, 'color': '2E3232'} {'space_before': 0, 'space_after': 140, 'space_line': 276} 
      “Flat institutional pricing with a near-zero cost base is a workable micro-SaaS model; the framework's low scor”
 20. P {'font': 'Gill Sans MT', 'pt': 10.0, 'color': '132246', 'bold': True} {'space_before': 120, 'space_after': 80, 'space_line': 276} 
      “What moves the score”
 21. P {'font': 'Gill Sans MT', 'pt': 10.0, 'color': '2E3232'} {'space_before': 0, 'space_after': 140, 'space_line': 276} 
      “A registration hand-off or write-back into Banner, Colleague or Elements would move A3.1 from 1 to 5 and A2.5 ”
 22. P {'font': 'Gill Sans MT', 'pt': 12.0, 'color': '132246', 'bold': True} {'space_before': 320, 'space_after': 140, 'space_line': 240} borders=bottom:132246
      “Area findings”
 23. P {'font': 'Gill Sans MT', 'pt': 7.5, 'color': '646A7A'} {'space_before': 0, 'space_after': 80, 'space_line': 240} 
      “Each area shows its score out of 10, its weight in the headline and the share of its driver weight that public”
 24. P {'font': 'Gill Sans MT', 'pt': 10.0, 'color': '132246', 'bold': True} {'space_before': 200, 'space_after': 60, 'space_line': 240} borders=bottom:E9EBEB
      “A1  Workflow & user replacement by AI agents7.0 / 10   ·   weight 11%   ·   coverage 100%”
 25. P {'font': 'Gill Sans MT', 'pt': 10.0, 'color': '2E3232'} {'space_before': 0, 'space_after': 60, 'space_line': 276} 
      “Users are the registrar's office, academic advisors, leadership viewers and students [F27, F42, F43]. Tiers ca”
 26. P {'font': 'Gill Sans MT', 'pt': 9.0, 'color': 'C0392B', 'bold': True} {'space_before': 0, 'space_after': 40, 'space_line': 276} 
      “Counter: Students do not use agents to browse a schedule; the public page has a user population no automation ”
 27. P {'font': 'Gill Sans MT', 'pt': 8.0, 'color': '646A7A', 'bold': True} {'space_before': 0, 'space_after': 80, 'space_line': 276} 
      “Gaps: Registrar and scheduling headcount trends; seats in use at the named college.”
 28. P {'font': 'Gill Sans MT', 'pt': 10.0, 'color': '132246', 'bold': True} {'space_before': 200, 'space_after': 60, 'space_line': 240} borders=bottom:E9EBEB
      “B1  Data moat3.8 / 10   ·   weight 12%   ·   coverage 75%”
 29. P {'font': 'Gill Sans MT', 'pt': 10.0, 'color': '2E3232'} {'space_before': 0, 'space_after': 60, 'space_line': 276} 
      “First-party behavioural data (searches, filters, adds, conflicts) per institution surfaced as a Seat Demand In”
 30. P {'font': 'Gill Sans MT', 'pt': 9.0, 'color': 'C0392B', 'bold': True} {'space_before': 0, 'space_after': 40, 'space_line': 276} 
      “Counter: Demand signals across many colleges would be novel; no SIS vendor publishes them.”
 31. P {'font': 'Gill Sans MT', 'pt': 8.0, 'color': '646A7A', 'bold': True} {'space_before': 0, 'space_after': 80, 'space_line': 276} 
      “Gaps: Data-rights clauses; anonymisation; retention.”
 32. P {'font': 'Gill Sans MT', 'pt': 10.0, 'color': '132246', 'bold': True} {'space_before': 200, 'space_after': 60, 'space_line': 240} borders=bottom:E9EBEB
      “C3  Unit economics & inference margin8.7 / 10   ·   weight 5%   ·   coverage 78%”
 33. P {'font': 'Gill Sans MT', 'pt': 10.0, 'color': '2E3232'} {'space_before': 0, 'space_after': 60, 'space_line': 276} 
      “Serverless edge hosting and a static marketing site [F23, F25, F34]; no AI, so no inference cost; onboarding i”
 34. P {'font': 'Gill Sans MT', 'pt': 9.0, 'color': 'C0392B', 'bold': True} {'space_before': 0, 'space_after': 40, 'space_line': 276} 
      “Counter: A near-zero cost base is a property of stage as much as of design; a real SIS integration would add s”
 35. P {'font': 'Gill Sans MT', 'pt': 8.0, 'color': '646A7A', 'bold': True} {'space_before': 0, 'space_after': 80, 'space_line': 276} 
      “Gaps: Hosting bill; support headcount; contract value at the named college.”
 36. P {'font': 'Gill Sans MT', 'pt': 12.0, 'color': '132246', 'bold': True} {'space_before': 320, 'space_after': 140, 'space_line': 240} borders=bottom:132246
      “Diligence questions for management”
 37. P {'font': 'Gill Sans MT', 'pt': 10.0, 'color': '2E3232'} {'space_before': 0, 'space_after': 60, 'space_line': 276} bullet style=ListParagraph
      “Which institutions are live on their own domain today, and which of the four logos are contracted customers?”
 38. P {'font': 'Gill Sans MT', 'pt': 10.0, 'color': '2E3232'} {'space_before': 0, 'space_after': 60, 'space_line': 276} bullet style=ListParagraph
      “Is a registration write-back into any SIS on the roadmap, and has any customer asked for it?”
 39. P {'font': 'Gill Sans MT', 'pt': 10.0, 'color': '2E3232'} {'space_before': 0, 'space_after': 60, 'space_line': 276} bullet style=ListParagraph
      “What compliance evidence (VPAT, HECVAT, SOC 2) exists or is in progress, and who owns it?”
