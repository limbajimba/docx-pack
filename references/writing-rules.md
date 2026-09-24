# Writing rules: what makes a document read as written by a person who knows the subject

Two sources feed this file: the house standard (top-down-communication, exec-handoff, the no-slop rules) and the
public catalogues of machine-writing tells (Wikipedia "Signs of AI writing", The Field Guide to AI Slop). The
lint script `scripts/lint_docx.py` checks the mechanical items; the judgement items are here for the writer.

## 1. Structure: the answer first, then the reasons, then the evidence

- Page 1 is the answer. A reader who stops after the first paragraph leaves with the verdict.
- Open with SCQA in four sentences or fewer: situation, complication, question (usually implied), answer.
- The governing thought is one sentence of 25 words or fewer. It goes in the verdict bar.
- Three or four Key Line points support it. One plural noun describes them all (reasons, risks, steps).
- Section headings are conclusions in full sentences, not labels. "Introduction", "Background", "Findings",
  "Conclusion" are labels. "The product is a read-only layer over the SIS" is a heading.
- Order every group by one rule: argument, time, structure or importance. A colleague should be able to say why
  point two follows point one.
- Method goes last, in one short paragraph or an appendix. Never narrate the order you worked in.
- Appendices carry the register: evidence tags, sources, dates, URLs. The body cites tags in brackets [F12].

## 2. Sentences: short, literal, specific

- One idea per sentence, around 20 words, with a verb. Short does not mean clipped; a sentence beats a label.
- Name the thing. "Thesis SM cloud margin", not "the comparator". "The deal thesis", not "the thesis".
- Put the number in the sentence and the source tag after it: "Domain registered 17 April 2026 [F20]."
- Drop hedging adverbs that carry no information (perhaps, arguably, somewhat, relatively). Keep a hedge only when
  the uncertainty is real, and then say what is uncertain.
- No metaphors. No "moat" unless the framework defines it. No "landscape", "journey", "navigate", "unlock".
- No paired-contrast flourishes: "X is real; Y is not", "not a bug but a feature", "it's not X, it's Y". State the
  fact and its consequence.
- No rule-of-three padding. Use the real number of items, even if it is two or five.
- No em dashes and no parentheticals in prose. Use commas, colons, full stops, or a new sentence.
- No filler openers or closers: "It is worth noting", "In today's", "In conclusion", "Overall", "Ultimately".
- Admit gaps in their own line ("Gaps: signed customer count; contract value."). A document that names what it
  could not find reads as researched; one that never does reads as generated.
- Argue against yourself once per finding ("Counter: ..."). Generated prose rarely does this unprompted.
- Vary paragraph length. Uniform three-sentence paragraphs are a tell.

## 3. Vocabulary to strike on sight

delve · tapestry · testament to · underscore · pivotal · crucial · vital role · plays a key role · landscape ·
in today's · fast-paced · ever-evolving · it's worth noting · in conclusion · to summarise · overall, · ultimately, ·
notably, · importantly, · furthermore · moreover · additionally · game-changer · cutting-edge · groundbreaking ·
vibrant · nestled · boasts · serves as · stands as · marks a · at its core · dive into · deep dive · unlock · harness ·
empower · elevate · streamline · seamless · robust · holistic · synergy · leverage (verb) · paradigm · realm ·
embark · foster · showcase · shed light · key takeaway · navigate · journey · transformative · comprehensive ·
multifaceted · nuanced · intricate · meticulous · a myriad of · plethora · indelible · resonate · stakeholders across

Replacements are plain verbs and nouns: "shows", "is", "has", "the market", "the sector", "customers".

## 4. Formatting tells

| Tell | Why it reads as generated | Do instead |
|---|---|---|
| Bullet that opens with a **bold label:** then text | The chatbot list pattern | A full sentence; if a table fits better, use a table |
| Walls of bullets | Bullets cannot carry an argument | Prose for reasoning; bullets only for parallel items, one sentence each |
| Emoji in headings or bullets | Never in business documents | None |
| Title Case Headings | Word defaults and model habit | Sentence case |
| Headings that are labels | Say nothing | Full-sentence conclusions |
| Heading levels skipped (1 to 3) | Careless outline | Consecutive levels |
| Horizontal rules between every section | Markdown habit | Spacing and heading rules from the spec |
| Bold sprinkled on random phrases | Emphasis by reflex | Bold only labels in tables and tile values |
| Tables for non-tabular content | Structure by reflex | Prose |
| Word default heading blue (2E74B5) and Calibri | Unstyled document | The spec's palette and typeface |
| "**", "#", backticks, [cite:], oaicite in text | Tool residue | Remove; build from a content file, not pasted chat |
| {{placeholder}}, TBD, TODO left in | Unfinished | Fill or delete before sending |

## 5. Metadata tells

Word writes creator, last-modified-by, company, application and timestamps. Generators leave "Un-named"
(docx-js), "python-docx" (python-docx) or blanks, and an empty app.xml. Run `scripts/set_metadata.py` before sending.

## 6. What a person-made document has that a generated one lacks

- Specific dated facts with sources, and a register that resolves every tag.
- A verdict that could be wrong, and a "what would prove this wrong" paragraph.
- Gaps named. Counters named.
- Numbers that agree everywhere they appear (tile, chart, table, prose). Check them against each other.
- The reader's own words quoted back, then judged ("They launched a chatbot": confirmed, Feb 2026).
- Uneven texture: a two-sentence paragraph next to a six-sentence one, a one-line finding next to a table.

## 7. Pre-send checks (the six house checks plus the tells)

1. The first sentence answers the reader's question.
2. The opener runs SCQA in four sentences or fewer.
3. Three or four Key Line points, one plural noun describes them all.
4. Each group argues one way, deduction or induction.
5. The order is deliberate: argument, time, structure or importance.
6. Headlines alone tell the whole story.
7. `python3 scripts/lint_docx.py out.docx --spec <spec>` shows no FAIL and every WARN is a deliberate choice.
8. Every page has been looked at (see `visual-review.md`).
9. Metadata set; file name is `<Subject>-<Doc type>-<YYYY-MM-DD>.docx`, no "final_v2".
