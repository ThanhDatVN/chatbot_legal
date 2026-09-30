"""Automated quality gates for a corpus snapshot.

Hard gates block the build. Soft checks are reported for review. A chunk may be
marked `machine_checked` only when its document passes every hard gate and the
chunk passes the per-chunk checks; `verified` still requires a human.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from ingestion.chunk import MAX_TOKENS
from ingestion.layout import DocumentLayout, GAZETTE_BANNER, HEADER_RE, STAMP_RE
from ingestion.models import INDEXABLE_KINDS, Chunk, RegistryDocument, SectionKind
from ingestion.structure import ParsedDocument

HEADER_INLINE_RE = re.compile(r"CÔNG BÁO/Số\s+\d+(\s*\+\s*\d+)?/Ngày")
STAMP_INLINE_RE = re.compile(r"(Ký bởi|Người ký|Ngày ký|Thời gian ký)\s*:|thongtinchinhphu@chinhphu\.vn"
                             r"|[Tt]iếp theo Công báo số")
MAX_EMBEDDING_TOKENS = 1024
MAX_INVALID_SYLLABLE_RATE = 0.01

TONE_MARKS = {"̀", "́", "̃", "̉", "̣"}
ONSETS = ["", "b", "c", "ch", "d", "đ", "g", "gh", "gi", "h", "k", "kh", "l", "m", "n", "ng", "ngh", "nh", "p", "ph",
          "qu", "r", "s", "t", "th", "tr", "v", "x"]
NUCLEI = {
    "a": ["", "i", "o", "u", "y", "c", "ch", "m", "n", "ng", "nh", "p", "t"], "ă": ["c", "m", "n", "ng", "p", "t"],
    "â": ["u", "y", "c", "m", "n", "ng", "p", "t"], "e": ["", "o", "c", "m", "n", "ng", "p", "t"],
    "ê": ["", "u", "ch", "m", "n", "nh", "p", "t"], "i": ["", "a", "u", "ch", "m", "n", "nh", "p", "t"],
    "o": ["", "i", "c", "m", "n", "ng", "p", "t", "ong"], "ô": ["", "i", "c", "m", "n", "ng", "p", "t"],
    "ơ": ["", "i", "m", "n", "p", "t", "u"], "u": ["", "a", "i", "y", "c", "m", "n", "ng", "p", "t"],
    "ư": ["", "a", "i", "u", "c", "m", "n", "ng", "t"], "y": ["", "nh", "ch", "t", "n", "p", "u"],
    "iê": ["u", "c", "m", "n", "ng", "p", "t"], "yê": ["u", "m", "n", "ng", "t"], "uô": ["i", "c", "m", "n", "ng", "t"],
    "ươ": ["i", "u", "c", "m", "n", "ng", "p", "t"], "oa": ["", "i", "o", "y", "c", "ch", "m", "n", "ng", "nh", "p", "t"],
    "oă": ["c", "m", "n", "ng", "t"], "oe": ["", "o", "n", "t"], "uâ": ["y", "n", "ng", "t"], "uê": ["", "ch", "nh", "n"],
    "uy": ["", "a", "u", "ch", "n", "nh", "p", "t"], "uyê": ["n", "t"], "uơ": [""],
}
RHYMES = {n + c for n, cs in NUCLEI.items() for c in cs}
ROMAN_RE = re.compile(r"^[IVXLC]+$")


def _strip_tone(word: str) -> str:
    return unicodedata.normalize("NFC", "".join(
        ch for ch in unicodedata.normalize("NFD", word) if ch not in TONE_MARKS))


def valid_syllable(word: str) -> bool:
    w = _strip_tone(word.lower())
    return any(w.startswith(o) and w[len(o):] in RHYMES for o in ONSETS)


def invalid_syllables(text: str) -> tuple[int, int, list[str]]:
    total = bad = 0
    examples: list[str] = []
    for tok in re.findall(r"[^\W\d_]+", text):
        if len(tok) < 2 or ROMAN_RE.match(tok) or tok.isascii():
            continue  # abbreviations, roman numerals, e-mail/English words in forms
        if tok.isupper() and not valid_syllable(tok):
            continue
        total += 1
        if not valid_syllable(tok):
            bad += 1
            if len(examples) < 10:
                examples.append(tok)
    return total, bad, examples


def loose(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    return " ".join(re.findall(r"[^\W_]+", text))


@dataclass
class DocumentQuality:
    document_id: str
    hard: dict[str, bool] = field(default_factory=dict)
    details: dict[str, object] = field(default_factory=dict)
    soft: dict[str, object] = field(default_factory=dict)
    chunk_failures: dict[str, list[str]] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(self.hard.values())


def chunk_problems(chunk: Chunk, footnote_texts: list[str]) -> list[str]:
    problems = []
    if not chunk.text.strip():
        problems.append("empty")
    if HEADER_INLINE_RE.search(chunk.text) or STAMP_INLINE_RE.search(chunk.text) or GAZETTE_BANNER in chunk.text:
        problems.append("header_or_stamp_leak")
    if any(snippet and snippet in chunk.text for snippet in footnote_texts):
        problems.append("footnote_leak")
    if chunk.embedding_token_count > MAX_EMBEDDING_TOKENS:
        problems.append("too_many_tokens")
    return problems


def check_document(doc: RegistryDocument, layout: DocumentLayout, parsed: ParsedDocument, chunks: list[Chunk],
                   hashes_ok: bool, fixtures: dict) -> DocumentQuality:
    q = DocumentQuality(document_id=doc.document_id)
    q.hard["source_hashes"] = hashes_ok
    page_total = sum(p.pages for p in doc.source_parts) - len(layout.blank_pages)
    q.hard["page_count"] = len(layout.pages) == page_total
    q.details["pages"] = len(layout.pages)

    articles = [s.article_number for s in parsed.sections if s.kind == SectionKind.MAIN_TEXT]
    q.hard["article_sequence"] = articles == list(range(1, doc.expected_main_articles + 1))
    q.details["main_articles"] = len(articles)
    q.soft["structure_warnings"] = parsed.warnings

    # every paragraph is inside exactly one section or is a chapter/part heading
    owners = []
    for k, p in enumerate(parsed.paragraphs):
        n = sum(1 for s in parsed.sections if s.start <= p.start and p.end <= s.end)
        owners.append(n + (1 if k in parsed.structural_paragraphs else 0))
    q.hard["paragraph_ownership"] = all(n == 1 for n in owners)

    # every indexable paragraph is covered by at least one chunk of its section
    uncovered = 0
    for s in parsed.sections:
        if s.kind not in INDEXABLE_KINDS:
            continue
        spans = [(c.source_start_char, c.source_end_char) for c in chunks if c.section_id == s.section_id]
        for p in parsed.paragraphs:
            if s.start <= p.start and p.end <= s.end and not any(a <= p.start and p.end <= b for a, b in spans):
                uncovered += 1
    q.hard["chunk_coverage"] = uncovered == 0
    q.details["uncovered_paragraphs"] = uncovered

    q.hard["exact_offsets"] = all(parsed.text[c.source_start_char:c.source_end_char] == c.raw_text for c in chunks)
    q.hard["page_bounds"] = all(1 <= c.page_start <= c.page_end <= len(layout.pages) for c in chunks)

    number_loose = loose(doc.document_number)
    q.hard["document_number_in_text"] = number_loose in loose(parsed.text)

    footnote_texts = [fn.text[:80] for fn in parsed.footnotes]
    q.hard["footnotes_attached"] = all(fn.section_id and fn.target_label for fn in parsed.footnotes) \
        and len(parsed.footnotes) == len(layout.footnotes)
    q.details["footnotes"] = len(parsed.footnotes)

    q.hard["no_header_lines_in_body"] = not any(
        HEADER_RE.match(line.text.strip()) or STAMP_RE.match(line.text.strip()) for line in parsed.lines)
    for c in chunks:
        problems = chunk_problems(c, footnote_texts)
        if problems:
            q.chunk_failures[c.chunk_id] = problems
    q.hard["chunk_checks"] = not q.chunk_failures

    over_budget = [c.chunk_id for c in chunks if c.token_count > MAX_TOKENS]
    q.soft["chunks_over_token_budget"] = len(over_budget)

    total, bad, examples = invalid_syllables("\n".join(c.text for c in chunks if c.section_kind != SectionKind.ANNEX))
    rate = bad / total if total else 0.0
    q.soft["invalid_syllable_rate"] = round(rate, 5)
    q.soft["invalid_syllable_examples"] = examples
    q.hard["syllable_validity"] = rate <= MAX_INVALID_SYLLABLE_RATE

    unlabeled = [t.page for t in layout.tables if t.header_source == "none"]
    q.soft["tables"] = len(layout.tables)
    q.soft["tables_without_column_labels"] = unlabeled

    if doc.effective_date:
        d = doc.effective_date
        pattern = rf"ngày 0?{d.day} tháng 0?{d.month} năm {d.year}"
        q.soft["effective_date_in_text"] = bool(re.search(pattern, " ".join(parsed.text.split())))

    fixture_results = []
    by_section: dict[str, str] = {}
    for c in chunks:
        by_section[c.section_label] = by_section.get(c.section_label, "") + "\n" + c.text
    for fx in fixtures.get("passages", []):
        if fx["document_id"] != doc.document_id:
            continue
        haystack = " ".join(by_section.get(fx["section"], "").split())
        found = loose(fx["text"]) in loose(haystack) if fx["match"] == "loose" else fx["text"] in haystack
        fixture_results.append({"section": fx["section"], "kind": fx["kind"], "found": found})
    for fx in fixtures.get("footnotes", []):
        if fx["document_id"] != doc.document_id:
            continue
        fn = next((f for f in parsed.footnotes if f.number == fx["number"]), None)
        ok = fn is not None and fn.target_label == fx["target_label"] and fn.change_type == fx["change_type"] \
            and fx["instrument"] in (fn.amending_instrument or "") and str(fn.effective_from) == fx["effective_from"]
        fixture_results.append({"footnote": fx["number"], "found": ok})
    q.details["fixtures"] = fixture_results
    q.hard["regression_fixtures"] = all(r["found"] for r in fixture_results)

    if doc.document_id == "135_2020_nd_cp":
        q.details["retirement_schedule"] = retirement_invariant(layout)
        q.hard["retirement_schedule"] = q.details["retirement_schedule"]["violations"] == 0 \
            and q.details["retirement_schedule"]["rows"] == 350
    return q


def retirement_invariant(layout: DocumentLayout) -> dict:
    """Annex I/II of Nghị định 135/2020: pension month = birth month + retirement age + 1 month."""
    rows = violations = 0
    for table in layout.tables:
        if table.page < 7:
            continue
        for values in table.rows:
            for k in range(0, len(values), 5):
                group = values[k:k + 5]
                if len(group) < 5 or not (group[0].isdigit() and group[1].isdigit()):
                    continue
                m = re.search(r"(\d+)\s*tuổi(?:\s*(\d+)\s*tháng)?", group[2])
                if not m or not group[3].isdigit() or not group[4].isdigit():
                    violations += 1
                    continue
                age = int(m.group(1)) * 12 + int(m.group(2) or 0)
                total = int(group[1]) * 12 + int(group[0]) - 1 + age + 1
                rows += 1
                if (total // 12, total % 12 + 1) != (int(group[4]), int(group[3])):
                    violations += 1
    return {"rows": rows, "violations": violations}
