"""Parent-child chunking over the parsed legal tree.

The split follows the law's own units rather than a token window:

*   **Parent** = one Dieu (article).  This is what the model reads, because a
    Khoan is frequently meaningless without the article's opening sentence
    ("Cac truong hop sau day duoc mien thue: 1. ... 2. ...").
*   **Child** = one Khoan, or a Diem when the Khoan is long.  This is what gets
    embedded and retrieved, because it is the unit a user's question actually
    matches and the unit a citation must point at.

Retrieval scores children and hands the model parents.  That combination is
what the ablation calls ``use_parent_expansion``.
"""

from __future__ import annotations

import hashlib
import re

from virag.ingest.structure import iter_articles, node_full_text
from virag.legal import authority as authority_mod
from virag.schemas import Chunk, DocumentMeta, LegalNode, ParentChunk, stable_id
from virag.settings import Settings, get_settings

_WORD = re.compile(r"\S+")


def count_tokens(text: str) -> int:
    """Whitespace token count.

    Vietnamese is written in syllables separated by spaces, so this tracks real
    length closely enough for chunk sizing and costs nothing.
    """
    return len(_WORD.findall(text))


def content_hash(text: str) -> str:
    normalised = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def make_version_id(meta: DocumentMeta, text: str) -> str:
    """Stable identity of one *version* of an instrument.

    Re-crawling an unchanged document yields the same version id, so ingestion
    is idempotent; a changed body yields a new one, so old citations keep
    resolving to the text they were made against.
    """
    base = meta.instrument_number or meta.document_id
    return f"{base}#{content_hash(text)[:12]}"


def _citation_label(
    meta: DocumentMeta,
    dieu: str | None,
    khoan: str | None = None,
    diem: str | None = None,
) -> str:
    parts: list[str] = []
    if dieu:
        parts.append(f"Điều {dieu}")
    if khoan:
        parts.append(f"khoản {khoan}")
    if diem:
        parts.append(f"điểm {diem}")
    pin = " ".join(parts) if parts else "Toàn văn"

    instrument = meta.instrument_number or meta.document_id
    doc_type = meta.document_type or ""
    label = f"{doc_type} {instrument}".strip()
    return f"{pin} - {label}"


def window_parent(parent_text: str, child_text: str, max_tokens: int) -> str:
    """Fit a parent article into ``max_tokens`` **without losing the child**.

    Parent expansion exists to give the model the article's opening sentence,
    which a Khoan usually needs to make sense ("Cac truong hop sau day duoc
    mien thue: 1. ... 2. ..."). Truncating the article from the head defeats
    that: a clause late in a long article is deleted by the step meant to
    supply its context, while the citation still points at it.

    So the window always keeps two things: the article's opening lines, and the
    child itself. When both fit, the text is returned whole.
    """
    words = _WORD.findall(parent_text)
    if len(words) <= max_tokens:
        return parent_text

    # Locate the child inside the parent.  The child repeats the article header,
    # so match on its distinctive tail rather than its first line.
    child_lines = [line for line in child_text.splitlines() if line.strip()]
    needle = child_lines[-1].strip() if child_lines else ""
    position = parent_text.find(needle) if needle else -1

    # A head budget large enough to carry the article heading and its lead-in.
    head_tokens = max(1, min(max_tokens // 4, 120))
    head = " ".join(words[:head_tokens])

    if position < 0:
        # Child not locatable: keep the head and say so rather than pretend the
        # article is complete.
        return f"{head}\n[...]"

    prefix_tokens = len(_WORD.findall(parent_text[:position]))
    body_budget = max_tokens - head_tokens
    start = max(head_tokens, prefix_tokens - body_budget // 3)
    body = " ".join(words[start : start + body_budget])

    parts = [head]
    if start > head_tokens:
        parts.append("[...]")
    parts.append(body)
    if start + body_budget < len(words):
        parts.append("[...]")
    return "\n".join(parts)


def _split_long_text(text: str, target: int, overlap: int) -> list[str]:
    """Sentence-aware split for clauses that exceed the child budget."""
    words = _WORD.findall(text)
    if len(words) <= target:
        return [text]

    pieces: list[str] = []
    start = 0
    step = max(1, target - overlap)
    while start < len(words):
        window = words[start : start + target]
        if not window:
            break
        pieces.append(" ".join(window))
        if start + target >= len(words):
            break
        start += step
    return pieces


def chunk_document(
    nodes: list[LegalNode],
    meta: DocumentMeta,
    settings: Settings | None = None,
) -> tuple[list[ParentChunk], list[Chunk]]:
    """Turn a parsed document into (parents, children).

    ``meta`` is mutated with the resolved authority tier and version id so the
    caller can persist a single, consistent record.
    """
    settings = settings or get_settings()

    meta.authority_tier = authority_mod.resolve_tier(
        meta.document_type, meta.instrument_number, meta.title
    )

    articles = iter_articles(nodes)
    if not articles:
        return _chunk_unstructured(nodes, meta, settings)

    full_text = "\n\n".join(node_full_text(article) for article, _ in articles)
    meta.version_id = meta.version_id or make_version_id(meta, full_text)

    parents: list[ParentChunk] = []
    children: list[Chunk] = []

    for article, ancestry in articles:
        article_text = node_full_text(article)
        if not article_text.strip():
            continue

        parent_id = stable_id(meta.document_id, "dieu", article.number or "?", content_hash(article_text)[:8])
        parent = ParentChunk(
            parent_id=parent_id,
            document_id=meta.document_id,
            # Store the article whole.  An earlier version sliced it to
            # `parent_max_tokens * 8` characters, which was both a unit error (a
            # token budget applied as a character bound) and a correctness bug:
            # a Khoan near the end of a long Dieu was cut out of the very
            # context meant to explain it.  Fitting the budget is a retrieval
            # concern, handled by `window_parent`, because only retrieval knows
            # which child has to stay in view.
            text=article_text,
            citation_label=_citation_label(meta, article.number),
            dieu=article.number,
            chuong=ancestry.get("chuong"),
            page_number=article.page_number,
            meta=meta,
        )

        units = _child_units(article)
        for khoan_number, diem_number, unit_text, page in units:
            if not unit_text.strip():
                continue
            for index, piece in enumerate(
                _split_long_text(unit_text, settings.child_target_tokens, settings.child_overlap_tokens)
            ):
                chunk_id = stable_id(parent_id, khoan_number or "-", diem_number or "-", str(index))
                children.append(
                    Chunk(
                        chunk_id=chunk_id,
                        document_id=meta.document_id,
                        parent_id=parent_id,
                        text=piece,
                        citation_label=_citation_label(meta, article.number, khoan_number, diem_number),
                        dieu=article.number,
                        khoan=khoan_number,
                        diem=diem_number,
                        chuong=ancestry.get("chuong"),
                        muc=ancestry.get("muc"),
                        page_number=page,
                        token_count=count_tokens(piece),
                        legal_status=meta.legal_status,
                        authority_tier=meta.authority_tier,
                        version_id=meta.version_id,
                        effective_from=meta.effective_from,
                        effective_to=meta.effective_to,
                        tax_domains=list(meta.tax_domains),
                        meta=meta,
                    )
                )
                parent.child_ids.append(chunk_id)

        if parent.child_ids:
            parents.append(parent)

    return parents, children


def _child_units(article: LegalNode) -> list[tuple[str | None, str | None, str, int | None]]:
    """Flatten an article into ``(khoan, diem, text, page)`` retrieval units.

    An article with no Khoan yields one unit carrying the whole article, so
    every article is retrievable even when the numbering was not recovered.
    """
    units: list[tuple[str | None, str | None, str, int | None]] = []

    header = f"Điều {article.number}. {article.heading}".strip() if article.number else ""
    if not article.children:
        body = f"{header}\n{article.text}".strip() if header else article.text
        return [(None, None, body, article.page_number)]

    if article.text.strip():
        units.append((None, None, f"{header}\n{article.text}".strip(), article.page_number))

    for khoan in article.children:
        if khoan.kind != "khoan":
            units.append((None, None, node_full_text(khoan), khoan.page_number))
            continue

        khoan_number = khoan.number if khoan.number != "?" else None
        # Repeating the article header in every child keeps the retrieved
        # snippet self-describing when it is shown without its parent.
        prefix = f"{header}\n" if header else ""

        if not khoan.children:
            body = f"{prefix}{khoan_number}. {khoan.text}".strip()
            units.append((khoan_number, None, body, khoan.page_number))
            continue

        if khoan.text.strip():
            units.append(
                (khoan_number, None, f"{prefix}{khoan_number}. {khoan.text}".strip(), khoan.page_number)
            )
        for diem in khoan.children:
            diem_number = diem.number if diem.number != "?" else None
            lead = f"{prefix}{khoan_number}. {khoan.text}".strip()
            body = f"{lead}\n{diem_number}) {diem.text}".strip()
            units.append((khoan_number, diem_number, body, diem.page_number))

    return units


def _chunk_unstructured(
    nodes: list[LegalNode],
    meta: DocumentMeta,
    settings: Settings,
) -> tuple[list[ParentChunk], list[Chunk]]:
    """Fallback for documents where no Dieu heading was recovered.

    Citation degrades to page level, which the label makes explicit rather than
    inventing an article number.
    """
    text = "\n".join(node_full_text(node) for node in nodes).strip()
    if not text:
        return [], []

    meta.version_id = meta.version_id or make_version_id(meta, text)

    parents: list[ParentChunk] = []
    children: list[Chunk] = []
    blocks = _split_long_text(text, settings.parent_max_tokens, 0)

    for block_index, block in enumerate(blocks):
        parent_id = stable_id(meta.document_id, "block", str(block_index))
        label = f"Đoạn {block_index + 1} - {meta.instrument_number or meta.document_id}"
        parent = ParentChunk(
            parent_id=parent_id,
            document_id=meta.document_id,
            text=block,
            citation_label=label,
            meta=meta,
        )
        for piece_index, piece in enumerate(
            _split_long_text(block, settings.child_target_tokens, settings.child_overlap_tokens)
        ):
            chunk_id = stable_id(parent_id, str(piece_index))
            children.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=meta.document_id,
                    parent_id=parent_id,
                    text=piece,
                    citation_label=label,
                    token_count=count_tokens(piece),
                    legal_status=meta.legal_status,
                    authority_tier=meta.authority_tier,
                    version_id=meta.version_id,
                    effective_from=meta.effective_from,
                    effective_to=meta.effective_to,
                    tax_domains=list(meta.tax_domains),
                    meta=meta,
                )
            )
            parent.child_ids.append(chunk_id)
        if parent.child_ids:
            parents.append(parent)

    return parents, children
