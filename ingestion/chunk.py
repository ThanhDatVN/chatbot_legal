"""Structure-aware chunking with exact source offsets.

An article that fits the token budget stays one chunk. Longer articles are split
at clause (khoản) boundaries, then paragraph boundaries, and only as a last
resort inside a paragraph, where consecutive pieces overlap by about
OVERLAP_TOKENS. Every chunk's raw_text is an exact slice of the document text.

`breaks` forces cuts at given clause starts, so that a clause the currency
ledger marks as expired or amended never shares a chunk with clauses that are
still in force.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from ingestion.models import (INDEXABLE_KINDS, Chunk, CurrencyStatus, Footnote, RegistryDocument, Section,
                              SectionKind, TextQualityStatus)
from ingestion.structure import CLAUSE_RE, ParsedDocument, Paragraph
from ingestion.tokenizer import TokenCounter

MAX_TOKENS = 700
OVERLAP_TOKENS = 100
FORM_RE = re.compile(r"^Mẫu số\s+\S+")
SENTENCE_BREAK_RE = re.compile(r"(?<=[.;:])\s+")
DOT_LEADER_RE = re.compile(r"[.…]{4,}")
CHUNKER_VERSION = "chunker-v4"


@dataclass
class Span:
    start: int
    end: int


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_span(parsed: ParsedDocument, start: int, end: int, paragraphs: list[Paragraph]) -> str:
    out = []
    for p in paragraphs:
        if p.end <= start or p.start >= end:
            continue
        piece = parsed.text[max(p.start, start):min(p.end, end)]
        piece = DOT_LEADER_RE.sub("…", " ".join(piece.split()))
        if piece:
            out.append(piece)
    return "\n".join(out)


def _clause_groups(section: Section, paras: list[Paragraph],
                   breaks: set[int] | frozenset[int] = frozenset()) -> list[list[Paragraph]]:
    groups: list[list[Paragraph]] = []
    for p in paras:
        starts_group = not groups or p.start in breaks
        if section.kind == SectionKind.MAIN_TEXT and CLAUSE_RE.match(p.text):
            starts_group = True
        if section.kind == SectionKind.ANNEX and FORM_RE.match(p.text):
            starts_group = True
        if starts_group:
            groups.append([p])
        else:
            groups[-1].append(p)
    return groups


def _split_long_paragraph(parsed: ParsedDocument, p: Paragraph, counter: TokenCounter) -> list[Span]:
    raw = parsed.text[p.start:p.end]
    cuts = [0] + [m.end() for m in SENTENCE_BREAK_RE.finditer(raw)] + [len(raw)]
    pieces = [(p.start + a, p.start + b) for a, b in zip(cuts, cuts[1:]) if raw[a:b].strip()]
    spans: list[Span] = []
    i = 0
    while i < len(pieces):
        start = pieces[i][0]
        j = i
        while j + 1 < len(pieces) and counter.count(parsed.text[start:pieces[j + 1][1]]) <= MAX_TOKENS:
            j += 1
        end = pieces[j][1]
        if counter.count(parsed.text[start:end]) > MAX_TOKENS:
            spans.extend(_split_words(parsed, start, end, counter))
        else:
            spans.append(Span(start, end))
        if j + 1 >= len(pieces):
            break
        # step back so the next piece repeats about OVERLAP_TOKENS of context
        k = j + 1
        while k - 1 > i and counter.count(parsed.text[pieces[k - 1][0]:end]) <= OVERLAP_TOKENS:
            k -= 1
        i = k
    return spans


def _split_words(parsed: ParsedDocument, start: int, end: int, counter: TokenCounter) -> list[Span]:
    words = [(m.start() + start, m.end() + start) for m in re.finditer(r"\S+", parsed.text[start:end])]
    spans: list[Span] = []
    i = 0
    while i < len(words):
        j = i
        while j + 1 < len(words) and counter.count(parsed.text[words[i][0]:words[j + 1][1]]) <= MAX_TOKENS:
            j += 1
        spans.append(Span(words[i][0], words[j][1]))
        if j + 1 >= len(words):
            break
        back = j
        while back > i and counter.count(parsed.text[words[back][0]:words[j][1]]) <= OVERLAP_TOKENS:
            back -= 1
        i = max(back + 1, i + 1)
    return spans


def section_spans(parsed: ParsedDocument, section: Section, counter: TokenCounter,
                  breaks: set[int] | frozenset[int] = frozenset()) -> list[Span]:
    paras = [p for p in parsed.paragraphs if p.start >= section.start and p.end <= section.end]
    if not breaks and counter.count(parsed.text[section.start:section.end]) <= MAX_TOKENS:
        return [Span(section.start, section.end)]
    spans: list[Span] = []
    for group in _clause_groups(section, paras, breaks):
        g_start, g_end = group[0].start, group[-1].end
        if spans and g_start not in breaks and counter.count(parsed.text[spans[-1].start:g_end]) <= MAX_TOKENS \
                and not (section.kind == SectionKind.ANNEX and FORM_RE.match(group[0].text)):
            spans[-1] = Span(spans[-1].start, g_end)
            continue
        if counter.count(parsed.text[g_start:g_end]) <= MAX_TOKENS:
            spans.append(Span(g_start, g_end))
            continue
        for p in group:  # clause too long: pack its paragraphs
            if spans and spans[-1].end <= p.start and counter.count(parsed.text[spans[-1].start:p.end]) <= MAX_TOKENS \
                    and spans[-1].start >= g_start:
                spans[-1] = Span(spans[-1].start, p.end)
            elif counter.count(parsed.text[p.start:p.end]) <= MAX_TOKENS:
                spans.append(Span(p.start, p.end))
            else:
                spans.extend(_split_long_paragraph(parsed, p, counter))
    return spans


def _pages_for(parsed: ParsedDocument, start: int, end: int) -> tuple[int, int]:
    pages = [parsed.lines[i].page for i, (a, b) in enumerate(parsed.line_spans) if a < end and b > start]
    return min(pages), max(pages)


def _form_label(parsed: ParsedDocument, section: Section, start: int) -> str | None:
    label = None
    for p in parsed.paragraphs:
        if p.start < section.start:
            continue
        if p.start > start:
            break
        m = FORM_RE.match(p.text)
        if m:
            label = m.group(0)
    return label


def chunk_document(parsed: ParsedDocument, doc: RegistryDocument, snapshot_id: str,
                   counter: TokenCounter, breaks: dict[str, set[int]] | None = None) -> list[Chunk]:
    chunks: list[Chunk] = []
    source_shas = [part.sha256 for part in doc.source_parts]
    base = f"{doc.short_title} ({doc.document_number})"
    for section in parsed.sections:
        if section.kind not in INDEXABLE_KINDS or (doc.section_scope and section.label not in doc.section_scope):
            continue
        paras = [p for p in parsed.paragraphs if p.start >= section.start and p.end <= section.end]
        spans = section_spans(parsed, section, counter, (breaks or {}).get(section.section_id, frozenset()))
        notes = [fn for fn in parsed.footnotes if fn.section_id == section.section_id]
        for ordinal, span in enumerate(spans):
            raw = parsed.text[span.start:span.end]
            text = normalize_span(parsed, span.start, span.end, paras)
            path = list(section.path)
            if section.kind == SectionKind.ANNEX:
                form = _form_label(parsed, section, span.start)
                if form:
                    path.append(form)
            header = f"{base} › " + " › ".join(path)
            if len(spans) > 1:
                header += f" (phần {ordinal + 1}/{len(spans)})"
            page_start, page_end = _pages_for(parsed, span.start, span.end)
            attached: list[Footnote] = [
                fn for fn in notes
                if (fn.marker_offset is not None and span.start <= fn.marker_offset <= span.end)
                or (ordinal == 0 and (fn.marker_offset is None or not section.start <= fn.marker_offset <= section.end))
            ]
            embedding_text = f"{header}\n{text}"
            chunk_id = sha(f"{doc.document_id}|{','.join(source_shas)}|{section.section_id}|{ordinal}|{sha(text)}")[:24]
            chunks.append(Chunk(
                chunk_id=chunk_id, corpus_snapshot_id=snapshot_id, document_id=doc.document_id,
                document_number=doc.document_number, document_title=doc.title, short_title=doc.short_title,
                document_type=doc.document_type, issuer=doc.issuer, section_id=section.section_id,
                section_kind=section.kind, section_label=section.label, section_title=section.title,
                section_path=path, article_number=section.article_number, ordinal=ordinal, part_count=len(spans),
                page_start=page_start, page_end=page_end, source_start_char=span.start, source_end_char=span.end,
                raw_text=raw, text=text, context_header=header, embedding_text=embedding_text,
                token_count=counter.count(text), embedding_token_count=counter.count(embedding_text),
                source_url=doc.source_url, source_sha256=source_shas, content_sha256=sha(raw),
                contains_quoted_amendment=section.contains_quoted_amendment,
                contains_table=any(p.is_table for p in paras if p.start >= span.start and p.end <= span.end),
                amendment_notes=attached, currency_status=CurrencyStatus.UNVERIFIED, currency_basis="pending",
                text_quality_status=TextQualityStatus.UNREVIEWED))
    return chunks
