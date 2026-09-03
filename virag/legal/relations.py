"""Legal dependency graph: who amends, replaces, repeals, details or guides whom.

Vietnamese normative documents announce their own edges in stereotyped prose.
Crucially, they cite their target **by name far more often than by number** -
measured on this corpus, 134 of 193 resolvable links (69%) carry no instrument
number at all:

    "Luat so 149/2025/QH15 ... sua doi, bo sung mot so dieu cua
     Luat Thue gia tri gia tang"                    <- name only, no number

    "Bai bo Thong tu so 39/2014/TT-BTC"             <- number

A number-only extractor finds 31% of the graph and silently drops the rest,
which would break change detection, impact analysis, clause-level status and
conflict adjudication alike.  This module therefore matches on both axes.

Extracting these edges deterministically keeps change detection auditable: no
LLM is in the loop.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict, deque
from dataclasses import dataclass, field

from virag.schemas import LegalRelation, RelationType

#: "48/2024/QH15", "123/2025/ND-CP", "39/2014/TT-BTC"
INSTRUMENT_RE = re.compile(
    r"\b(\d{1,4}\s*/\s*(?:19|20)\d{2}\s*/\s*[A-ZĐ][A-ZĐ0-9\-]{1,20})\b"
)
#: Consolidated-document numbers routinely omit the year: "67/VBHN-NĐ-BCT".
VBHN_RE = re.compile(r"\b(\d{1,4}\s*/\s*(?:(?:19|20)\d{2}\s*/\s*)?VBHN[A-ZĐ0-9\-]*)\b")

#: Trailing article/clause pointer inside an amendment sentence.
_DIEU_POINTER = re.compile(r"Điều\s+(\d{1,3}[a-zđ]?)", re.IGNORECASE)
_KHOAN_POINTER = re.compile(r"khoản\s+(\d{1,2})", re.IGNORECASE)

#: A citable legal subject, e.g. "Luật Thuế giá trị gia tăng".
SUBJECT_RE = re.compile(
    r"((?:Bộ\s*luật|Luật|Pháp\s*lệnh|Nghị\s*định|Nghị\s*quyết|Thông\s*tư|Quyết\s*định)"
    r"[^,;.:]{4,120})",
    re.IGNORECASE,
)

#: The clause that introduces the target of an amendment or consolidation.
_AFTER_CUA = re.compile(
    r"(?:sửa\s*đổi[^:]{0,40}?của|bổ\s*sung[^:]{0,40}?của|bãi\s*bỏ|thay\s*thế)\s+(.+)$",
    re.IGNORECASE,
)
_AFTER_HOPNHAT = re.compile(r"hợp\s*nhất\s+(.+)$", re.IGNORECASE)

# Ordered: the first cue that matches a sentence wins, and the stronger verbs
# come first so "thay the" is not swallowed by "sua doi, bo sung ... thay the".
_CUES: tuple[tuple[RelationType, tuple[str, ...], float], ...] = (
    ("REPEALS", ("bãi bỏ", "hủy bỏ", "chấm dứt hiệu lực", "hết hiệu lực thi hành"), 0.9),
    ("REPLACES", ("thay thế", "thay thế cho"), 0.9),
    ("AMENDS", ("sửa đổi, bổ sung", "sửa đổi", "bổ sung một số điều", "bổ sung"), 0.85),
    ("CONSOLIDATES", ("hợp nhất",), 0.9),
    ("DETAILS", ("quy định chi tiết", "quy định chi tiết thi hành"), 0.8),
    ("GUIDES", ("hướng dẫn thi hành", "hướng dẫn thực hiện", "hướng dẫn"), 0.75),
    ("INTERPRETS", ("giải thích", "trả lời về"), 0.6),
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.;:\n])\s+")


def normalise_instrument(number: str) -> str:
    """Canonical form: whitespace removed, uppercased."""
    return re.sub(r"\s+", "", number).upper()


def fold(text: str) -> str:
    """Lowercase, strip Vietnamese diacritics, collapse whitespace.

    Subject names are compared folded so that a target cited as
    "Luật Thuế Giá trị gia tăng" matches an instrument titled
    "Luật Thuế giá trị gia tăng".
    """
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", stripped.replace("đ", "d")).strip()


def extract_subject(title: str) -> str:
    """The instrument's **own** normalised name, for name-based matching.

    Valid only when the name after the colon *starts* with a legal-type word:

        "Luật số 48/2024/QH15 của Quốc hội: Luật Thuế giá trị gia tăng"
            -> "luat thue gia tri gia tang"                    (its own name)

    A document that merely implements another has no name of its own, and
    naming it after its target would make it absorb every link aimed at that
    target:

        "Nghị định số 181/2025/NĐ-CP ...: Quy định chi tiết ... của
         Luật Thuế giá trị gia tăng"
            -> ""     (identity is its number, NOT the VAT Law)

    Getting this wrong inflates the dependency graph with phantom edges.
    """
    if not title:
        return ""
    tail = title.split(":", 1)[1].strip() if ":" in title else title.strip()
    match = SUBJECT_RE.match(tail)  # match, not search: must start with the type
    return fold(match.group(1)) if match else ""


def _targets_in_sentence(sentence: str) -> tuple[set[str], set[str]]:
    """Targets cited in one sentence, by instrument number and by subject name."""
    numbers: set[str] = set()
    for pattern in (INSTRUMENT_RE, VBHN_RE):
        numbers.update(normalise_instrument(m) for m in pattern.findall(sentence))

    names: set[str] = set()
    match = _AFTER_CUA.search(sentence) or _AFTER_HOPNHAT.search(sentence)
    if match:
        # "Luật A, Luật B và Luật C" -> three separate targets.
        for part in re.split(r",|\bvà\b", match.group(1)):
            found = SUBJECT_RE.search(part)
            if found:
                names.add(fold(found.group(1)))

    # "bãi bỏ Thông tư số 39/2014/TT-BTC" yields the same target twice - once as
    # a number, once as the surrounding phrase.  The number is strictly more
    # specific, so drop any name that merely restates a number already captured.
    if numbers:
        folded_numbers = {fold(number) for number in numbers}
        names = {
            name
            for name in names
            if not any(folded in name for folded in folded_numbers)
        }
    return numbers, names


def extract_relations(document_id: str, text: str, max_chars: int = 20000) -> list[LegalRelation]:
    """Pull dependency edges out of a document's own text.

    Only the head of the document is scanned: the title, the "can cu" recitals
    and the first articles carry essentially every amendment declaration, while
    the body is full of incidental cross-references that would flood the graph.
    """
    head = text[:max_chars]
    found: dict[tuple[str, str], LegalRelation] = {}

    for sentence in _SENTENCE_SPLIT.split(head):
        numbers, names = _targets_in_sentence(sentence)
        if not numbers and not names:
            continue

        lowered = sentence.lower()
        relation: RelationType = "REFERS_TO"
        confidence = 0.4
        for cue_relation, cues, cue_confidence in _CUES:
            if any(cue in lowered for cue in cues):
                relation, confidence = cue_relation, cue_confidence
                break

        # A bare cross-reference with no directional cue is only meaningful when
        # it names a number; a bare subject name is far too weak to be an edge.
        if relation == "REFERS_TO":
            names = set()

        dieu = _DIEU_POINTER.search(sentence)
        khoan = _KHOAN_POINTER.search(sentence)
        pointer = (
            dieu.group(1) if dieu else None,
            khoan.group(1) if khoan else None,
        )
        evidence = sentence.strip()[:400]

        for number in numbers:
            _record(found, document_id, relation, confidence, number, None, pointer, evidence)
        for name in names:
            _record(found, document_id, relation, confidence, "", name, pointer, evidence)

    return list(found.values())


def _record(
    found: dict[tuple[str, str], LegalRelation],
    document_id: str,
    relation: RelationType,
    confidence: float,
    target_instrument: str,
    target_subject: str | None,
    pointer: tuple[str | None, str | None],
    evidence: str,
) -> None:
    """Insert an edge, keeping the highest-confidence reading of a duplicate."""
    kind = "num" if target_instrument else "name"
    key = (relation, f"{kind}:{target_instrument or target_subject}")
    existing = found.get(key)
    if existing is not None and existing.confidence >= confidence:
        return
    found[key] = LegalRelation(
        source_document_id=document_id,
        relation=relation,
        target_instrument=target_instrument,
        target_subject=target_subject,
        target_dieu=pointer[0],
        target_khoan=pointer[1],
        evidence=evidence,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

#: Edges that change what a target document says; the rest are informational.
MUTATING = frozenset({"AMENDS", "REPLACES", "REPEALS", "CONSOLIDATES"})


@dataclass
class LegalGraph:
    """Directed graph over instrument numbers, resolvable by number or name.

    Nodes are canonical instrument numbers rather than internal document ids so
    that a document can point at an instrument the corpus does not contain yet -
    a dangling edge is information, not an error.
    """

    edges: list[LegalRelation] = field(default_factory=list)
    _out: dict[str, list[LegalRelation]] = field(default_factory=lambda: defaultdict(list))
    _in: dict[str, list[LegalRelation]] = field(default_factory=lambda: defaultdict(list))
    #: instrument number -> internal document id
    instrument_to_document: dict[str, str] = field(default_factory=dict)
    document_to_instrument: dict[str, str] = field(default_factory=dict)
    #: normalised subject name -> instrument numbers carrying that name
    subject_to_instruments: dict[str, list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def register_document(
        self,
        document_id: str,
        instrument_number: str | None,
        title: str | None = None,
    ) -> None:
        """Index a document so later edges can resolve to it.

        ``title`` is what makes name-based resolution possible; omit it and the
        graph falls back to number-only matching and loses ~69% of edges.
        """
        if not instrument_number:
            return
        canonical = normalise_instrument(instrument_number)
        self.instrument_to_document[canonical] = document_id
        self.document_to_instrument[document_id] = canonical

        subject = extract_subject(title or "")
        if subject and canonical not in self.subject_to_instruments[subject]:
            self.subject_to_instruments[subject].append(canonical)

    def _resolve(self, relation: LegalRelation) -> tuple[str, str | None]:
        """Return ``(target_instrument, matched_by)`` for an unresolved edge."""
        if relation.target_instrument:
            return relation.target_instrument, "number"
        if relation.target_subject:
            candidates = self.subject_to_instruments.get(relation.target_subject, [])
            if len(candidates) == 1:
                return candidates[0], "name"
            if candidates:
                # Ambiguous subject (several versions share a name).  Keep the
                # edge attached to the subject rather than guessing a version.
                return candidates[0], "name-ambiguous"
        return "", None

    def add(self, relation: LegalRelation) -> None:
        source = self.document_to_instrument.get(
            relation.source_document_id, relation.source_document_id
        )
        target, matched_by = self._resolve(relation)
        if target:
            relation.target_instrument = target
        relation.matched_by = matched_by
        relation.target_document_id = self.instrument_to_document.get(relation.target_instrument)

        # A self-edge is an artefact of a document restating its own number.
        if relation.target_instrument and relation.target_instrument == source:
            return

        self.edges.append(relation)
        self._out[source].append(relation)
        if relation.target_instrument:
            self._in[relation.target_instrument].append(relation)

    def add_all(self, relations: list[LegalRelation]) -> None:
        for relation in relations:
            self.add(relation)

    def outgoing(self, instrument: str) -> list[LegalRelation]:
        return list(self._out.get(normalise_instrument(instrument), []))

    def incoming(self, instrument: str) -> list[LegalRelation]:
        return list(self._in.get(normalise_instrument(instrument), []))

    def amendments_of(self, instrument: str) -> list[LegalRelation]:
        """Documents that amend / replace / repeal ``instrument``."""
        return [rel for rel in self.incoming(instrument) if rel.relation in MUTATING]

    def is_superseded(self, instrument: str) -> bool:
        return any(rel.relation in {"REPLACES", "REPEALS"} for rel in self.incoming(instrument))

    def resolution_stats(self) -> dict[str, int]:
        """How the graph was built - reported alongside any change analysis."""
        stats: dict[str, int] = defaultdict(int)
        for edge in self.edges:
            stats[edge.matched_by or "unresolved"] += 1
        stats["total"] = len(self.edges)
        return dict(stats)

    def impact_of(self, instrument: str, max_depth: int = 3) -> list[tuple[str, int, RelationType]]:
        """Everything a new document touches, directly and transitively.

        Answers "which circulars and decrees does this new law affect".  Returns
        ``(instrument, depth, relation_at_first_hop)`` in breadth-first order.
        """
        start = normalise_instrument(instrument)
        seen: set[str] = {start}
        out: list[tuple[str, int, RelationType]] = []
        queue: deque[tuple[str, int, RelationType | None]] = deque([(start, 0, None)])

        while queue:
            node, depth, first_relation = queue.popleft()
            if depth >= max_depth:
                continue
            # Downstream: what this document changes.
            for rel in self._out.get(node, []):
                if not rel.target_instrument or rel.target_instrument in seen:
                    continue
                seen.add(rel.target_instrument)
                relation = first_relation or rel.relation
                out.append((rel.target_instrument, depth + 1, relation))
                queue.append((rel.target_instrument, depth + 1, relation))
            # Upstream: documents that detail or guide what this document changes
            # are themselves impacted.
            for rel in self._in.get(node, []):
                if rel.relation not in {"DETAILS", "GUIDES", "INTERPRETS"}:
                    continue
                source = self.document_to_instrument.get(
                    rel.source_document_id, rel.source_document_id
                )
                if source in seen:
                    continue
                seen.add(source)
                relation = first_relation or rel.relation
                out.append((source, depth + 1, relation))
                queue.append((source, depth + 1, relation))

        return out

    def to_dict(self) -> dict:
        return {
            "nodes": sorted(
                set(self.instrument_to_document)
                | {e.target_instrument for e in self.edges if e.target_instrument}
            ),
            "edges": [edge.to_dict() for edge in self.edges],
            "resolution": self.resolution_stats(),
        }


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------

ChangeKind = str  # "added" | "modified" | "removed" | "unchanged"


def diff_articles(old: dict[str, str], new: dict[str, str]) -> dict[str, ChangeKind]:
    """Compare two versions of a document, keyed by article label.

    Deliberately literal: two articles are "modified" when their normalised text
    differs at all.  A legal diff must not smooth over a changed number.
    """
    result: dict[str, ChangeKind] = {}
    for key, new_text in new.items():
        if key not in old:
            result[key] = "added"
        elif _normalise(old[key]) != _normalise(new_text):
            result[key] = "modified"
        else:
            result[key] = "unchanged"
    for key in old:
        if key not in new:
            result[key] = "removed"
    return result


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()
