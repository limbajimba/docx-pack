#!/usr/bin/env python3
"""Lint a .docx for the tells that mark a document as machine-written, and for house-style slips.

Text tells (Wikipedia "Signs of AI writing", The Field Guide to AI Slop, house no-slop rules):
em dashes, AI vocabulary, "not X but Y" parallelisms, bold-lead bullets, bullet walls, emoji,
title-case headings, label headings, hedging adverbs, filler openers, markdown residue, placeholders.
Formatting tells: Word-default heading blue, mixed fonts, manual bullets, stacked empty paragraphs,
overuse of bold. Metadata tells: "Un-named" author, empty app.xml.

Usage:
  python3 lint_docx.py report.docx [--spec style-spec.json] [--strict] [--json] [--max-examples 5]
Exit 1 when any FAIL (with --strict, any WARN too).
"""
import argparse, collections, json, os, re, statistics, sys, zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from codify_template import NS, q, run_props, para_props, attr  # noqa: E402

AI_WORDS = r"""delve|delves|delving|tapestry|testament to|underscores?|underscoring|pivotal|crucial|vital role|
plays a (?:key|crucial|vital|central) role|landscape of|in today's|fast-paced|ever-evolving|it'?s worth noting|
it is (?:important|worth) (?:to note|noting)|in conclusion|to summari[sz]e|in summary|overall,|ultimately,|notably,|
importantly,|furthermore|moreover|additionally|game[- ]changer|cutting[- ]edge|groundbreaking|vibrant|nestled|
boasts?|serves? as|stands? as|marks? a|at its core|dive into|deep[- ]dive|unlocks?|harness(?:es|ing)?|empowers?|
elevates?|streamlines?|seamless(?:ly)?|robust|holistic|synergy|synergies|leverag(?:e|es|ing)|paradigm|realm|
embark|fosters?|showcas(?:e|es|ing)|shed light|key takeaways?|navigat(?:e|es|ing) the|journey|transformative|
comprehensive|multifaceted|nuanced|intricate|meticulous(?:ly)?|a myriad of|plethora|indelible|resonates?|
in the realm of|as an ai|knowledge cutoff|i hope this helps|let['’]s|stakeholders? across""".replace("\n", "")
AI_RE = re.compile(r"\b(?:" + AI_WORDS + r")\b", re.I)
NOT_BUT_RE = re.compile(r"\bnot (?:just |only |merely |simply )?[^.;:]{2,60}?,? (?:but(?: also| rather)?|it'?s|it is|rather)\b", re.I)
PAIRED_RE = re.compile(r"\b(?:is|are) [^;.]{1,40}; [^;.]{1,40} (?:is|are) not\b", re.I)
HEDGE_RE = re.compile(r"\b(?:perhaps|arguably|somewhat|relatively|fairly|quite|rather(?! than)|possibly|potentially|may well|could possibly|seems? to|appears? to|might)\b", re.I)
OPENER_RE = re.compile(r"^(?:the purpose of this (?:document|memo|report|note)|this (?:document|memo|report|note|paper) (?:sets out|provides|outlines|summari[sz]es|aims|is intended)|in this (?:document|memo|report))", re.I)
PLACEHOLDER_RE = re.compile(r"\{\{[^}]*\}\}|\[(?:INSERT|TBD|TODO|PLACEHOLDER|NAME|DATE)[^\]]*\]|\bTODO\b|\bTBD\b|lorem ipsum|XXX+", re.I)
MARKDOWN_RE = re.compile(r"\*\*[^*]+\*\*|^#{1,6} |`[^`]+`|^\s*[-*] |\[cite:|oaicite|turn\d+search\d+|【\d+", re.I | re.M)
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F900-\U0001F9FF✅❌⭐‼⁉]")
MANUAL_BULLET_RE = re.compile(r"^\s*[•●◦▪‣\-–—*]\s+")
LABEL_HEADINGS = {"introduction", "background", "overview", "findings", "conclusion", "conclusions", "summary",
                  "executive summary", "recommendations", "analysis", "discussion", "context", "next steps", "key findings"}
WORD_DEFAULT_HEADING_COLORS = {"2E74B5", "1F4D78", "2F5496", "1F3763", "0F4761", "156082"}
DEFAULT_FONTS = {"Calibri", "Aptos", "Times New Roman", "Cambria", "Arial"}


class Para:
    __slots__ = ("idx", "text", "style", "pp", "runs", "in_table", "is_list", "is_heading", "level", "bold_chars", "chars", "part")

    def __init__(self, idx, p, in_table, part="body"):
        self.idx, self.in_table, self.part = idx, in_table, part
        self.pp = para_props(p.find("w:pPr", NS))
        self.style = self.pp.get("style", "") or ""
        self.runs = []
        self.bold_chars = self.chars = 0
        for r in p.findall("w:r", NS):
            rp = run_props(r.find("w:rPr", NS))
            t = "".join(x.text or "" for x in r.iter(q("w:t")))
            if not t:
                continue
            self.runs.append((rp, t))
            self.chars += len(t)
            if rp.get("bold"):
                self.bold_chars += len(t)
        self.text = "".join(t for _, t in self.runs)
        self.is_list = bool(self.pp.get("numbered")) or self.style.lower().startswith("list")
        m = re.match(r"heading(\d)", self.style.lower())
        self.level = int(m.group(1)) if m else None
        first = self.runs[0][0] if self.runs else {}
        big = (first.get("pt") or 0) >= 11.5 and len(self.text) < 90 and not in_table
        self.is_heading = bool(m) or (big and (first.get("bold") or self.pp.get("borders")))


def load(path):
    z = zipfile.ZipFile(path)
    doc = ET.fromstring(z.read("word/document.xml"))
    body = doc.find("w:body", NS)
    paras, idx = [], 0
    for el in body:
        if el.tag == q("w:p"):
            paras.append(Para(idx, el, False)); idx += 1
        elif el.tag == q("w:tbl"):
            for p in el.iter(q("w:p")):
                paras.append(Para(idx, p, True)); idx += 1
    hf = []
    for n in z.namelist():
        if re.match(r"word/(header|footer)\d*\.xml", n):
            root = ET.fromstring(z.read(n))
            for p in root.iter(q("w:p")):
                hf.append(Para(-1, p, False, part=n))
    core = ET.fromstring(z.read("docProps/core.xml")) if "docProps/core.xml" in z.namelist() else None
    app = ET.fromstring(z.read("docProps/app.xml")) if "docProps/app.xml" in z.namelist() else None
    styles = ET.fromstring(z.read("word/styles.xml")) if "word/styles.xml" in z.namelist() else None
    return paras, hf, core, app, styles


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9“\"'(])", text) if len(s.split()) >= 3]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docx"); ap.add_argument("--spec"); ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true"); ap.add_argument("--max-examples", type=int, default=5)
    a = ap.parse_args()
    spec = json.load(open(a.spec)) if a.spec else None
    paras, hf, core, app, styles = load(a.docx)
    body = [p for p in paras if p.text.strip()]
    prose = [p for p in body if not p.in_table and not p.is_heading]
    findings = []

    def add(sev, code, msg, examples=None, count=None):
        findings.append({"severity": sev, "code": code, "message": msg, "count": count if count is not None else (len(examples) if examples else 0),
                         "examples": [e if isinstance(e, str) else f"¶{e.idx}: {e.text[:110]}" for e in (examples or [])][: a.max_examples]})

    # ---- text tells
    em = [p for p in prose if "—" in p.text]
    if em: add("WARN", "em-dash", f"em dashes in body prose ({sum(p.text.count('—') for p in em)}); house style uses commas, colons or full stops", em)
    ai = [(p, m.group(0)) for p in body for m in AI_RE.finditer(p.text)]
    if ai:
        c = collections.Counter(m.lower() for _, m in ai)
        add("WARN", "ai-vocabulary", f"AI-flavoured vocabulary ({len(ai)}): " + ", ".join(f"{k} ×{v}" for k, v in c.most_common(8)), [p for p, _ in ai])
    nb = [p for p in body if NOT_BUT_RE.search(p.text)]
    if nb: add("WARN", "not-x-but-y", "negative parallelism ('not X but Y', 'it's not X, it's Y'); state the fact and its consequence instead", nb)
    pr = [p for p in body if PAIRED_RE.search(p.text)]
    if pr: add("WARN", "paired-contrast", "paired-contrast flourish ('X is real; Y is not'); replace with the fact", pr)
    emo = [p for p in body + hf if EMOJI_RE.search(p.text)]
    if emo: add("FAIL", "emoji", "emoji or pictographs in a business document", emo)
    ph = [p for p in body + hf if PLACEHOLDER_RE.search(p.text)]
    if ph: add("FAIL", "placeholder", "unfilled placeholder or TODO text", ph)
    md = [p for p in body if MARKDOWN_RE.search(p.text)]
    if md: add("FAIL", "markdown-residue", "markdown or tool markup left in text (**, #, `, [cite:, oaicite)", md)
    mb = [p for p in body if MANUAL_BULLET_RE.match(p.text) and not p.is_list]
    if mb: add("FAIL", "manual-bullets", "bullet characters typed as text instead of a list style", mb)
    bullets = [p for p in body if p.is_list]
    if bullets:
        lead = [p for p in bullets if p.runs and p.runs[0][0].get("bold") and re.search(r"[:\-–—]\s*$", p.runs[0][1].strip() + " ") or (p.runs and p.runs[0][0].get("bold") and ":" in p.runs[0][1][:60])]
        if len(lead) / len(bullets) > 0.5 and len(lead) >= 3:
            add("WARN", "bold-lead-bullets", f"{len(lead)} of {len(bullets)} bullets open with a bold label and colon (the chatbot list pattern); write full sentences", lead)
        share = len(bullets) / max(1, len([p for p in body if not p.in_table]))
        if share > 0.45 and len(bullets) >= 8:
            add("WARN", "bullet-wall", f"{share:.0%} of body paragraphs are list items; prose carries argument better than stacked bullets", bullets[:5])
        long_b = [p for p in bullets if len(sentences(p.text)) >= 2 and len(p.text) > 160]
        if long_b: add("INFO", "multi-sentence-bullets", "bullets with two or more sentences; house rule is one sentence per bullet", long_b)
    heads = [p for p in body if p.is_heading]
    def title_case(t):
        ws = [w for w in re.sub(r"[·:|]", " ", t).split()[1:] if w.isalpha() and len(w) > 1]
        return len(ws) >= 3 and sum(w[:1].isupper() for w in ws) / len(ws) > 0.7
    tc = [p for p in heads if title_case(p.text)]
    if tc: add("WARN", "title-case-headings", "Title Case headings; house style is sentence case", tc)
    lab = [p for p in heads if re.sub(r"[\d.\s·:]+", " ", p.text).strip().lower() in LABEL_HEADINGS]
    if lab: add("INFO", "label-headings", "headings that are labels (Introduction, Findings, Conclusion); top-down style makes each heading a full-sentence conclusion", lab)
    if heads:
        levels = [p.level for p in heads if p.level]
        skips = [heads[i] for i in range(1, len(levels)) if levels[i] - levels[i - 1] > 1]
        if skips: add("WARN", "heading-level-skip", "heading levels skipped (e.g. Heading 1 to Heading 3)", skips)
    hedges = [(p, m.group(0)) for p in prose for m in HEDGE_RE.finditer(p.text)]
    if len(hedges) >= 3:
        c = collections.Counter(m.lower() for _, m in hedges)
        add("INFO", "hedging", f"hedging adverbs ({len(hedges)}): " + ", ".join(f"{k} ×{v}" for k, v in c.most_common(6)) + "; keep only those carrying real uncertainty", [p for p, _ in hedges])
    if prose and OPENER_RE.match(prose[0].text.strip()):
        add("WARN", "purpose-opener", "first body paragraph announces the document instead of giving the answer", [prose[0]])
    if heads and re.sub(r"[\d.\s]+", "", heads[0].text).strip().lower() in ("introduction", "background", "context"):
        add("WARN", "background-first", "first heading is Introduction/Background; the answer goes first", [heads[0]])
    sents = [s for p in prose for s in sentences(p.text)]
    if len(sents) >= 12:
        lens = [len(s.split()) for s in sents]
        sd = statistics.pstdev(lens); mean = statistics.mean(lens)
        if sd < 5 and 14 <= mean <= 28:
            add("INFO", "monotone-rhythm", f"sentence lengths barely vary (mean {mean:.0f} words, sd {sd:.1f}); vary length or the prose reads as generated", [])
        longs = [s for s in sents if len(s.split()) > 40]
        if len(longs) >= 3: add("INFO", "long-sentences", f"{len(longs)} sentences over 40 words", [s[:110] for s in longs])
    tri = [p for p in prose if len(re.findall(r"\b\w+, \w+,? and \w+\b", p.text)) >= 2]
    if len(tri) >= 3: add("INFO", "rule-of-three", "several paragraphs lean on three-item lists (rule of three); use the real number of items", tri)

    # ---- formatting tells
    total_chars = sum(p.chars for p in prose); bold_chars = sum(p.bold_chars for p in prose)
    if total_chars and bold_chars / total_chars > 0.08:
        add("WARN", "bold-overuse", f"{bold_chars / total_chars:.0%} of body prose is bold; reserve bold for the few words that need it", [p for p in prose if p.bold_chars][:5])
    fonts = collections.Counter(rp.get("font") for p in body for rp, _ in p.runs if rp.get("font"))
    if styles is not None:
        rd = styles.find("w:docDefaults/w:rPrDefault/w:rPr/w:rFonts", NS)
        if rd is not None and attr(rd, "w:ascii"): fonts[attr(rd, "w:ascii")] += 1
    if len(fonts) > 2: add("WARN", "mixed-fonts", "more than two typefaces in the body: " + ", ".join(f"{k} ×{v}" for k, v in fonts.most_common()), [])
    if spec and fonts and spec["font"]["body"] not in fonts:
        add("WARN", "font-off-spec", f"spec font {spec['font']['body']} not used; found " + ", ".join(fonts), [])
    if not spec and fonts and set(fonts) <= DEFAULT_FONTS:
        add("INFO", "default-font", "only Word default typefaces used (" + ", ".join(fonts) + "); fine, but a house typeface reads as designed", [])
    hcols = collections.Counter(rp.get("color") for p in heads for rp, _ in p.runs if rp.get("color"))
    if styles is not None:
        for s in styles.findall("w:style", NS):
            if (attr(s, "w:styleId") or "").lower().startswith("heading"):
                c = s.find("w:rPr/w:color", NS)
                if c is not None and any(p.style == attr(s, "w:styleId") for p in heads): hcols[attr(c, "w:val")] += 1
    wd = {c for c in hcols if c and c.upper() in WORD_DEFAULT_HEADING_COLORS}
    if wd: add("WARN" if spec else "INFO", "word-default-heading-colour", "headings use Word's default theme blue (" + ", ".join(wd) + "), the mark of an unstyled document", [])
    empties = 0; runs_of_empties = []
    for p in paras:
        if not p.in_table and not p.text.strip() and not p.pp.get("borders"):
            empties += 1
        else:
            if empties >= 2: runs_of_empties.append(empties)
            empties = 0
    if runs_of_empties: add("INFO", "empty-paragraph-spacing", f"{len(runs_of_empties)} places use stacked empty paragraphs for spacing; use paragraph spacing instead", [])
    hr = [p for p in paras if not p.text.strip() and p.pp.get("borders") and not p.in_table]
    if len(hr) >= 3: add("INFO", "horizontal-rules", f"{len(hr)} bare horizontal rules between sections", [])

    # ---- metadata
    if core is not None:
        lm = core.findtext("cp:lastModifiedBy", namespaces=NS) or ""
        cr = core.findtext("dc:creator", namespaces=NS) or ""
        ti = core.findtext("dc:title", namespaces=NS) or ""
        if lm.strip().lower() in ("un-named", "unnamed", "") : add("WARN", "metadata-author", f"lastModifiedBy is '{lm or 'empty'}' (docx-js/python-docx default); set it to the firm or author", [])
        if cr.strip().lower() in ("", "python-docx", "un-named"): add("WARN", "metadata-creator", f"creator is '{cr or 'empty'}'; set it", [])
        if not ti.strip(): add("INFO", "metadata-title", "core title is empty", [])
    if app is None or app.find("{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Application") is None:
        add("INFO", "metadata-app", "app.xml has no Application/Company; set_metadata.py fills it", [])

    stats = {"paragraphs": len(body), "prose_paragraphs": len(prose), "words": sum(len(p.text.split()) for p in body),
             "sentences": len(sents), "bullets": len(bullets), "headings": len(heads), "tables_paragraphs": sum(1 for p in body if p.in_table)}
    order = {"FAIL": 0, "WARN": 1, "INFO": 2}
    findings.sort(key=lambda f: order[f["severity"]])
    if a.json:
        print(json.dumps({"file": a.docx, "stats": stats, "findings": findings}, indent=2, ensure_ascii=False))
    else:
        print(f"{a.docx}: {stats['words']} words, {stats['prose_paragraphs']} prose paragraphs, {stats['bullets']} bullets, {stats['headings']} headings")
        if not findings: print("no findings")
        for f in findings:
            print(f"[{f['severity']}] {f['code']}: {f['message']}")
            for e in f["examples"]: print(f"        {e}")
    fails = sum(1 for f in findings if f["severity"] == "FAIL"); warns = sum(1 for f in findings if f["severity"] == "WARN")
    sys.exit(1 if fails or (a.strict and warns) else 0)


if __name__ == "__main__":
    main()
